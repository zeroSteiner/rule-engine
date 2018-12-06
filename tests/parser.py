#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/parser.py
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

import math
import unittest

import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.parser as parser

class ParserTests(unittest.TestCase):
	_parser = parser.Parser()
	context = engine.Context()
	def _parse(self, string, context):
		return self._parser.parse(string, self.context)

	def test_parser_order_of_operations(self):
		cases = (
			'100 * ( 2 + 12 ) / 14',
			'50 + 50 * 2 - 50',
			'19 + 9 ** 2',
			'(4 * 5) ** 2 / 4'
		)
		for case in cases:
			statement = self._parse(case, self.context)
			self.assertIsInstance(statement.expression, ast.FloatExpression)
			self.assertEqual(statement.evaluate(None), 100)

	def test_parser_returns_statement(self):
		expression = self._parse('true', self.context)
		self.assertIsInstance(expression, ast.Statement)

class ParserLiteralTests(ParserTests):
	def assertLiteralStatementEqual(self, string, ast_type, python_value, msg=None):
		msg = msg or "{0!r} does not evaluate to {1!r}".format(string, python_value)
		statement = self._parse(string, self.context)
		self.assertIsInstance(statement, ast.Statement, msg='the parser did not return a statement')
		self.assertIsInstance(statement.expression, ast_type, msg='the statement expression is not the correct literal type')
		self.assertEqual(statement.expression.value, python_value, msg=msg)

	def test_parse_boolean(self):
		self.assertLiteralStatementEqual('true', ast.BooleanExpression, True)
		self.assertLiteralStatementEqual('false', ast.BooleanExpression, False)

	def test_parse_float(self):
		self.assertLiteralStatementEqual('3.14', ast.FloatExpression, 3.14)
		self.assertLiteralStatementEqual('3.140', ast.FloatExpression, 3.140)
		self.assertLiteralStatementEqual('.314', ast.FloatExpression, 0.314)
		self.assertLiteralStatementEqual('0.314', ast.FloatExpression, 0.314)

	def test_parse_float_exponent(self):
		self.assertLiteralStatementEqual('3.14e5', ast.FloatExpression, 314000.0)
		self.assertLiteralStatementEqual('3.14e+3', ast.FloatExpression, 3140.0)
		self.assertLiteralStatementEqual('3.14e-3', ast.FloatExpression, 0.00314)
		self.assertLiteralStatementEqual('3.14E5', ast.FloatExpression, 314000.0)
		self.assertLiteralStatementEqual('3.14E+3', ast.FloatExpression, 3140.0)
		self.assertLiteralStatementEqual('3.14E-3', ast.FloatExpression, 0.00314)

	def test_parse_float_base_2(self):
		self.assertLiteralStatementEqual('0b00', ast.FloatExpression, 0)
		self.assertLiteralStatementEqual('0b11', ast.FloatExpression, 3)

	def test_parse_float_base_8(self):
		self.assertLiteralStatementEqual('0o00', ast.FloatExpression, 0)
		self.assertLiteralStatementEqual('0o77', ast.FloatExpression, 63)

	def test_parse_float_base_10(self):
		self.assertLiteralStatementEqual('00', ast.FloatExpression, 0)
		self.assertLiteralStatementEqual('99', ast.FloatExpression, 99)

	def test_parse_float_base_16(self):
		self.assertLiteralStatementEqual('0x00', ast.FloatExpression, 0)
		self.assertLiteralStatementEqual('0xdeadbeef', ast.FloatExpression, 3735928559)
		self.assertLiteralStatementEqual('0xdeADbeEF', ast.FloatExpression, 3735928559)

	def test_parse_float_inf(self):
		self.assertLiteralStatementEqual('inf', ast.FloatExpression, float('inf'))

	def test_parse_float_nan(self):
		statement = self._parse('nan', self.context)
		self.assertIsInstance(statement, ast.Statement, msg='the parser did not return a statement')
		self.assertIsInstance(statement.expression, ast.FloatExpression, msg='the statement expression is not the correct literal type')
		self.assertTrue(math.isnan(statement.expression.value), msg='the statement expression is not nan')

	def test_parse_string(self):
		self.assertLiteralStatementEqual("'Alice'", ast.StringExpression, 'Alice')
		self.assertLiteralStatementEqual('"Alice"', ast.StringExpression, 'Alice')

	def test_parse_string_escapes(self):
		self.assertLiteralStatementEqual("'Alice\\\'s'", ast.StringExpression, 'Alice\'s')
		self.assertLiteralStatementEqual('"Alice\'s"', ast.StringExpression, 'Alice\'s')

if __name__ == '__main__':
	unittest.main()
