#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/sqlalchemy.py
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the project nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import datetime
import enum
import unittest
import uuid

import rule_engine
import rule_engine.engine as engine
import rule_engine.errors as errors
import rule_engine.types as types

try:
    import sqlalchemy
    from sqlalchemy import Column, ForeignKey, Integer, String
    from sqlalchemy.orm import DeclarativeBase, Mapped, column_property, mapped_column, relationship
    _HAS_SQLALCHEMY = True
except ImportError:
    _HAS_SQLALCHEMY = False

__all__ = ('SqlAlchemyObjectTests', 'SqlAlchemyTypeResolverTests')

DataType = types.DataType

if _HAS_SQLALCHEMY:
    class _Base(DeclarativeBase):
        pass

    class _Publisher(enum.Enum):
        DC = 'DC'
        MARVEL = 'Marvel'

    class _Hero(_Base):
        __tablename__ = 'heroes'
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]
        alias: Mapped[str | None]
        publisher: Mapped[_Publisher]
        first_appearance: Mapped[datetime.datetime]
        active: Mapped[bool]
        profile: Mapped[dict] = mapped_column(sqlalchemy.JSON)

    class _OnlyId(_Base):
        __tablename__ = 'only_ids'
        id: Mapped[int] = mapped_column(primary_key=True)

    class _OpaqueType(sqlalchemy.types.TypeDecorator):
        """A column type whose ``python_type`` raises to exercise the UNDEFINED fallback."""
        impl = sqlalchemy.String
        cache_ok = True

        @property
        def python_type(self):
            raise NotImplementedError

    class _WithOpaque(_Base):
        __tablename__ = 'with_opaques'
        id: Mapped[int] = mapped_column(primary_key=True)
        blob = mapped_column(_OpaqueType, nullable=False)

    class _UuidType(sqlalchemy.types.TypeDecorator):
        """A column type whose ``python_type`` is introspectable but unmappable by Rule Engine."""
        impl = sqlalchemy.String
        cache_ok = True

        @property
        def python_type(self):
            return uuid.UUID

    class _WithUuid(_Base):
        __tablename__ = 'with_uuids'
        id: Mapped[int] = mapped_column(primary_key=True)
        external_id = mapped_column(_UuidType, nullable=False)

    # One-to-many + many-to-one pair used to exercise recursive relationships
    class _Author(_Base):
        __tablename__ = 'authors'
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]
        books: Mapped[list['_Book']] = relationship(back_populates='author')

    class _Book(_Base):
        __tablename__ = 'books'
        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str]
        author_id: Mapped[int | None] = mapped_column(ForeignKey('authors.id'))
        author: Mapped['_Author | None'] = relationship(back_populates='books')

    # Self-referential adjacency list
    class _Category(_Base):
        __tablename__ = 'categories'
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str]
        parent_id: Mapped[int | None] = mapped_column(ForeignKey('categories.id'))
        parent: Mapped['_Category | None'] = relationship(remote_side=[id])

    # Three-way cycle to exercise OBJECT.reference placeholders for non-root ancestors
    class _Alpha(_Base):
        __tablename__ = 'alphas'
        id: Mapped[int] = mapped_column(primary_key=True)
        beta_id: Mapped[int | None] = mapped_column(ForeignKey('betas.id'))
        beta: Mapped['_Beta | None'] = relationship(foreign_keys=[beta_id])

    class _Beta(_Base):
        __tablename__ = 'betas'
        id: Mapped[int] = mapped_column(primary_key=True)
        gamma_id: Mapped[int | None] = mapped_column(ForeignKey('gammas.id'))
        gamma: Mapped['_Gamma | None'] = relationship(foreign_keys=[gamma_id])

    class _Gamma(_Base):
        __tablename__ = 'gammas'
        id: Mapped[int] = mapped_column(primary_key=True)
        alpha_id: Mapped[int | None] = mapped_column(ForeignKey('alphas.id'))
        alpha: Mapped['_Alpha | None'] = relationship(foreign_keys=[alpha_id])

    # column_property lands in mapper.columns as a Label rather than a Column, so the walker must skip it
    class _WithColumnProperty(_Base):
        __tablename__ = 'with_column_properties'
        id = Column(Integer, primary_key=True)
        title = Column(String)
        subtitle = Column(String, default='')
        full_title = column_property(title + ' - ' + subtitle)

    class _Priority(enum.IntEnum):
        LOW = 1
        HIGH = 9

    class _Task(_Base):
        __tablename__ = 'tasks'
        id: Mapped[int] = mapped_column(primary_key=True)
        priority: Mapped[_Priority]

    class _Post(_Base):
        __tablename__ = 'posts'
        id: Mapped[int] = mapped_column(primary_key=True)
        tags = Column(sqlalchemy.ARRAY(String))


