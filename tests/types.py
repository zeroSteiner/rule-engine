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
import copy
import dataclasses
import datetime
import decimal
import enum
import pickle
import sys
import typing
import unittest
import unittest.mock

import rule_engine.errors as errors
import rule_engine.types as types
import rule_engine.types.coercion as coercion

__all__ = (
    'CoercionTests',
    'DataTypeTests',
    'MetaDataTypeTests',
    'NullableDataTypeTests',
    'ObjectDataTypeTests',
    'ValueIsTests'
)

DataType = types.DataType

class CoercionTests(unittest.TestCase):
    def test_coerce_int_subclass_uses_int_value(self):
        # int subclasses like IntEnum don't repr() as a plain number; coercion must still produce a usable Decimal
        class Priority(enum.IntEnum):
            HIGH = 9

        value = types.coerce_value(Priority.HIGH)
        self.assertEqual(value, decimal.Decimal(9))

    def _set_int_max_str_digits(self, int_max_digits):
        if not hasattr(sys, 'set_int_max_str_digits'):
            self.skipTest('sys.set_int_max_str_digits is not available')
        self.addCleanup(sys.set_int_max_str_digits, sys.get_int_max_str_digits())
        sys.set_int_max_str_digits(int_max_digits)

    def test_coerce_int_max_digits_boundaries(self):
        for int_max_digits in (1, 2, 3, 20, 640, 4300):
            limit = 10 ** int_max_digits
            with self.subTest(int_max_digits=int_max_digits):
                for value in (limit - 1, -(limit - 1), (1 << (3 * int_max_digits)) - 1, 1 << (3 * int_max_digits)):
                    self.assertEqual(types.coerce_value(value, int_max_digits=int_max_digits), decimal.Decimal(value))
                for value in (limit, -limit):
                    with self.assertRaisesRegex(errors.ArithmeticError, r'\({0} digits\)'.format(int_max_digits)):
                        types.coerce_value(value, int_max_digits=int_max_digits)

    def test_coerce_int_max_digits_unlimited(self):
        value = 10 ** 4300
        self.assertEqual(types.coerce_value(value, int_max_digits=0), decimal.Decimal(value))

    def test_coerce_int_max_digits_default_follows_interpreter(self):
        self._set_int_max_str_digits(640)
        with self.assertRaisesRegex(errors.ArithmeticError, r'\(640 digits\)'):
            types.coerce_value(10 ** 640)
        sys.set_int_max_str_digits(4300)
        self.assertEqual(types.coerce_value(10 ** 640), decimal.Decimal(10 ** 640))

    def test_coerce_int_max_digits_overrides_interpreter(self):
        self._set_int_max_str_digits(640)
        self.assertEqual(types.coerce_value(10 ** 640, int_max_digits=4300), decimal.Decimal(10 ** 640))
        with self.assertRaises(errors.ArithmeticError):
            types.coerce_value(10 ** 20, int_max_digits=20)

    def test_coerce_int_max_digits_nested(self):
        for value in ([1, 10 ** 20], range(10 ** 20, 10 ** 20 + 1), {10 ** 20: 1}, {'a': (10 ** 20,)}):
            with self.subTest(value=type(value).__name__), self.assertRaises(errors.ArithmeticError):
                types.coerce_value(value, int_max_digits=20)
        self.assertEqual(types.coerce_value({'a': [10 ** 19]}, int_max_digits=20), {'a': (decimal.Decimal(10 ** 19),)})

    def test_coerce_int_max_digits_int_subclass(self):
        class Huge(enum.IntEnum):
            VALUE = 10 ** 20

        with self.assertRaises(errors.ArithmeticError):
            types.coerce_value(Huge.VALUE, int_max_digits=20)
        self.assertEqual(types.coerce_value(Huge.VALUE, int_max_digits=21), decimal.Decimal(10 ** 20))

    def test_coerce_int_max_digits_ignores_other_types(self):
        self.assertIs(types.coerce_value(True, int_max_digits=1), True)
        self.assertEqual(types.coerce_value(1e300, int_max_digits=20), decimal.Decimal(repr(1e300)))
        self.assertEqual(types.coerce_value(decimal.Decimal('1e300'), int_max_digits=20), decimal.Decimal('1e300'))

    def test_coerce_int_max_digits_set(self):
        # SET members aren't converted, their size is only checked
        value = {1, 'one', (2, frozenset([3]))}
        self.assertIs(types.coerce_value(value, int_max_digits=1), value)
        for value in ({10 ** 20}, {(1, (10 ** 20,))}, {frozenset([-10 ** 20])}):
            with self.subTest(value=value), self.assertRaises(errors.ArithmeticError):
                types.coerce_value(value, int_max_digits=20)
        self.assertEqual(types.coerce_value({10 ** 20}, int_max_digits=0), {10 ** 20})

    def test_coerce_int_max_digits_large_limit(self):
        # 10 ** int_max_digits is slow to calculate for large limits, so it's only used when the bit length isn't enough
        with unittest.mock.patch.object(coercion, '_int_limit', side_effect=AssertionError('_int_limit was called')):
            self.assertEqual(types.coerce_value(1 << 1000, int_max_digits=sys.maxsize), decimal.Decimal(1 << 1000))
            coercion._assert_int_bit_length(10 ** 6, sys.maxsize)
            with self.assertRaises(errors.ArithmeticError):
                types.coerce_value(1 << 100, int_max_digits=20)
            with self.assertRaises(errors.ArithmeticError):
                coercion._assert_int_bit_length(68, 20)
        coercion._assert_int_bit_length(67, 20)

    def test_coerce_int_max_digits_is_keyword_only(self):
        with self.assertRaises(TypeError):
            types.coerce_value(10 ** 20, True, 20)


