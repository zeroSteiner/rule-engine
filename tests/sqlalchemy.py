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

import rule_engine.types as types

try:
    import sqlalchemy
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    _HAS_SQLALCHEMY = True
except ImportError:
    _HAS_SQLALCHEMY = False

__all__ = ('SqlAlchemyObjectTests',)

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

    def test_object_from_sqlalchemy_json_column(self):
        # sqlalchemy.JSON reports python_type as dict, so it threads through DataType.from_type to MAPPING
        schema = DataType.OBJECT.from_sqlalchemy('Hero', _Hero)
        self.assertEqual(schema.attributes['profile'], DataType.MAPPING(DataType.UNDEFINED, DataType.UNDEFINED))

    def test_object_from_sqlalchemy_unsupported_python_type(self):
        # column types whose python_type raises NotImplementedError fall back to UNDEFINED
        schema = DataType.OBJECT.from_sqlalchemy('WithOpaque', _WithOpaque)
        self.assertIs(schema.attributes['blob'], DataType.UNDEFINED)

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


if __name__ == '__main__':
    unittest.main()
