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
	context = engine.Context()
	def test_parser_order_of_operations(self):
		parser_ = parser.Parser()
		cases = (
			'100 * ( 2 + 12 ) / 14',
			'50 + 50 * 2 - 50',
			'19 + 9 ** 2',
			'(4 * 5) ** 2 / 4'
		)
		for case in cases:
			statement = parser_.parse(case, self.context)
			self.assertIsInstance(statement.expression, ast.FloatExpression)
			self.assertEqual(statement.evaluate(None), 100)

	def test_parser_returns_statement(self):
		parser_ = parser.Parser()
		expression = parser_.parse('true', self.context)
		self.assertIsInstance(expression, ast.Statement)

class ParserLiteralTests(ParserTests):
	def _evaluate(self, string):
		parser_ = parser.Parser()
		statement = parser_.parse(string, self.context)
		return statement.evaluate({})

	def assertLiteralStatementEqual(self, string, value, msg=None):
		msg = msg or "{0!r} does not evaluate to {1!r}".format(string, value)
		self.assertEqual(self._evaluate(string), value, msg=msg)

	def test_parse_boolean(self):
		self.assertLiteralStatementEqual('true', True)
		self.assertLiteralStatementEqual('false', False)

	def test_parse_float(self):
		self.assertLiteralStatementEqual('3.14', 3.14)
		self.assertLiteralStatementEqual('3.140', 3.140)
		self.assertLiteralStatementEqual('.314', 0.314)
		self.assertLiteralStatementEqual('0.314', 0.314)

	def test_parse_float_exponent(self):
		self.assertLiteralStatementEqual('3.14e5', 314000.0)
		self.assertLiteralStatementEqual('3.14e+3', 3140.0)
		self.assertLiteralStatementEqual('3.14e-3', 0.00314)
		self.assertLiteralStatementEqual('3.14E5', 314000.0)
		self.assertLiteralStatementEqual('3.14E+3', 3140.0)
		self.assertLiteralStatementEqual('3.14E-3', 0.00314)

		self.assertLiteralStatementEqual('-3.14e5', -314000.0)
		self.assertLiteralStatementEqual('-3.14e+3', -3140.0)
		self.assertLiteralStatementEqual('-3.14e-3', -0.00314)
		self.assertLiteralStatementEqual('-3.14E5', -314000.0)
		self.assertLiteralStatementEqual('-3.14E+3', -3140.0)
		self.assertLiteralStatementEqual('-3.14E-3', -0.00314)

	def test_parse_float_base_2(self):
		self.assertLiteralStatementEqual('0b00', 0)
		self.assertLiteralStatementEqual('0b11', 3)

	def test_parse_float_base_8(self):
		self.assertLiteralStatementEqual('0o00', 0)
		self.assertLiteralStatementEqual('0o77', 63)

	def test_parse_float_base_10(self):
		self.assertLiteralStatementEqual('00', 0)
		self.assertLiteralStatementEqual('99', 99)

	def test_parse_float_base_16(self):
		self.assertLiteralStatementEqual('0x00', 0)
		self.assertLiteralStatementEqual('0xdeadbeef', 3735928559)
		self.assertLiteralStatementEqual('0xdeADbeEF', 3735928559)

	def test_parse_float_inf(self):
		self.assertLiteralStatementEqual('inf', float('inf'))
		self.assertLiteralStatementEqual('-inf', float('-inf'))

	def test_parse_float_nan(self):
		self.assertTrue(math.isnan(self._evaluate('nan')))
		self.assertTrue(math.isnan(self._evaluate('-nan')))

	def test_parse_string(self):
		self.assertLiteralStatementEqual("'Alice'", 'Alice')
		self.assertLiteralStatementEqual('"Alice"', 'Alice')

	def test_parse_string_escapes(self):
		self.assertLiteralStatementEqual("'Alice\\\'s'", 'Alice\'s')
		self.assertLiteralStatementEqual('"Alice\'s"', 'Alice\'s')

if __name__ == '__main__':
	unittest.main()