@unittest.skipUnless(_HAS_SQLALCHEMY, 'sqlalchemy is not installed')
class SqlAlchemyObjectTests(unittest.TestCase):
    def test_object_from_sqlalchemy_flat(self):
        schema = DataType.OBJECT.from_sqlalchemy('Hero', _Hero)
        self.assertEqual(schema.name, 'Hero')
        self.assertIs(schema.attributes['id'], DataType.FLOAT)
        self.assertIs(schema.attributes['name'], DataType.STRING)
        self.assertIs(schema.attributes['alias'], DataType.STRING)
        self.assertIs(schema.attributes['first_appearance'], DataType.DATETIME)
        self.assertIs(schema.attributes['active'], DataType.BOOLEAN)
        self.assertIs(schema.accessor, getattr)

    def test_object_from_sqlalchemy_nullability(self):
        schema = DataType.OBJECT.from_sqlalchemy('Hero', _Hero)
        # primary keys and Mapped[T] (no Optional) are not nullable
        self.assertFalse(schema.is_attributes_nullable('id'))
        self.assertFalse(schema.is_attributes_nullable('name'))
        # Mapped[T | None] is nullable
        self.assertTrue(schema.is_attributes_nullable('alias'))

    def test_object_from_sqlalchemy_enum_column(self):
        schema = DataType.OBJECT.from_sqlalchemy('Hero', _Hero)
        self.assertIs(schema.attributes['publisher'], DataType.STRING)

    def test_object_from_sqlalchemy_int_enum_column(self):
        # IntEnum members are ints at runtime, so the walker maps them to FLOAT rather than STRING
        schema = DataType.OBJECT.from_sqlalchemy('Task', _Task)
        self.assertIs(schema.attributes['priority'], DataType.FLOAT)
        rule = rule_engine.Rule('obj.priority == 9', context=rule_engine.Context(
            type_resolver=rule_engine.engine.type_resolver_from_dict({'obj': schema})
        ))
        self.assertTrue(rule.matches({'obj': _Task(id=1, priority=_Priority.HIGH)}))

    def test_object_from_sqlalchemy_json_column(self):
        # sqlalchemy.JSON reports python_type as dict, so it threads through DataType.from_type to MAPPING
        schema = DataType.OBJECT.from_sqlalchemy('Hero', _Hero)
        self.assertEqual(schema.attributes['profile'], DataType.MAPPING(DataType.UNDEFINED, DataType.UNDEFINED))

    def test_object_from_sqlalchemy_unsupported_python_type_strict(self):
        # by default (strict=True), an opaque column type raises ValueError
        with self.assertRaisesRegex(ValueError, r"can not map column 'blob' to a compatible data type"):
            DataType.OBJECT.from_sqlalchemy('WithOpaque', _WithOpaque)

    def test_object_from_sqlalchemy_unsupported_python_type_non_strict(self):
        # with strict=False, an opaque column type falls back to UNDEFINED
        schema = DataType.OBJECT.from_sqlalchemy('WithOpaque', _WithOpaque, strict=False)
        self.assertIs(schema.attributes['blob'], DataType.UNDEFINED)

    def test_object_from_sqlalchemy_unmappable_python_type_strict(self):
        # a column whose python_type is known but not mappable (e.g. uuid.UUID) also raises under strict
        with self.assertRaises((TypeError, ValueError)):
            DataType.OBJECT.from_sqlalchemy('WithUuid', _WithUuid)

    def test_object_from_sqlalchemy_unmappable_python_type_non_strict(self):
        schema = DataType.OBJECT.from_sqlalchemy('WithUuid', _WithUuid, strict=False)
        self.assertIs(schema.attributes['external_id'], DataType.UNDEFINED)

    def test_object_from_sqlalchemy_custom_accessor(self):
        def dict_getter(obj, name):
            return obj[name]
        schema = DataType.OBJECT.from_sqlalchemy('OnlyId', _OnlyId, accessor=dict_getter)
        self.assertIs(schema.accessor, dict_getter)

    def test_object_from_sqlalchemy_rejects_non_mapped(self):
        class NotMapped:
            id: int

        with self.assertRaisesRegex(
                TypeError,
                r'^from_sqlalchemy argument 2 must be a SQLAlchemy mapped class'
        ):
            DataType.OBJECT.from_sqlalchemy('X', NotMapped)

    def test_object_from_sqlalchemy_one_to_many_relationship(self):
        schema = DataType.OBJECT.from_sqlalchemy('Author', _Author)
        books_type = schema.attributes['books']
        self.assertIsInstance(books_type, types._ArrayDataTypeDef)
        book_type = books_type.value_type
        self.assertIsInstance(book_type, types._ObjectDataTypeDef)
        # nested classes default their OBJECT name to target_cls.__name__
        self.assertEqual(book_type.name, '_Book')
        self.assertIs(book_type.attributes['title'], DataType.STRING)
        # Book.author back-references Author (the root); left as a placeholder for later parse-time resolution
        author_back_ref = book_type.attributes['author']
        self.assertIsInstance(author_back_ref, types._ReferenceDataTypeDef)
        self.assertEqual(author_back_ref.name, 'Author')
        # collection relationships are not nullable (empty list = "no items")
        self.assertFalse(schema.is_attributes_nullable('books'))

    def test_object_from_sqlalchemy_many_to_one_relationship(self):
        schema = DataType.OBJECT.from_sqlalchemy('Book', _Book)
        author_type = schema.attributes['author']
        self.assertIsInstance(author_type, types._ObjectDataTypeDef)
        self.assertEqual(author_type.name, '_Author')
        # Book.author_id is nullable, so the scalar relationship is nullable
        self.assertTrue(schema.is_attributes_nullable('author'))

    def test_object_from_sqlalchemy_self_reference(self):
        schema = DataType.OBJECT.from_sqlalchemy('Category', _Category)
        # parent relationship loops back to the root class
        self.assertIs(schema.attributes['parent'], schema)
        self.assertTrue(schema.is_attributes_nullable('parent'))

    def test_object_from_sqlalchemy_typed_array_column(self):
        # ARRAY columns preserve their element type; value_type reflects the mapped inner type
        schema = DataType.OBJECT.from_sqlalchemy('Post', _Post)
        tags_type = schema.attributes['tags']
        self.assertIsInstance(tags_type, types._ArrayDataTypeDef)
        self.assertIs(tags_type.value_type, DataType.STRING)

    def test_object_from_sqlalchemy_skips_column_property(self):
        schema = DataType.OBJECT.from_sqlalchemy('WithColumnProperty', _WithColumnProperty)
        self.assertIn('title', schema.attributes)
        self.assertIn('subtitle', schema.attributes)
        # column_property entries don't expose .nullable and are out of scope for rule evaluation
        self.assertNotIn('full_title', schema.attributes)

    def test_object_from_sqlalchemy_forward_reference_on_deep_cycle(self):
        # Alpha -> Beta -> Gamma -> Alpha forms a 3-way cycle. The Gamma.alpha relationship is to the
        # build-stack ancestor Alpha (not the class currently being expanded — that's Gamma), so it
        # must surface as an unresolved reference that the type_resolver will close later.
        schema = DataType.OBJECT.from_sqlalchemy('Alpha', _Alpha)
        beta_type = schema.attributes['beta']
        self.assertIsInstance(beta_type, types._ObjectDataTypeDef)
        gamma_type = beta_type.attributes['gamma']
        self.assertIsInstance(gamma_type, types._ObjectDataTypeDef)
        alpha_ref = gamma_type.attributes['alpha']
        self.assertIsInstance(alpha_ref, types._ReferenceDataTypeDef)
        self.assertEqual(alpha_ref.name, 'Alpha')


