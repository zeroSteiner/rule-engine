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
import unittest

import rule_engine.types as types

__all__ = ('DataTypeTests', 'MetaDataTypeTests', 'ValueIsTests')

DataType = types.DataType

class DataTypeTests(unittest.TestCase):
	class _UnsupportedType(object):
		pass

	def test_data_type_equality(self):
		dt1 = DataType.ARRAY(DataType.STRING)
		self.assertIs(dt1.value_type, DataType.STRING)
		self.assertEqual(dt1, DataType.ARRAY(DataType.STRING))
		self.assertNotEqual(dt1, DataType.ARRAY)
		self.assertNotEqual(dt1, DataType.ARRAY(DataType.STRING, value_type_nullable=False))

		dt1 = DataType.MAPPING(DataType.STRING)
		self.assertIs(dt1.key_type, DataType.STRING)
		self.assertEqual(dt1, DataType.MAPPING(DataType.STRING))
		self.assertNotEqual(dt1, DataType.MAPPING)
		self.assertNotEqual(dt1, DataType.MAPPING(DataType.STRING, value_type=DataType.STRING))
		self.assertNotEqual(dt1, DataType.MAPPING(DataType.STRING, value_type_nullable=False))

		dt1 = DataType.SET(DataType.STRING)
		self.assertIs(dt1.value_type, DataType.STRING)
		self.assertEqual(dt1, DataType.SET(DataType.STRING))
		self.assertNotEqual(dt1, DataType.SET)
		self.assertNotEqual(dt1, DataType.SET(DataType.STRING, value_type_nullable=False))

	def test_data_type_from_name(self):
		self.assertIs(DataType.from_name('ARRAY'), DataType.ARRAY)
		self.assertIs(DataType.from_name('BOOLEAN'), DataType.BOOLEAN)
		self.assertIs(DataType.from_name('DATETIME'), DataType.DATETIME)
		self.assertIs(DataType.from_name('TIMEDELTA'), DataType.TIMEDELTA)
		self.assertIs(DataType.from_name('FLOAT'), DataType.FLOAT)
		self.assertIs(DataType.from_name('MAPPING'), DataType.MAPPING)
		self.assertIs(DataType.from_name('NULL'), DataType.NULL)
		self.assertIs(DataType.from_name('SET'), DataType.SET)
		self.assertIs(DataType.from_name('STRING'), DataType.STRING)

	def test_data_type_from_name_error(self):
		with self.assertRaises(TypeError):
			DataType.from_name(1)
		with self.assertRaises(ValueError):
			DataType.from_name('FOOBAR')

	def test_data_type_from_type(self):
		self.assertIs(DataType.from_type(list), DataType.ARRAY)
		self.assertIs(DataType.from_type(tuple), DataType.ARRAY)
		self.assertIs(DataType.from_type(bool), DataType.BOOLEAN)
		self.assertIs(DataType.from_type(datetime.date), DataType.DATETIME)
		self.assertIs(DataType.from_type(datetime.datetime), DataType.DATETIME)
		self.assertIs(DataType.from_type(datetime.timedelta), DataType.TIMEDELTA)
		self.assertIs(DataType.from_type(float), DataType.FLOAT)
		self.assertIs(DataType.from_type(int), DataType.FLOAT)
		self.assertIs(DataType.from_type(dict), DataType.MAPPING)
		self.assertIs(DataType.from_type(type(None)), DataType.NULL)
		self.assertIs(DataType.from_type(set), DataType.SET)
		self.assertIs(DataType.from_type(str), DataType.STRING)

	def test_data_type_from_type_error(self):
		with self.assertRaisesRegex(TypeError, r'^from_type argument 1 must be type, not _UnsupportedType$'):
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
		self.assertEqual(DataType.from_value(False), DataType.BOOLEAN)
		self.assertEqual(DataType.from_value(datetime.date.today()), DataType.DATETIME)
		self.assertEqual(DataType.from_value(datetime.datetime.now()), DataType.DATETIME)
		self.assertEqual(DataType.from_value(datetime.timedelta()), DataType.TIMEDELTA)
		self.assertEqual(DataType.from_value(0), DataType.FLOAT)
		self.assertEqual(DataType.from_value(0.0), DataType.FLOAT)
		self.assertEqual(DataType.from_value(None), DataType.NULL)
		self.assertEqual(DataType.from_value(''), DataType.STRING)

	def test_data_type_from_value_error(self):
		with self.assertRaisesRegex(TypeError, r'^can not map python type \'_UnsupportedType\' to a compatible data type$'):
			DataType.from_value(self._UnsupportedType())

	def test_data_type_definitions_describe_themselves(self):
		for name in ('ARRAY', 'BOOLEAN', 'DATETIME', 'TIMEDELTA', 'FLOAT', 'MAPPING', 'NULL', 'SET', 'STRING', 'UNDEFINED'):
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

	def test_data_type_is_definition(self):
		self.assertTrue(DataType.is_definition(DataType.ARRAY))
		self.assertFalse(DataType.is_definition(1))
		self.assertFalse(DataType.is_definition(None))

	def test_data_type_supports_contains(self):
		self.assertIn('STRING', DataType)

	def test_data_type_supports_getitem(self):
		dt = DataType['STRING']
		self.assertEqual(dt, DataType.STRING)

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