class _FunctionDataTypeWithDict(types._FunctionDataTypeDef):
    # without __slots__, instances of this subclass have a __dict__
    pass

def _restore_data_type(data_type):
    restored = [('copy', copy.copy(data_type)), ('deepcopy', copy.deepcopy(data_type))]
    for protocol in range(2, pickle.HIGHEST_PROTOCOL + 1):
        restored.append(('pickle protocol {}'.format(protocol), pickle.loads(pickle.dumps(data_type, protocol=protocol))))
    return restored

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
        self.assertNotEqual(dt1, DataType.ARRAY(DataType.NULLABLE(DataType.STRING)))

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
        self.assertNotEqual(dt1, DataType.MAPPING(DataType.STRING, value_type=DataType.NULLABLE(DataType.STRING)))

    def test_data_type_equality_set(self):
        dt1 = DataType.SET(DataType.STRING)
        self.assertIs(dt1.value_type, DataType.STRING)
        self.assertEqual(dt1, DataType.SET(DataType.STRING))
        self.assertNotEqual(dt1, DataType.SET)
        self.assertNotEqual(dt1, DataType.SET(DataType.NULLABLE(DataType.STRING)))

    def test_data_type_value_type_nullable_kwarg_emits_deprecation(self):
        for constructor in (DataType.ARRAY, DataType.SET):
            with self.assertWarns(DeprecationWarning) as cm:
                wrapped = constructor(DataType.STRING, value_type_nullable=True)
            self.assertIn('value_type_nullable', str(cm.warning))
            self.assertIn('DataType.NULLABLE', str(cm.warning))
            self.assertIn('v6.0.0', str(cm.warning))
            self.assertEqual(wrapped.value_type, DataType.NULLABLE(DataType.STRING))
            self.assertTrue(wrapped.value_type_nullable)
            # false is deprecated too and leaves the type as it is
            with self.assertWarns(DeprecationWarning):
                unwrapped = constructor(DataType.STRING, value_type_nullable=False)
            self.assertIs(unwrapped.value_type, DataType.STRING)
            self.assertFalse(unwrapped.value_type_nullable)
        with self.assertWarns(DeprecationWarning) as cm:
            wrapped = DataType.MAPPING(DataType.STRING, DataType.STRING, value_type_nullable=True)
        self.assertIn('value_type_nullable', str(cm.warning))
        self.assertEqual(wrapped.value_type, DataType.NULLABLE(DataType.STRING))
        self.assertTrue(wrapped.value_type_nullable)
        with self.assertWarns(DeprecationWarning):
            unwrapped = DataType.MAPPING(DataType.STRING, DataType.STRING, value_type_nullable=False)
        self.assertIs(unwrapped.value_type, DataType.STRING)
        self.assertFalse(unwrapped.value_type_nullable)

    def test_data_type_value_type_nullable_property_derived(self):
        self.assertTrue(DataType.ARRAY(DataType.NULLABLE(DataType.STRING)).value_type_nullable)
        self.assertFalse(DataType.ARRAY(DataType.STRING).value_type_nullable)
        self.assertTrue(DataType.SET(DataType.NULLABLE(DataType.STRING)).value_type_nullable)
        self.assertFalse(DataType.SET(DataType.STRING).value_type_nullable)
        self.assertTrue(DataType.MAPPING(DataType.STRING, DataType.NULLABLE(DataType.STRING)).value_type_nullable)
        self.assertFalse(DataType.MAPPING(DataType.STRING, DataType.STRING).value_type_nullable)

    def test_data_type_value_type_nullable_kwarg_warns_at_caller(self):
        string = DataType.STRING
        for label, constructor in (
                ('ARRAY', lambda: DataType.ARRAY(string, value_type_nullable=True)),
                ('SET', lambda: DataType.SET(string, value_type_nullable=True)),
                ('MAPPING', lambda: DataType.MAPPING(string, string, value_type_nullable=True)),
                ('ARRAY class', lambda: type(DataType.ARRAY)('ARRAY', tuple, value_type=string, value_type_nullable=True)),
                ('SET class', lambda: type(DataType.SET)('SET', set, value_type=string, value_type_nullable=True)),
                ('MAPPING class', lambda: type(DataType.MAPPING)('MAPPING', dict, string, string, value_type_nullable=True)),
        ):
            with self.subTest(label):
                with self.assertWarns(DeprecationWarning) as cm:
                    constructor()
                self.assertEqual(cm.filename, __file__)
                self.assertEqual(cm.lineno, constructor.__code__.co_firstlineno)

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

    def test_data_type_pickle_compound(self):
        for data_type in (
                DataType.ARRAY,
                DataType.ARRAY(DataType.STRING),
                DataType.ARRAY(DataType.NULLABLE(DataType.STRING)),
                DataType.ARRAY(DataType.MAPPING(DataType.STRING, DataType.ARRAY(DataType.FLOAT))),
                DataType.SET,
                DataType.SET(DataType.FLOAT),
                DataType.SET(DataType.NULLABLE(DataType.STRING)),
                DataType.MAPPING,
                DataType.MAPPING(DataType.STRING),
                DataType.MAPPING(DataType.ARRAY(DataType.STRING), DataType.SET(DataType.DATETIME)),
                DataType.NULLABLE(DataType.ARRAY(DataType.STRING)),
                DataType.NULLABLE(DataType.MAPPING(DataType.STRING, DataType.NULLABLE(DataType.FLOAT))),
        ):
            for label, restored in _restore_data_type(data_type):
                with self.subTest(label, data_type=data_type):
                    self.assertEqual(restored, data_type)
                    self.assertEqual(hash(restored), hash(data_type))
                    self.assertEqual(repr(restored), repr(data_type))
                    self.assertEqual(restored.is_iterable, data_type.is_iterable)

    def test_data_type_pickle_compound_members(self):
        array_type = DataType.ARRAY(DataType.NULLABLE(DataType.STRING))
        for label, restored in _restore_data_type(array_type):
            with self.subTest(label):
                self.assertEqual(restored.value_type, DataType.NULLABLE(DataType.STRING))
                self.assertIs(restored.iterable_type, restored.value_type)
                self.assertTrue(restored.value_type_nullable)
        mapping_type = DataType.MAPPING(DataType.STRING, DataType.FLOAT)
        for label, restored in _restore_data_type(mapping_type):
            with self.subTest(label):
                self.assertEqual(restored.key_type, DataType.STRING)
                self.assertEqual(restored.value_type, DataType.FLOAT)
                self.assertIs(restored.iterable_type, restored.key_type)
                self.assertFalse(restored.value_type_nullable)
        # the ARRAY and SET definitions have a __dict__ too, it's restored like it is by default
        set_type = DataType.SET(DataType.STRING)
        set_type.comment = 'tags'
        for label, restored in _restore_data_type(set_type):
            with self.subTest(label):
                self.assertEqual(restored.comment, 'tags')

    def test_data_type_pickle_compound_undefined_members(self):
        # the type checks compare members to UNDEFINED by identity, a copy of it would make untyped members incompatible
        # with typed ones
        for data_type, typed_data_type in (
                (DataType.ARRAY, DataType.ARRAY(DataType.STRING)),
                (DataType.SET, DataType.SET(DataType.STRING)),
                (DataType.MAPPING, DataType.MAPPING(DataType.STRING, DataType.FLOAT)),
        ):
            for label, restored in _restore_data_type(data_type):
                with self.subTest(label, data_type=data_type):
                    self.assertIs(restored.value_type, DataType.UNDEFINED)
                    self.assertIs(restored.iterable_type, DataType.UNDEFINED)
                    self.assertTrue(DataType.is_compatible(restored, typed_data_type))

    def test_data_type_unpickle_compound_from_earlier_versions(self):
        # earlier versions could write this pickle of DataType.ARRAY but not load it, it holds a copy of UNDEFINED and
        # the iterable_type slot
        restored = pickle.loads(
                b'\x80\x02crule_engine.types.definitions\n_ArrayDataTypeDef\n)\x81N}(X\n\x00\x00\x00value_type'
                b'crule_engine.types.definitions\n_UndefinedDataTypeDef\n)\x81q\x00N}(X\x04\x00\x00\x00nameq\x01X\t\x00\x00'
                b'\x00UNDEFINEDX\x0b\x00\x00\x00python_typeq\x02crule_engine.errors\nUNDEFINED\nX\t\x00\x00\x00is_scalarq'
                b'\x03\x88u\x86bh\x01X\x05\x00\x00\x00ARRAYh\x02c__builtin__\ntuple\nh\x03\x89X\r\x00\x00\x00iterable_typeh'
                b'\x00u\x86b.'
        )
        self.assertEqual(restored, DataType.ARRAY)
        self.assertEqual(repr(restored), repr(DataType.ARRAY))
        self.assertIs(restored.value_type, DataType.UNDEFINED)
        self.assertTrue(DataType.is_compatible(restored, DataType.ARRAY(DataType.STRING)))

    def test_data_type_pickle_undefined_keeps_identity(self):
        for label, restored in _restore_data_type(DataType.UNDEFINED):
            with self.subTest(label):
                self.assertIs(restored, DataType.UNDEFINED)
                self.assertTrue(DataType.is_compatible(restored, DataType.STRING))
        function_type = DataType.FUNCTION('test', return_type=DataType.FLOAT)
        restored = copy.deepcopy(function_type)
        self.assertIs(restored.argument_types, DataType.UNDEFINED)
        self.assertIs(restored.minimum_arguments, DataType.UNDEFINED)
        object_type = DataType.OBJECT('Hero', attributes={'misc': DataType.UNDEFINED})
        for label, restored in _restore_data_type(object_type):
            with self.subTest(label):
                self.assertIs(restored.attributes['misc'], DataType.UNDEFINED)
        # a shallow copy still shares the attributes when there's nothing to replace
        self.assertIs(copy.copy(object_type).attributes, object_type.attributes)
        # another instance, like one from a pickle that an earlier version wrote, still pickles
        other = type(DataType.UNDEFINED)('UNDEFINED', errors.UNDEFINED)
        for label, restored in _restore_data_type(other):
            with self.subTest(label):
                self.assertEqual(restored, DataType.UNDEFINED)

    def test_data_type_pickle_constants_keep_identity(self):
        hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        for name in DataType:
            data_type = DataType[name]
            for label, restored in _restore_data_type(data_type):
                with self.subTest(label, name=name):
                    self.assertIs(restored, data_type)
                    self.assertTrue(DataType.is_type(restored, data_type))
        for label, restored in _restore_data_type(DataType.OBJECT):
            with self.subTest(label):
                # the bare OBJECT is compatible with every OBJECT schema
                self.assertTrue(DataType.is_compatible(restored, hero))
        for label, restored in _restore_data_type(DataType.ARRAY(DataType.STRING)):
            with self.subTest(label):
                self.assertIs(restored.value_type, DataType.STRING)
        # other instances that are equal to a constant are still copied
        for label, restored in _restore_data_type(types._DataTypeDef('STRING', str)):
            with self.subTest(label):
                self.assertEqual(restored, DataType.STRING)
                self.assertIsNot(restored, DataType.STRING)

    def test_data_type_pickle_names_that_are_not_constants(self):
        # the name isn't always a string, or even set
        unnamed = types._DataTypeDef.__new__(types._DataTypeDef)
        unnamed.python_type = str
        for data_type in (
                DataType.OBJECT(None),
                DataType.OBJECT(1),
                DataType.OBJECT(['STRING']),
                types._DataTypeDef(None, str),
                DataType.OBJECT.reference(None),
                unnamed,
        ):
            for label, restored in _restore_data_type(data_type):
                with self.subTest(label, data_type=type(data_type).__name__):
                    self.assertIsNot(restored, data_type)
                    self.assertIs(type(restored), type(data_type))
                    self.assertEqual(getattr(restored, 'name', 'unset'), getattr(data_type, 'name', 'unset'))

    def test_data_type_pickle_function(self):
        Hero = DataType.OBJECT('Hero', attributes={
                'promote': DataType.FUNCTION('promote', return_type=DataType.OBJECT.self, argument_types=(DataType.STRING,)),
        })
        for data_type in (
                DataType.FUNCTION('test'),
                DataType.FUNCTION('test', return_type=DataType.FLOAT, argument_types=(DataType.STRING, DataType.ARRAY), minimum_arguments=1),
                DataType.ARRAY(DataType.FUNCTION('test', return_type=DataType.NULLABLE(DataType.STRING))),
                Hero,
        ):
            for label, restored in _restore_data_type(data_type):
                with self.subTest(label, data_type=data_type):
                    self.assertEqual(restored, data_type)
                    self.assertEqual(hash(restored), hash(data_type))
                    self.assertEqual(repr(restored), repr(data_type))
        for label, restored in _restore_data_type(Hero):
            with self.subTest(label):
                promote = restored.attributes['promote']
                self.assertIs(promote.python_type, DataType.FUNCTION.python_type)
                self.assertEqual(promote.value_name, 'promote')
                if label != 'copy':
                    self.assertIs(promote.return_type, restored)
        # a FUNCTION definition with another python_type keeps it
        function_type = types._FunctionDataTypeDef('FUNCTION', collections.OrderedDict, value_name='test')
        for label, restored in _restore_data_type(function_type):
            with self.subTest(label):
                self.assertEqual(restored, function_type)
                self.assertIs(restored.python_type, collections.OrderedDict)

    def test_data_type_pickle_function_with_dict(self):
        for python_type in (DataType.FUNCTION.python_type, collections.OrderedDict):
            function_type = _FunctionDataTypeWithDict('FUNCTION', python_type, value_name='test')
            function_type.comment = 'note'
            for label, restored in _restore_data_type(function_type):
                with self.subTest(label, python_type=python_type.__name__):
                    self.assertIs(type(restored), _FunctionDataTypeWithDict)
                    self.assertIs(restored.python_type, python_type)
                    self.assertEqual(restored.comment, 'note')
                    self.assertEqual(restored, function_type)

    def test_data_type_pickle_undefined_copies_replaced(self):
        # pickles that earlier versions wrote hold copies of UNDEFINED, wherever a data type can hold one
        other = type(DataType.UNDEFINED)('UNDEFINED', errors.UNDEFINED)
        object_type = DataType.OBJECT('Hero', attributes={'misc': other, 'name': DataType.STRING})
        nullable_type = type(DataType.NULLABLE)('NULLABLE', object, inner_type=other)
        for label, restored in _restore_data_type(object_type):
            with self.subTest(label):
                self.assertIs(restored.attributes['misc'], DataType.UNDEFINED)
                self.assertEqual(restored.attributes['name'], DataType.STRING)
        for label, restored in _restore_data_type(nullable_type):
            with self.subTest(label):
                self.assertIs(restored.inner_type, DataType.UNDEFINED)
        function_type = DataType.FUNCTION('test', return_type=other, argument_types=(other, DataType.STRING))
        for label, restored in (('copy', copy.copy(function_type)), ('deepcopy', copy.deepcopy(function_type))):
            with self.subTest(label):
                self.assertIs(restored.return_type, DataType.UNDEFINED)
                self.assertEqual(restored.argument_types, (DataType.UNDEFINED, DataType.STRING))
                self.assertIs(restored.argument_types[0], DataType.UNDEFINED)

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

