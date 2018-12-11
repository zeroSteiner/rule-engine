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

__all__ = ('DataTypeTests',)

class DataTypeTests(unittest.TestCase):
	class _UnsupportedType(object):
		pass

	def test_datatype_from_type(self):
		self.assertIs(ast.DataType.from_type(bool), ast.DataType.BOOLEAN)
		self.assertIs(ast.DataType.from_type(datetime.date), ast.DataType.DATETIME)
		self.assertIs(ast.DataType.from_type(datetime.datetime), ast.DataType.DATETIME)
		self.assertIs(ast.DataType.from_type(float), ast.DataType.FLOAT)
		self.assertIs(ast.DataType.from_type(int), ast.DataType.FLOAT)
		self.assertIs(ast.DataType.from_type(str), ast.DataType.STRING)

	def test_datatype_from_type_exceptions(self):
		with self.assertRaisesRegex(TypeError, r'^from_type argument 1 must be type, not _UnsupportedType$'):
			ast.DataType.from_type(self._UnsupportedType())
		with self.assertRaisesRegex(ValueError, r'^can not map python type \'_UnsupportedType\' to a compatible data type$'):
			ast.DataType.from_type(self._UnsupportedType)

	def test_datatype_from_value(self):
		self.assertIs(ast.DataType.from_value(False), ast.DataType.BOOLEAN)
		self.assertIs(ast.DataType.from_value(datetime.date.today()), ast.DataType.DATETIME)
		self.assertIs(ast.DataType.from_value(datetime.datetime.now()), ast.DataType.DATETIME)
		self.assertIs(ast.DataType.from_value(0), ast.DataType.FLOAT)
		self.assertIs(ast.DataType.from_value(0.0), ast.DataType.FLOAT)
		self.assertIs(ast.DataType.from_value(''), ast.DataType.STRING)

	def test_datatype_from_value_exceptions(self):
		with self.assertRaisesRegex(TypeError, r'^can not map python type \'_UnsupportedType\' to a compatible data type$'):
			ast.DataType.from_value(self._UnsupportedType())

if __name__ == '__main__':
	unittest.main()
