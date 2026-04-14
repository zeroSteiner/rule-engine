#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/types.py
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

import collections
import datetime
import sys
import typing
import unittest

import rule_engine.errors as errors
import rule_engine.types as types

__all__ = ('DataTypeTests', 'MetaDataTypeTests', 'ObjectDataTypeTests', 'ValueIsTests')

DataType = types.DataType

class DataTypeTests(unittest.TestCase):
    class _UnsupportedType(object):
        pass

    def test_data_type_collections(self):
        with self.assertRaises(TypeError):
            types._CollectionDataTypeDef('TEST', float)

    def test_data_type_equality_array(self):
        dt1 = DataType.ARRAY(DataType.STRING)
        self.assertIs(dt1.value_type, DataType.STRING)
        self.assertEqual(dt1, DataType.ARRAY(DataType.STRING))
        self.assertNotEqual(dt1, DataType.ARRAY)
        self.assertNotEqual(dt1, DataType.ARRAY(DataType.STRING, value_type_nullable=False))

    def test_data_type_equality_function(self):
        dt1 = DataType.FUNCTION('test', return_type=DataType.FLOAT, argument_types=(), minimum_arguments=0)
        self.assertEqual(dt1.value_name, 'test')
        self.assertEqual(dt1, DataType.FUNCTION('otherTest', return_type=DataType.FLOAT, argument_types=(), minimum_arguments=0))
        self.assertNotEqual(dt1, DataType.NULL)
        self.assertNotEqual(dt1, DataType.FUNCTION('test', return_type=DataType.NULL, argument_types=(), minimum_arguments=0))
        self.assertNotEqual(dt1, DataType.FUNCTION('test', return_type=DataType.FLOAT, argument_types=(DataType.FLOAT,), minimum_arguments=0))
        self.assertNotEqual(dt1, DataType.FUNCTION('otherTest', return_type=DataType.FLOAT, minimum_arguments=1))

    def test_data_type_equality_mapping(self):
        dt1 = DataType.MAPPING(DataType.STRING)
        self.assertIs(dt1.key_type, DataType.STRING)
        self.assertEqual(dt1, DataType.MAPPING(DataType.STRING))
        self.assertNotEqual(dt1, DataType.MAPPING)
        self.assertNotEqual(dt1, DataType.MAPPING(DataType.STRING, value_type=DataType.STRING))
        self.assertNotEqual(dt1, DataType.MAPPING(DataType.STRING, value_type_nullable=False))

    def test_data_type_equality_set(self):
        dt1 = DataType.SET(DataType.STRING)
        self.assertIs(dt1.value_type, DataType.STRING)
        self.assertEqual(dt1, DataType.SET(DataType.STRING))
        self.assertNotEqual(dt1, DataType.SET)
        self.assertNotEqual(dt1, DataType.SET(DataType.STRING, value_type_nullable=False))

    def test_data_type_from_name(self):
        self.assertIs(DataType.from_name('ARRAY'), DataType.ARRAY)
        self.assertIs(DataType.from_name('BOOLEAN'), DataType.BOOLEAN)
        self.assertIs(DataType.from_name('BYTES'), DataType.BYTES)
        self.assertIs(DataType.from_name('DATETIME'), DataType.DATETIME)
        self.assertIs(DataType.from_name('FLOAT'), DataType.FLOAT)
        self.assertIs(DataType.from_name('FUNCTION'), DataType.FUNCTION)
        self.assertIs(DataType.from_name('MAPPING'), DataType.MAPPING)
        self.assertIs(DataType.from_name('NULL'), DataType.NULL)
        self.assertIs(DataType.from_name('SET'), DataType.SET)
        self.assertIs(DataType.from_name('STRING'), DataType.STRING)
        self.assertIs(DataType.from_name('TIMEDELTA'), DataType.TIMEDELTA)

    def test_data_type_from_name_error(self):
        with self.assertRaises(TypeError):
            DataType.from_name(1)
        with self.assertRaises(ValueError):
            DataType.from_name('FOOBAR')

    def test_data_type_from_type(self):
        self.assertIs(DataType.from_type(list), DataType.ARRAY)
        self.assertIs(DataType.from_type(tuple), DataType.ARRAY)
        self.assertIs(DataType.from_type(bool), DataType.BOOLEAN)
        self.assertIs(DataType.from_type(bytes), DataType.BYTES)
        self.assertIs(DataType.from_type(datetime.date), DataType.DATETIME)
        self.assertIs(DataType.from_type(datetime.datetime), DataType.DATETIME)
        self.assertIs(DataType.from_type(float), DataType.FLOAT)
        self.assertIs(DataType.from_type(int), DataType.FLOAT)
        self.assertIs(DataType.from_type(type(lambda: None)), DataType.FUNCTION)
        self.assertIs(DataType.from_type(dict), DataType.MAPPING)
        self.assertIs(DataType.from_type(type(None)), DataType.NULL)
        self.assertIs(DataType.from_type(set), DataType.SET)
        self.assertIs(DataType.from_type(str), DataType.STRING)
        self.assertIs(DataType.from_type(datetime.timedelta), DataType.TIMEDELTA)

    def test_data_type_from_type_hint(self):
        # simple compound tests
        self.assertEqual(DataType.from_type(typing.List[str]), DataType.ARRAY(DataType.STRING))
        self.assertEqual(DataType.from_type(typing.Tuple[str]), DataType.ARRAY(DataType.UNDEFINED))
        self.assertEqual(DataType.from_type(typing.Set[int]), DataType.SET(DataType.FLOAT))
        self.assertEqual(DataType.from_type(typing.Dict[str, str]), DataType.MAPPING(DataType.STRING, DataType.STRING))

        # complex compound tests
        self.assertEqual(DataType.from_type(typing.List[list]), DataType.ARRAY(DataType.ARRAY))
        self.assertEqual(DataType.from_type(
                typing.Dict[str, typing.Dict[str, datetime.datetime]]),
                DataType.MAPPING(DataType.STRING, DataType.MAPPING(DataType.STRING, DataType.DATETIME)
        ))

        if sys.version_info >= (3, 9):
            self.assertEqual(DataType.from_type(list[str]), DataType.ARRAY(DataType.STRING))
            self.assertEqual(DataType.from_type(tuple[str]), DataType.ARRAY(DataType.UNDEFINED))
            self.assertEqual(DataType.from_type(set[int]), DataType.SET(DataType.FLOAT))
            self.assertEqual(DataType.from_type(dict[str, str]), DataType.MAPPING(DataType.STRING, DataType.STRING))

            self.assertEqual(DataType.from_type(list[list]), DataType.ARRAY(DataType.ARRAY))
            self.assertEqual(DataType.from_type(
                    dict[str, dict[str, datetime.datetime]]),
                    DataType.MAPPING(DataType.STRING, DataType.MAPPING(DataType.STRING, DataType.DATETIME)
            ))

    def test_data_type_from_type_error(self):
        with self.assertRaisesRegex(TypeError, r'^from_type argument 1 must be a type or a type hint, not _UnsupportedType$'):
            DataType.from_type(self._UnsupportedType())
        with self.assertRaisesRegex(ValueError, r'^can not map python type \'_UnsupportedType\' to a compatible data type$'):
            DataType.from_type(self._UnsupportedType)

    def test_data_type_from_value_compound_array(self):
        for value in [list(), range(0), tuple()]:
            value = DataType.from_value(value)
            self.assertEqual(value, DataType.ARRAY)
            self.assertIs(value.value_type, DataType.UNDEFINED)
            self.assertIs(value.iterable_type, DataType.UNDEFINED)
        value = DataType.from_value(['test'])
        self.assertEqual(value, DataType.ARRAY(DataType.STRING))
        self.assertIs(value.value_type, DataType.STRING)
        self.assertIs(value.iterable_type, DataType.STRING)

    def test_data_type_from_value_compound_mapping(self):
        value = DataType.from_value({})
        self.assertEqual(value, DataType.MAPPING)
        self.assertIs(value.key_type, DataType.UNDEFINED)
        self.assertIs(value.value_type, DataType.UNDEFINED)
        self.assertIs(value.iterable_type, DataType.UNDEFINED)

        value = DataType.from_value({'one': 1})
        self.assertEqual(value, DataType.MAPPING(DataType.STRING, DataType.FLOAT))
        self.assertIs(value.key_type, DataType.STRING)
        self.assertIs(value.value_type, DataType.FLOAT)
        self.assertIs(value.iterable_type, DataType.STRING)

    def test_data_type_from_value_compound_set(self):
        value = DataType.from_value(set())
        self.assertEqual(value, DataType.SET)
        self.assertIs(value.value_type, DataType.UNDEFINED)
        self.assertIs(value.iterable_type, DataType.UNDEFINED)

        value = DataType.from_value({'test'})
        self.assertEqual(value, DataType.SET(DataType.STRING))
        self.assertIs(value.value_type, DataType.STRING)
        self.assertIs(value.iterable_type, DataType.STRING)

    def test_data_type_from_value_scalar(self):
        self.assertIs(DataType.from_value(False), DataType.BOOLEAN)
        self.assertIs(DataType.from_value(b''), DataType.BYTES)
        self.assertIs(DataType.from_value(datetime.date.today()), DataType.DATETIME)
        self.assertIs(DataType.from_value(datetime.datetime.now()), DataType.DATETIME)
        self.assertIs(DataType.from_value(0), DataType.FLOAT)
        self.assertIs(DataType.from_value(0.0), DataType.FLOAT)
        self.assertIs(DataType.from_value(lambda: None), DataType.FUNCTION)
        self.assertIs(DataType.from_value(print), DataType.FUNCTION)
        self.assertIs(DataType.from_value(None), DataType.NULL)
        self.assertIs(DataType.from_value(''), DataType.STRING)
        self.assertIs(DataType.from_value(datetime.timedelta()), DataType.TIMEDELTA)

    def test_data_type_from_value_error(self):
        with self.assertRaisesRegex(TypeError, r'^can not map python type \'_UnsupportedType\' to a compatible data type$'):
            DataType.from_value(self._UnsupportedType())

    def test_data_type_function(self):
        with self.assertRaises(TypeError, msg='argument_types should be a sequence'):
            DataType.FUNCTION('test', argument_types=DataType.NULL)
        with self.assertRaises(ValueError, msg='minimum_arguments should be less than or equal to the length of argument_types'):
            DataType.FUNCTION('test', argument_types=(), minimum_arguments=1)

    def test_data_type_definitions_describe_themselves(self):
        for name in DataType:
            if name == 'UNDEFINED':
                continue
            data_type = getattr(DataType, name)
            self.assertRegex(repr(data_type), 'name=' + name)