class NullableDataTypeTests(unittest.TestCase):
    def test_nullable_construction(self):
        dt = DataType.NULLABLE(DataType.STRING)
        self.assertIsInstance(dt, types._NullableDataTypeDef)
        self.assertIs(dt.inner_type, DataType.STRING)
        self.assertFalse(dt.is_scalar)
        self.assertTrue(dt.is_compound)

    def test_nullable_equality(self):
        self.assertEqual(DataType.NULLABLE(DataType.STRING), DataType.NULLABLE(DataType.STRING))
        self.assertNotEqual(DataType.NULLABLE(DataType.STRING), DataType.NULLABLE(DataType.FLOAT))
        self.assertNotEqual(DataType.NULLABLE(DataType.STRING), DataType.STRING)
        self.assertNotEqual(DataType.NULLABLE(DataType.STRING), DataType.NULL)

    def test_nullable_hash(self):
        self.assertEqual(hash(DataType.NULLABLE(DataType.STRING)), hash(DataType.NULLABLE(DataType.STRING)))
        seen = {DataType.NULLABLE(DataType.STRING), DataType.NULLABLE(DataType.STRING)}
        self.assertEqual(len(seen), 1)

    def test_nullable_repr_names_inner_type(self):
        self.assertIn('STRING', repr(DataType.NULLABLE(DataType.STRING)))

    def test_nullable_collapses_double_wrap(self):
        # NULLABLE(NULLABLE(T)) == NULLABLE(T)
        once = DataType.NULLABLE(DataType.STRING)
        twice = DataType.NULLABLE(once)
        self.assertEqual(twice, once)
        self.assertIs(twice.inner_type, DataType.STRING)

    def test_nullable_rejects_null_inner_type(self):
        with self.assertRaises(errors.EngineError):
            DataType.NULLABLE(DataType.NULL)

    def test_nullable_rejects_undefined_inner_type(self):
        with self.assertRaises(errors.EngineError):
            DataType.NULLABLE(DataType.UNDEFINED)

    def test_nullable_is_compatible_with_inner_type(self):
        self.assertTrue(DataType.is_compatible(DataType.NULLABLE(DataType.STRING), DataType.STRING))
        self.assertTrue(DataType.is_compatible(DataType.STRING, DataType.NULLABLE(DataType.STRING)))

    def test_nullable_is_compatible_with_null(self):
        self.assertTrue(DataType.is_compatible(DataType.NULLABLE(DataType.STRING), DataType.NULL))
        self.assertTrue(DataType.is_compatible(DataType.NULL, DataType.NULLABLE(DataType.STRING)))

    def test_nullable_is_compatible_with_matching_nullable(self):
        self.assertTrue(DataType.is_compatible(
                DataType.NULLABLE(DataType.STRING),
                DataType.NULLABLE(DataType.STRING)
        ))

    def test_nullable_is_not_compatible_with_mismatched_inner(self):
        self.assertFalse(DataType.is_compatible(
                DataType.NULLABLE(DataType.STRING),
                DataType.NULLABLE(DataType.FLOAT)
        ))
        self.assertFalse(DataType.is_compatible(DataType.NULLABLE(DataType.STRING), DataType.FLOAT))

    def test_nullable_is_compatible_with_undefined(self):
        self.assertTrue(DataType.is_compatible(DataType.NULLABLE(DataType.STRING), DataType.UNDEFINED))
        self.assertTrue(DataType.is_compatible(DataType.UNDEFINED, DataType.NULLABLE(DataType.STRING)))

    def test_nullable_is_compatible_nested_inside_array(self):
        self.assertTrue(DataType.is_compatible(
                DataType.ARRAY(DataType.NULLABLE(DataType.STRING)),
                DataType.ARRAY(DataType.NULLABLE(DataType.STRING))
        ))
        self.assertTrue(DataType.is_compatible(
                DataType.ARRAY(DataType.NULLABLE(DataType.STRING)),
                DataType.ARRAY(DataType.STRING)
        ))

    def test_nullable_from_type_optional(self):
        self.assertEqual(DataType.from_type(typing.Optional[str]), DataType.NULLABLE(DataType.STRING))

    def test_nullable_from_type_pep604_union(self):
        self.assertEqual(DataType.from_type(str | None), DataType.NULLABLE(DataType.STRING))
        self.assertEqual(DataType.from_type(None | str), DataType.NULLABLE(DataType.STRING))

    def test_nullable_from_type_nested_generic(self):
        self.assertEqual(DataType.from_type(list[int | None]), DataType.ARRAY(DataType.NULLABLE(DataType.FLOAT)))

    def test_nullable_from_type_rejects_multi_member_union(self):
        with self.assertRaises(ValueError):
            DataType.from_type(str | int)
        with self.assertRaises(ValueError):
            DataType.from_type(typing.Union[str, int, None])

    def test_nullable_from_value_never_returns_nullable(self):
        # NULLABLE is a type-hint-only construct; runtime None resolves to NULL
        self.assertIs(DataType.from_value(None), DataType.NULL)

    def test_nullable_bare_is_in_data_type_members(self):
        self.assertIn('NULLABLE', DataType)
        self.assertIs(DataType.from_name('NULLABLE'), DataType.NULLABLE)