@unittest.skipUnless(_HAS_SQLALCHEMY, 'sqlalchemy is not installed')
class SqlAlchemyTypeResolverTests(unittest.TestCase):
    def test_type_resolver_from_sqlalchemy(self):
        type_resolver = rule_engine.type_resolver_from_sqlalchemy(_Hero)
        self.assertTrue(callable(type_resolver))
        self.assertIs(type_resolver('name'), DataType.STRING)
        self.assertIs(type_resolver('active'), DataType.BOOLEAN)
        with self.assertRaises(errors.SymbolResolutionError):
            type_resolver('doesnotexist')

    def test_type_resolver_from_sqlalchemy_evaluates_rule(self):
        context = engine.Context(
                resolver=engine.resolve_attribute,
                type_resolver=rule_engine.type_resolver_from_sqlalchemy(_Hero)
        )
        hero = _Hero(
                id=1,
                name='Batman',
                alias='Bruce Wayne',
                publisher=_Publisher.DC,
                first_appearance=datetime.datetime(1939, 5, 1),
                active=True,
                profile={}
        )
        self.assertTrue(engine.Rule('name == "Batman" and active', context=context).matches(hero))
        self.assertFalse(engine.Rule('name == "Joker"', context=context).matches(hero))

    def test_type_resolver_from_sqlalchemy_mutual_recursion(self):
        # Author.books -> [Book], Book.author -> Author; the Book.author reference must close at
        # parse time via the type_resolver registering both OBJECT schemas.
        type_resolver = rule_engine.type_resolver_from_sqlalchemy(_Author)
        author_type = type_resolver('_Author')
        book_type = type_resolver('_Book')
        self.assertIsInstance(author_type, types._ObjectDataTypeDef)
        self.assertIsInstance(book_type, types._ObjectDataTypeDef)

        context = engine.Context(resolver=engine.resolve_attribute, type_resolver=type_resolver)
        # parsing this rule requires traversing Author -> books -> Book -> author -> Author
        engine.Rule('books.length > 0', context=context)

    def test_type_resolver_from_sqlalchemy_non_strict(self):
        # strict=False threads through to from_sqlalchemy so opaque columns resolve to UNDEFINED
        type_resolver = rule_engine.type_resolver_from_sqlalchemy(_WithOpaque, strict=False)
        self.assertIs(type_resolver('blob'), DataType.UNDEFINED)

    def test_type_resolver_from_sqlalchemy_rejects_non_mapped(self):
        class NotMapped:
            id: int

        with self.assertRaisesRegex(
                TypeError,
                r'^type_resolver_from_sqlalchemy argument 1 must be a SQLAlchemy mapped class'
        ):
            rule_engine.type_resolver_from_sqlalchemy(NotMapped)


if __name__ == '__main__':
    unittest.main()