class MetaDataTypeTests(unittest.TestCase):
    def test_data_type_is_iterable(self):
        self.assertGreater(len(DataType), 0)
        for name in DataType:
            self.assertIsInstance(name, str)
            self.assertRegex(name, r'^[A-Z]+$')

    def test_data_type_is_compatible(self):
        def _is_compat(*args):
            return self.assertTrue(DataType.is_compatible(*args))
        def _is_not_compat(*args):
            return self.assertFalse(DataType.is_compatible(*args))
        _is_compat(DataType.STRING, DataType.STRING)
        _is_compat(DataType.STRING, DataType.UNDEFINED)
        _is_compat(DataType.UNDEFINED, DataType.STRING)

        _is_compat(DataType.UNDEFINED, DataType.ARRAY)
        _is_compat(DataType.ARRAY, DataType.ARRAY(DataType.STRING))

        _is_not_compat(DataType.STRING, DataType.ARRAY)
        _is_not_compat(DataType.STRING, DataType.NULL)
        _is_not_compat(DataType.ARRAY(DataType.STRING), DataType.ARRAY(DataType.FLOAT))

        _is_compat(DataType.MAPPING, DataType.MAPPING)
        _is_compat(
                DataType.MAPPING(DataType.STRING),
                DataType.MAPPING(DataType.STRING, value_type=DataType.ARRAY)
        )
        _is_compat(
                DataType.MAPPING(DataType.STRING, value_type=DataType.ARRAY),
                DataType.MAPPING(DataType.STRING, value_type=DataType.ARRAY(DataType.STRING))
        )
        _is_not_compat(
                DataType.MAPPING(DataType.STRING),
                DataType.MAPPING(DataType.FLOAT)
        )
        _is_not_compat(
                DataType.MAPPING(DataType.STRING, value_type=DataType.STRING),
                DataType.MAPPING(DataType.STRING, value_type=DataType.FLOAT)
        )

        with self.assertRaises(TypeError):
            DataType.is_compatible(DataType.STRING, None)

    def test_data_type_is_compatible_function(self):
        def _is_compat(*args):
            return self.assertTrue(DataType.is_compatible(*args))
        def _is_not_compat(*args):
            return self.assertFalse(DataType.is_compatible(*args))
        # the function name doesn't matter, it's only for reporting
        _is_compat(
                DataType.FUNCTION('functionA'),
                DataType.FUNCTION('functionB')
        )
        # return type is UNDEFINED by default which should be compatible
        _is_compat(
                DataType.FUNCTION('test', return_type=DataType.FLOAT),
                DataType.FUNCTION('test')
        )
        # argument types are UNDEFINED by default which should be compatible
        _is_compat(
                DataType.FUNCTION('test', argument_types=(DataType.STRING,), minimum_arguments=1),
                DataType.FUNCTION('test', minimum_arguments=1)
        )
        # minimum arguments defaults to the number of arguments
        _is_compat(
                DataType.FUNCTION('test', argument_types=(DataType.STRING,), minimum_arguments=1),
                DataType.FUNCTION('test', argument_types=(DataType.STRING,))
        )

        _is_not_compat(
                DataType.FUNCTION('test', return_type=DataType.FLOAT),
                DataType.FUNCTION('test', return_type=DataType.STRING)
        )
        _is_not_compat(
                DataType.FUNCTION('test', argument_types=(DataType.STRING,)),
                DataType.FUNCTION('test', argument_types=())
        )
        _is_not_compat(
                DataType.FUNCTION('test', argument_types=(DataType.FLOAT,)),
                DataType.FUNCTION('test', argument_types=(DataType.STRING,))
        )
        _is_not_compat(
                DataType.FUNCTION('test', minimum_arguments=0),
                DataType.FUNCTION('test', minimum_arguments=1)
        )

    def test_data_type_is_definition(self):
        self.assertTrue(DataType.is_definition(DataType.ARRAY))
        self.assertFalse(DataType.is_definition(1))
        self.assertFalse(DataType.is_definition(None))

    def test_data_type_supports_contains(self):
        self.assertIn('ARRAY', DataType)
        self.assertIn('FUNCTION', DataType)
        self.assertIn('MAPPING', DataType)
        self.assertIn('STRING', DataType)
        self.assertIn('UNDEFINED', DataType)


    def test_data_type_supports_getitem(self):
        self.assertEqual(DataType['ARRAY'], DataType.ARRAY)
        self.assertEqual(DataType['FUNCTION'], DataType.FUNCTION)
        self.assertEqual(DataType['MAPPING'], DataType.MAPPING)
        self.assertEqual(DataType['STRING'], DataType.STRING)
        self.assertEqual(DataType['UNDEFINED'], DataType.UNDEFINED)