@dataclasses.dataclass
class _SelfRefHero:
    name: str
    nemesis: typing.Optional['_SelfRefHero'] = None

@dataclasses.dataclass
class _ArraySelfRefHero:
    name: str
    sidekicks: list['_ArraySelfRefHero'] = dataclasses.field(default_factory=list)

@dataclasses.dataclass
class _MappingSelfRefHero:
    name: str
    allies: dict[str, '_MappingSelfRefHero'] = dataclasses.field(default_factory=dict)

@dataclasses.dataclass
class _MutualPerson:
    name: str
    employer: '_MutualCompany'

@dataclasses.dataclass
class _MutualCompany:
    name: str
    ceo: _MutualPerson

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
        left = DataType.OBJECT('Hero', attributes={'name': DataType.NULLABLE(DataType.STRING)})
        right = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
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

    def test_nullable_object_set_rejection(self):
        Hero = DataType.OBJECT('Hero', attributes={'name': DataType.STRING})
        with self.assertRaises(errors.EngineError):
            DataType.SET(DataType.NULLABLE(Hero))

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

    def test_object_from_dataclass_flat(self):
        @dataclasses.dataclass
        class Hero:
            name: str
            age: int
            first_appearance: datetime.datetime

        Wookiee = DataType.OBJECT.from_dataclass('Hero', Hero)
        self.assertEqual(Wookiee.name, 'Hero')
        self.assertIs(Wookiee.attributes['name'], DataType.STRING)
        self.assertIs(Wookiee.attributes['age'], DataType.FLOAT)
        self.assertIs(Wookiee.attributes['first_appearance'], DataType.DATETIME)
        self.assertIs(Wookiee.accessor, getattr)

    def test_object_from_dataclass_with_generics(self):
        @dataclasses.dataclass
        class Roster:
            heroes: list[str]
            scores: dict[str, int]
            tags: set[str]

        result = DataType.OBJECT.from_dataclass('Roster', Roster)
        self.assertEqual(result.attributes['heroes'], DataType.ARRAY(DataType.STRING))
        self.assertEqual(result.attributes['scores'], DataType.MAPPING(DataType.STRING, DataType.FLOAT))
        self.assertEqual(result.attributes['tags'], DataType.SET(DataType.STRING))

    def test_object_from_dataclass_custom_accessor(self):
        @dataclasses.dataclass
        class Hero:
            name: str

        def dict_getter(obj, name):
            return obj[name]

        result = DataType.OBJECT.from_dataclass('Hero', Hero, accessor=dict_getter)
        self.assertIs(result.accessor, dict_getter)

    def test_object_from_dataclass_rejects_non_dataclass(self):
        class NotADataclass:
            name: str

        with self.assertRaisesRegex(TypeError, r'^from_dataclass argument 2 must be a dataclass'):
            DataType.OBJECT.from_dataclass('Hero', NotADataclass)

    def test_object_from_dataclass_resolves_stringified_annotations(self):
        # exercise typing.get_type_hints for fields whose annotations are strings (e.g. PEP 563)
        @dataclasses.dataclass
        class Hero:
            name: 'str'
            age: 'int'

        result = DataType.OBJECT.from_dataclass('Hero', Hero)
        self.assertIs(result.attributes['name'], DataType.STRING)
        self.assertIs(result.attributes['age'], DataType.FLOAT)

    def test_object_from_dataclass_optional_typing(self):
        @dataclasses.dataclass
        class Hero:
            name: str
            alias: typing.Optional[str]
            sidekick: typing.Union[str, None]

        result = DataType.OBJECT.from_dataclass('Hero', Hero)
        self.assertIs(result.attributes['name'], DataType.STRING)
        self.assertEqual(result.attributes['alias'], DataType.NULLABLE(DataType.STRING))
        self.assertEqual(result.attributes['sidekick'], DataType.NULLABLE(DataType.STRING))

    def test_object_from_dataclass_optional_pep604(self):
        @dataclasses.dataclass
        class Hero:
            name: str
            alias: str | None

        result = DataType.OBJECT.from_dataclass('Hero', Hero)
        self.assertIs(result.attributes['name'], DataType.STRING)
        self.assertEqual(result.attributes['alias'], DataType.NULLABLE(DataType.STRING))

    def test_object_from_dataclass_rejects_unsupported_union(self):
        @dataclasses.dataclass
        class Bad:
            value: typing.Union[str, int]

        with self.assertRaises((TypeError, ValueError)):
            DataType.OBJECT.from_dataclass('Bad', Bad)

    def test_object_from_dataclass_nested(self):
        @dataclasses.dataclass
        class Address:
            city: str

        @dataclasses.dataclass
        class Person:
            name: str
            address: Address

        result = DataType.OBJECT.from_dataclass('Person', Person)
        nested = result.attributes['address']
        self.assertIsInstance(nested, types._ObjectDataTypeDef)
        self.assertEqual(nested.name, 'Address')
        self.assertIs(nested.attributes['city'], DataType.STRING)

    def test_object_from_dataclass_self_reference(self):
        result = DataType.OBJECT.from_dataclass('Hero', _SelfRefHero)
        # nemesis is Optional[_SelfRefHero], so the walker wraps the self-reference in NULLABLE
        nemesis = result.attributes['nemesis']
        self.assertIsInstance(nemesis, types._NullableDataTypeDef)
        self.assertIs(nemesis.inner_type, result)

    def test_object_from_dataclass_self_reference_in_array(self):
        result = DataType.OBJECT.from_dataclass('Hero', _ArraySelfRefHero)
        self.assertIsInstance(result.attributes['sidekicks'], types._ArrayDataTypeDef)
        self.assertIs(result.attributes['sidekicks'].value_type, result)

    def test_object_from_dataclass_self_reference_in_mapping(self):
        result = DataType.OBJECT.from_dataclass('Hero', _MappingSelfRefHero)
        allies = result.attributes['allies']
        self.assertIsInstance(allies, types._MappingDataTypeDef)
        self.assertIs(allies.key_type, DataType.STRING)
        self.assertIs(allies.value_type, result)

    def test_object_from_dataclass_mutual_recursion(self):
        result = DataType.OBJECT.from_dataclass('Person', _MutualPerson)
        company = result.attributes['employer']
        self.assertIsInstance(company, types._ObjectDataTypeDef)
        self.assertEqual(company.name, '_MutualCompany')
        # the deeper Person reference inside Company is left unresolved for the
        # type_resolver to fill in at parse time; the placeholder carries the
        # *root* OBJECT name supplied by the caller, not the dataclass class name
        ceo_ref = company.attributes['ceo']
        self.assertIsInstance(ceo_ref, types._ReferenceDataTypeDef)
        self.assertEqual(ceo_ref.name, 'Person')

    def test_object_from_dataclass_optional_nested(self):
        @dataclasses.dataclass
        class Address:
            city: str

        @dataclasses.dataclass
        class Person:
            name: str
            address: typing.Optional[Address]

        result = DataType.OBJECT.from_dataclass('Person', Person)
        address = result.attributes['address']
        self.assertIsInstance(address, types._NullableDataTypeDef)
        nested = address.inner_type
        self.assertIsInstance(nested, types._ObjectDataTypeDef)
        self.assertEqual(nested.name, 'Address')

    def test_object_from_dataclass_unsupported_type_strict(self):
        import uuid
        @dataclasses.dataclass
        class Hero:
            name: str
            identifier: uuid.UUID

        with self.assertRaises((TypeError, ValueError)):
            DataType.OBJECT.from_dataclass('Hero', Hero)

    def test_object_from_dataclass_unsupported_type_non_strict(self):
        import uuid
        @dataclasses.dataclass
        class Hero:
            name: str
            identifier: uuid.UUID

        result = DataType.OBJECT.from_dataclass('Hero', Hero, strict=False)
        self.assertIs(result.attributes['name'], DataType.STRING)
        self.assertIs(result.attributes['identifier'], DataType.UNDEFINED)

    def test_object_pickle_with_compound_attributes(self):
        Hero = DataType.OBJECT('Hero', attributes={
                'name': DataType.STRING,
                'aliases': DataType.SET(DataType.STRING),
                'sidekicks': DataType.ARRAY(DataType.OBJECT.self),
                'allies': DataType.MAPPING(DataType.STRING, DataType.NULLABLE(DataType.OBJECT.self)),
                'scores': DataType.NULLABLE(DataType.ARRAY(DataType.FLOAT)),
                'employers': DataType.ARRAY(DataType.OBJECT.reference('Company')),
                'notes': DataType.ARRAY,
        })
        for label, restored in _restore_data_type(Hero):
            with self.subTest(label):
                self.assertEqual(restored, Hero)
                self.assertEqual(hash(restored), hash(Hero))
                self.assertEqual(repr(restored), repr(Hero))
                for name, attribute_type in Hero.attributes.items():
                    self.assertEqual(restored.attributes[name], attribute_type)
                    self.assertEqual(repr(restored.attributes[name]), repr(attribute_type))
                self.assertIs(restored.attributes['notes'].value_type, DataType.UNDEFINED)
                if label != 'copy':
                    # the self references point at the restored schema, not the original
                    self.assertIs(restored.attributes['sidekicks'].value_type, restored)
                    self.assertIs(restored.attributes['allies'].value_type.inner_type, restored)

    def test_object_pickle_recursive_dataclass(self):
        for name, cls in (('Hero', _ArraySelfRefHero), ('Hero', _MappingSelfRefHero), ('Person', _MutualPerson)):
            data_type = DataType.OBJECT.from_dataclass(name, cls)
            for label, restored in _restore_data_type(data_type):
                with self.subTest(label, cls=cls.__name__):
                    self.assertEqual(restored, data_type)
                    self.assertEqual(hash(restored), hash(data_type))
                    self.assertEqual(repr(restored), repr(data_type))

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
