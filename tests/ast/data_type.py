#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/ast/data_type.py
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
import unittest

import rule_engine.ast as ast

__all__ = ('DataTypeTests', 'MetaDataTypeTests')

class DataTypeTests(unittest.TestCase):
	class _UnsupportedType(object):
		pass

	def test_data_type_from_name(self):
		self.assertIs(ast.DataType.from_name('BOOLEAN'), ast.DataType.BOOLEAN)
		self.assertIs(ast.DataType.from_name('DATETIME'), ast.DataType.DATETIME)
		self.assertIs(ast.DataType.from_name('FLOAT'), ast.DataType.FLOAT)
		self.assertIs(ast.DataType.from_name('NULL'), ast.DataType.NULL)
		self.assertIs(ast.DataType.from_name('STRING'), ast.DataType.STRING)

	def test_data_type_from_name_error(self):
		with self.assertRaises(TypeError):
			ast.DataType.from_name(1)
		with self.assertRaises(ValueError):
			ast.DataType.from_name('FOOBAR')

	def test_data_type_from_type(self):
		self.assertIs(ast.DataType.from_type(list), ast.DataType.ARRAY)
		self.assertIs(ast.DataType.from_type(tuple), ast.DataType.ARRAY)
		self.assertIs(ast.DataType.from_type(bool), ast.DataType.BOOLEAN)
		self.assertIs(ast.DataType.from_type(datetime.date), ast.DataType.DATETIME)
		self.assertIs(ast.DataType.from_type(datetime.datetime), ast.DataType.DATETIME)
		self.assertIs(ast.DataType.from_type(float), ast.DataType.FLOAT)
		self.assertIs(ast.DataType.from_type(int), ast.DataType.FLOAT)
		self.assertIs(ast.DataType.from_type(type(None)), ast.DataType.NULL)
		self.assertIs(ast.DataType.from_type(str), ast.DataType.STRING)

	def test_data_type_from_type_error(self):
		with self.assertRaisesRegex(TypeError, r'^from_type argument 1 must be type, not _UnsupportedType$'):
			ast.DataType.from_type(self._UnsupportedType())
		with self.assertRaisesRegex(ValueError, r'^can not map python type \'_UnsupportedType\' to a compatible data type$'):
			ast.DataType.from_type(self._UnsupportedType)

	def test_data_type_from_value_compound(self):
		for value in [list(), range(0), tuple()]:
			value = ast.DataType.from_value(value)
			self.assertEqual(value, ast.DataType.ARRAY)
			self.assertIs(value.value_type, ast.DataType.UNDEFINED)
		value = ast.DataType.from_value(['test'])
		self.assertEqual(value, ast.DataType.ARRAY(ast.DataType.STRING))
		self.assertIs(value.value_type, ast.DataType.STRING)

	def test_data_type_from_value_compound_error(self):
		with self.assertRaises(TypeError):
			ast.DataType.from_value([1.0, 'error'])

	def test_data_type_from_value_scalar(self):
		self.assertEqual(ast.DataType.from_value(False), ast.DataType.BOOLEAN)
		self.assertEqual(ast.DataType.from_value(datetime.date.today()), ast.DataType.DATETIME)
		self.assertEqual(ast.DataType.from_value(datetime.datetime.now()), ast.DataType.DATETIME)
		self.assertEqual(ast.DataType.from_value(0), ast.DataType.FLOAT)
		self.assertEqual(ast.DataType.from_value(0.0), ast.DataType.FLOAT)
		self.assertEqual(ast.DataType.from_value(None), ast.DataType.NULL)
		self.assertEqual(ast.DataType.from_value(''), ast.DataType.STRING)

	def test_data_type_from_value_error(self):
		with self.assertRaisesRegex(TypeError, r'^can not map python type \'_UnsupportedType\' to a compatible data type$'):
			ast.DataType.from_value(self._UnsupportedType())

	def test_data_type_definitions_describe_themselves(self):
		for name in ('ARRAY', 'BOOLEAN', 'DATETIME', 'FLOAT', 'NULL', 'STRING', 'UNDEFINED'):
			data_type = getattr(ast.DataType, name)
			self.assertRegex(repr(data_type), 'name=' + name)

class MetaDataTypeTests(unittest.TestCase):
	def test_data_type_is_iterable(self):
		self.assertGreater(len(ast.DataType), 0)
		for name in ast.DataType:
			self.assertIsInstance(name, str)
			self.assertRegex(name, r'^[A-Z]+$')

	def test_data_type_is_compatible(self):
		def _is_compat(*args):
			return self.assertTrue(ast.DataType.is_compatible(*args))
		def _is_not_compat(*args):
			return self.assertFalse(ast.DataType.is_compatible(*args))
		_is_compat(ast.DataType.STRING, ast.DataType.STRING)
		_is_compat(ast.DataType.STRING, ast.DataType.UNDEFINED)
		_is_compat(ast.DataType.UNDEFINED, ast.DataType.STRING)

		_is_compat(ast.DataType.UNDEFINED, ast.DataType.ARRAY)
		_is_compat(ast.DataType.ARRAY, ast.DataType.ARRAY(ast.DataType.STRING))

		_is_not_compat(ast.DataType.STRING, ast.DataType.ARRAY)
		_is_not_compat(ast.DataType.STRING, ast.DataType.NULL)
		_is_not_compat(ast.DataType.ARRAY(ast.DataType.STRING), ast.DataType.ARRAY(ast.DataType.FLOAT))

		with self.assertRaises(TypeError):
			ast.DataType.is_compatible(ast.DataType.STRING, None)

	def test_data_type_is_definition(self):
		self.assertTrue(ast.DataType.is_definition(ast.DataType.ARRAY))
		self.assertFalse(ast.DataType.is_definition(1))
		self.assertFalse(ast.DataType.is_definition(None))

	def test_data_type_supports_contains(self):
		self.assertIn('STRING', ast.DataType)

	def test_data_type_supports_getitem(self):
		dt = ast.DataType['STRING']
		self.assertEqual(dt, ast.DataType.STRING)

if __name__ == '__main__':
	unittest.main()