class ObjectDataTypeTests(unittest.TestCase):
    class _HeroDataclass(object):
        def __init__(self, name, first_appearance):
            self.name = name
            self.first_appearance = first_appearance

    def _build_hero(self):
        return DataType.OBJECT('Hero', attributes={
                'name': DataType.STRING,
                'first_appearance': DataType.DATETIME,
                'nemesis': DataType.OBJECT.reference('Hero'),
        })

    def test_object_bare_repr_and_member_registration(self):
        self.assertIn('OBJECT', DataType)
        self.assertRegex(repr(DataType.OBJECT), r'name=OBJECT')
        self.assertIs(DataType.from_name('OBJECT'), DataType.OBJECT)
        self.assertTrue(DataType.is_definition(DataType.OBJECT))

    def test_object_construction_empty(self):
        empty = DataType.OBJECT('Empty')
        self.assertEqual(empty.name, 'Empty')
        self.assertEqual(empty.attributes, {})
        self.assertFalse(empty.is_scalar)
        self.assertTrue(empty.is_compound)
        self.assertIs(empty.accessor, getattr)

    def test_object_construction_flat_schema(self):
        Wookiee = DataType.OBJECT('Wookiee', attributes={
                'name': DataType.STRING,
                'homeworld': DataType.STRING,
        })
        self.assertEqual(Wookiee.name, 'Wookiee')
        self.assertIs(Wookiee.attributes['name'], DataType.STRING)
        self.assertIs(Wookiee.attributes['homeworld'], DataType.STRING)

    def test_object_nested_schema(self):
        Address = DataType.OBJECT('Address', attributes={'city': DataType.STRING})
        Person = DataType.OBJECT('Person', attributes={
                'name': DataType.STRING,
                'address': Address,
        })
        self.assertIs(Person.attributes['address'], Address)

    def test_object_self_reference_direct(self):
        Hero = self._build_hero()
        self.assertIs(Hero.attributes['nemesis'], Hero)

    def test_object_self_sentinel(self):
        Hero = DataType.OBJECT('Hero', attributes={
                'name': DataType.STRING,
                'nemesis': DataType.OBJECT.self,
                'sidekicks': DataType.ARRAY(DataType.OBJECT.self),
        })
        self.assertIs(Hero.attributes['nemesis'], Hero)
        self.assertIs(Hero.attributes['sidekicks'].value_type, Hero)

    def test_object_self_sentinel_uses_reserved_name(self):
        # the sentinel carries a reserved name so users don't collide with it
        self.assertEqual(DataType.OBJECT.self.name, '__self__')
        self.assertIsInstance(DataType.OBJECT.self, types._ReferenceDataTypeDef)

    def test_object_self_reference_inside_array(self):
        Hero = DataType.OBJECT('Hero', attributes={
                'sidekicks': DataType.ARRAY(DataType.OBJECT.reference('Hero')),
        })
        self.assertIs(Hero.attributes['sidekicks'].value_type, Hero)

    def test_object_self_reference_inside_mapping(self):
        Hero = DataType.OBJECT('Hero', attributes={
                'known_aliases': DataType.MAPPING(DataType.STRING, value_type=DataType.OBJECT.reference('Hero')),
        })
        self.assertIs(Hero.attributes['known_aliases'].value_type, Hero)

    def test_object_self_reference_inside_function(self):
        Hero = DataType.OBJECT('Hero', attributes={
                'promote': DataType.FUNCTION(
                        'promote',
                        return_type=DataType.OBJECT.reference('Hero'),
                        argument_types=(DataType.OBJECT.reference('Hero'),)
                ),
        })
        self.assertIs(Hero.attributes['promote'].return_type, Hero)
        self.assertIs(Hero.attributes['promote'].argument_types[0], Hero)

    def test_object_cross_reference_left_unresolved(self):
        Person = DataType.OBJECT('Person', attributes={
                'employer': DataType.OBJECT.reference('Company'),
        })
        self.assertIsInstance(Person.attributes['employer'], types._ReferenceDataTypeDef)
        self.assertEqual(Person.attributes['employer'].name, 'Company')

    def test_object_repr_does_not_recurse(self):
        Hero = self._build_hero()
        text = repr(Hero)
        self.assertRegex(text, r'name=Hero')
        self.assertIn('nemesis', text)

    def test_object_hash_does_not_recurse(self):
        Hero = self._build_hero()
        # would infinite-loop if __hash__ walked the schema
        self.assertEqual(hash(Hero), hash(('OBJECT', 'Hero')))

    def test_object_hash_is_nominal(self):
        left = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        right = DataType.OBJECT('Hero', attributes={'alias': DataType.STRING})
        # same name, different schemas — hash matches but equality does not
        self.assertEqual(hash(left), hash(right))
        self.assertNotEqual(left, right)

    def test_object_equality_self_referential(self):
        left = self._build_hero()
        right = self._build_hero()
        self.assertEqual(left, right)

    def test_object_equality_distinct_schemas(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        Wookiee = DataType.OBJECT('Wookiee', attributes={'name': DataType.STRING})
        self.assertNotEqual(Hero, Wookiee)

    def test_object_equality_non_object(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        self.assertNotEqual(Hero, DataType.STRING)
        self.assertNotEqual(Hero, None)

    def test_object_equality_different_attribute_names(self):
        left = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        right = DataType.OBJECT('Hero', attributes={'name': DataType.STRING, 'alias': DataType.STRING})
        self.assertNotEqual(left, right)

    def test_object_equality_different_nullable(self):
        left = DataType.OBJECT('Hero', attributes={'name': DataType.STRING}, attributes_nullable={'name': True})
        right = DataType.OBJECT('Hero', attributes={'name': DataType.STRING}, attributes_nullable={'name': False})
        self.assertNotEqual(left, right)

    def test_object_hashable_in_set(self):
        types_set = {DataType.OBJECT('Hero'), DataType.OBJECT('Wookiee'), DataType.OBJECT('Hero')}
        self.assertEqual(len(types_set), 2)

    def test_object_is_compatible_same_name(self):
        left = self._build_hero()
        right = self._build_hero()
        self.assertTrue(DataType.is_compatible(left, right))

    def test_object_is_compatible_different_name(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        Wookiee = DataType.OBJECT('Wookiee', attributes={'name': DataType.STRING})
        self.assertFalse(DataType.is_compatible(Hero, Wookiee))

    def test_object_is_compatible_with_undefined(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        self.assertTrue(DataType.is_compatible(Hero, DataType.UNDEFINED))
        self.assertTrue(DataType.is_compatible(DataType.UNDEFINED, Hero))

    def test_object_is_compatible_with_reference(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        self.assertTrue(DataType.is_compatible(Hero, DataType.OBJECT.reference('Hero')))
        self.assertTrue(DataType.is_compatible(DataType.OBJECT.reference('Hero'), Hero))
        # even mismatching reference names are optimistically compatible; real check happens at parse time
        self.assertTrue(DataType.is_compatible(Hero, DataType.OBJECT.reference('Wookiee')))

    def test_object_is_compatible_with_scalar(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        self.assertFalse(DataType.is_compatible(Hero, DataType.STRING))
        self.assertFalse(DataType.is_compatible(DataType.STRING, Hero))

    def test_object_is_compatible_inside_array(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        Wookiee = DataType.OBJECT('Wookiee', attributes={'name': DataType.STRING})
        self.assertTrue(DataType.is_compatible(DataType.ARRAY(Hero), DataType.ARRAY(Hero)))
        self.assertFalse(DataType.is_compatible(DataType.ARRAY(Hero), DataType.ARRAY(Wookiee)))

    def test_object_is_compatible_inside_mapping(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        self.assertTrue(DataType.is_compatible(
                DataType.MAPPING(DataType.STRING, value_type=Hero),
                DataType.MAPPING(DataType.STRING, value_type=Hero)
        ))

    def test_object_set_rejection(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        with self.assertRaises(errors.EngineError):
            DataType.SET(Hero)

    def test_object_mapping_value_accepted(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        mapping = DataType.MAPPING(DataType.STRING, value_type=Hero)
        self.assertIs(mapping.value_type, Hero)

    def test_object_function_return_and_argument(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        fn = DataType.FUNCTION('promote', return_type=Hero, argument_types=(Hero,))
        self.assertIs(fn.return_type, Hero)
        self.assertIs(fn.argument_types[0], Hero)

    def test_object_from_value_rejects_instance(self):
        instance = self._HeroDataclass('Luke', datetime.datetime(1977, 5, 25))
        with self.assertRaises(TypeError):
            DataType.from_value(instance)

    def test_object_from_type_rejects_class(self):
        with self.assertRaises(ValueError):
            DataType.from_type(self._HeroDataclass)

    def test_object_from_name_unknown_schema_errors(self):
        with self.assertRaises(ValueError):
            DataType.from_name('Hero')

    def test_object_is_attributes_nullable(self):
        Hero = DataType.OBJECT('Hero', attributes={
                'name': DataType.STRING,
                'nemesis': DataType.STRING,
        }, attributes_nullable={'nemesis': False})
        self.assertTrue(Hero.is_attributes_nullable('name'))
        self.assertFalse(Hero.is_attributes_nullable('nemesis'))
        # unspecified attributes default to nullable
        self.assertTrue(Hero.is_attributes_nullable('totally_unknown'))

    def test_object_custom_accessor(self):
        def dict_getter(obj, name):
            return obj[name]
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING}, accessor=dict_getter)
        self.assertIs(Hero.accessor, dict_getter)

    def test_reference_is_definition(self):
        ref = DataType.OBJECT.reference('Hero')
        self.assertTrue(DataType.is_definition(ref))
        self.assertFalse(ref.is_scalar)
        self.assertTrue(ref.is_compound)

    def test_reference_equality_and_hash(self):
        a = DataType.OBJECT.reference('Hero')
        b = DataType.OBJECT.reference('Hero')
        c = DataType.OBJECT.reference('Wookiee')
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertNotEqual(a, c)
        self.assertNotEqual(a, 'Hero')

    def test_reference_repr(self):
        ref = DataType.OBJECT.reference('Hero')
        self.assertRegex(repr(ref), r'name=Hero')
        self.assertIn('unresolved', repr(ref))

    def test_reference_inside_set_fails_during_self_resolution(self):
        # SET(reference('Self')) gets resolved during _ObjectDataTypeDef.__init__ which triggers SET's OBJECT rejection
        with self.assertRaises(errors.EngineError):
            DataType.OBJECT('Hero', attributes={
                    'allies': DataType.SET(DataType.OBJECT.reference('Hero')),
            })

    def test_substitute_self_references_noop_on_unrelated_reference(self):
        Person = DataType.OBJECT('Person', attributes={
                'manager': DataType.ARRAY(DataType.OBJECT.reference('Manager')),
        })
        # cross-reference is left intact since the name doesn't match
        self.assertIsInstance(Person.attributes['manager'].value_type, types._ReferenceDataTypeDef)
        self.assertEqual(Person.attributes['manager'].value_type.name, 'Manager')

    def test_object_equality_attribute_type_mismatch(self):
        left = DataType.OBJECT('Hero', attributes={'rank': DataType.STRING})
        right = DataType.OBJECT('Hero', attributes={'rank': DataType.FLOAT})
        self.assertNotEqual(left, right)

    def test_object_schema_with_mapping_attribute_no_self_ref(self):
        # exercises the _MappingDataTypeDef no-op branch in _substitute_self_references
        Hero = DataType.OBJECT('Hero', attributes={
                'aliases': DataType.MAPPING(DataType.STRING, value_type=DataType.STRING),
        })
        self.assertIsInstance(Hero.attributes['aliases'], types._MappingDataTypeDef)
        self.assertIs(Hero.attributes['aliases'].value_type, DataType.STRING)

    def test_object_schema_with_function_attribute_no_self_ref(self):
        # exercises the _FunctionDataTypeDef no-op branch in _substitute_self_references
        Hero = DataType.OBJECT('Hero', attributes={
                'describe': DataType.FUNCTION('describe', return_type=DataType.STRING),
        })
        self.assertIsInstance(Hero.attributes['describe'], types._FunctionDataTypeDef)
        self.assertIs(Hero.attributes['describe'].return_type, DataType.STRING)

    def test_object_schema_with_function_undefined_arguments(self):
        # exercises the argument_types is UNDEFINED branch in _substitute_self_references
        Hero = DataType.OBJECT('Hero', attributes={
                'describe': DataType.FUNCTION('describe', return_type=DataType.OBJECT.reference('Hero')),
        })
        self.assertIs(Hero.attributes['describe'].return_type, Hero)
        self.assertIs(Hero.attributes['describe'].argument_types, DataType.UNDEFINED)

    def test_object_schema_with_array_attribute_no_self_ref(self):
        Hero = DataType.OBJECT('Hero', attributes={
                'aliases': DataType.ARRAY(DataType.STRING),
        })
        self.assertIsInstance(Hero.attributes['aliases'], types._ArrayDataTypeDef)
        self.assertIs(Hero.attributes['aliases'].value_type, DataType.STRING)

    def test_substitute_self_references_skips_nested_object(self):
        Inner = DataType.OBJECT('Inner', attributes={'name': DataType.STRING})
        Outer = DataType.OBJECT('Outer', attributes={
                'inner': Inner,
                'self_ref': DataType.OBJECT.reference('Outer'),
        })
        # nested OBJECT is not descended into (its own __init__ handled its scope)
        self.assertIs(Outer.attributes['inner'], Inner)
        self.assertIs(Outer.attributes['self_ref'], Outer)

inf = float('inf')
nan = float('nan')

class ValueIsTests(unittest.TestCase):
    _Case = collections.namedtuple('_Case', ('value', 'numeric', 'real', 'integer', 'natural'))
    cases = (
            #     value   numeric  real    integer natural
            _Case(-inf,   True,    False,  False,  False),
            _Case(-1.5,   True,    True,   False,  False),
            _Case(-1.0,   True,    True,   True,   False),
            _Case(-1,     True,    True,   True,   False),
            _Case(0,      True,    True,   True,   True ),
            _Case(1,      True,    True,   True,   True ),
            _Case(1.0,    True,    True,   True,   True ),
            _Case(1.5,    True,    True,   False,  False),
            _Case(inf,    True,    False,  False,  False),
            _Case(nan,    True,    False,  False,  False),
            _Case(True,   False,   False,  False,  False),
            _Case(False,  False,   False,  False,  False),
            _Case('',     False,   False,  False,  False),
            _Case(None,   False,   False,  False,  False),
    )
    def test_value_is_integer_number(self):
        for case in self.cases:
            self.assertEqual(types.is_integer_number(case.value), case.integer)

    def test_value_is_natural_number(self):
        for case in self.cases:
            self.assertEqual(types.is_natural_number(case.value), case.natural)

    def test_value_is_numeric(self):
        for case in self.cases:
            self.assertEqual(types.is_numeric(case.value), case.numeric)

    def test_value_is_real_number(self):
        for case in self.cases:
            self.assertEqual(types.is_real_number(case.value), case.real)

if __name__ == '__main__':
    unittest.main()
