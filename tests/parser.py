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

import datetime
import itertools
import math
import unittest

import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors
import rule_engine.parser as parser

import dateutil.tz

class ParserTestsBase(unittest.TestCase):
	_parser = parser.Parser()
	context = engine.Context()
	def _parse(self, string, context):
		return self._parser.parse(string, self.context)

	def assertStatementType(self, string, ast_expression):
		statement = self._parse(string, self.context)
		self.assertIsInstance(statement, ast.Statement, msg='the parser did not return a statement')
		expression = statement.expression
		self.assertIsInstance(expression, ast_expression, msg='the statement expression is not the correct expression type')
		return statement

class ParserTests(ParserTestsBase):
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

	def test_parser_raises_syntax_error(self):
		with self.assertRaises(errors.RuleSyntaxError):
			self._parse('test[', self.context)

	def test_parser_returns_statement(self):
		expression = self._parse('true', self.context)
		self.assertIsInstance(expression, ast.Statement)

	def test_parser_symbol_expressions(self):
		symbols = ('a', 'b')
		for text in symbols:
			expression = self.assertStatementType(text, ast.SymbolExpression).expression
			self.assertEqual(expression.name, text)
			self.assertIsNone(expression.scope)

			expression = self.assertStatementType('$' + text, ast.SymbolExpression).expression
			self.assertEqual(expression.name, text)
			self.assertEqual(expression.scope, 'built-in')


	def test_parser_ternary_expressions(self):
		statement = self.assertStatementType('condition ? case_true : case_false', ast.TernaryExpression)
		self.assertIsInstance(statement.expression.condition, ast.SymbolExpression)
		self.assertEqual(statement.expression.condition.name, 'condition')
		self.assertIsInstance(statement.expression.case_true, ast.SymbolExpression)
		self.assertEqual(statement.expression.case_true.name, 'case_true')
		self.assertIsInstance(statement.expression.case_false, ast.SymbolExpression)
		self.assertEqual(statement.expression.case_false.name, 'case_false')

	def test_parser_unary_expressions(self):
		expressions = ('-right', 'not right')
		for expression in expressions:
			statement = self.assertStatementType(expression, ast.UnaryExpression)
			self.assertIsInstance(statement.expression.right, ast.SymbolExpression)
			self.assertEqual(statement.expression.right.name, 'right')

class ParserLeftOperatorRightTests(ParserTestsBase):
	def assertStatementType(self, string, ast_expression):
		statement = super(ParserLeftOperatorRightTests, self).assertStatementType(string, ast_expression)
		expression = statement.expression
		self.assertIsInstance(expression.left, ast.SymbolExpression)
		self.assertEqual(expression.left.name, 'left')
		self.assertIsInstance(expression.right, ast.SymbolExpression)
		self.assertEqual(expression.right.name, 'right')
		return statement

	def test_parser_arithmetic_expressions(self):
		expressions = (
			'left + right',
			'left - right',
			'left / right',
			'left // right',
			'left % right',
			'left * right',
			'left ** right'
		)
		for expression in expressions:
			self.assertStatementType(expression, ast.ArithmeticExpression)

	def test_parser_bitwise_expressions(self):
		expressions = (
			'left & right',
			'left | right',
			'left ^ right',
			'left << right',
			'left >> right'
		)
		for expression in expressions:
			self.assertStatementType(expression, ast.BitwiseExpression)

	def test_parser_logical_expressions(self):
		expressions = ('left and right', 'left or right')
		for expression in expressions:
			self.assertStatementType(expression, ast.LogicExpression)

	def test_parser_comparison_expressions(self):
		expressions = ('left == right', 'left != right')
		for expression in expressions:
			self.assertStatementType(expression, ast.ComparisonExpression)

	def test_parser_comparison_arithmetic_expressions(self):
		expressions = (
			'left > right',
			'left >= right',
			'left < right',
			'left <= right'
		)
		for expression in expressions:
			self.assertStatementType(expression, ast.ComparisonExpression)

	def test_parser_comparison_fuzzy_expressions(self):
		expressions = ('left =~ right', 'left =~~ right', 'left !~ right', 'left !~~ right')
		for expression in expressions:
			self.assertStatementType(expression, ast.FuzzyComparisonExpression)

class ParserLiteralTests(ParserTestsBase):
	def assertLiteralAttributeStatementEqual(self, string, python_value, msg=None):
		statement = self._parse(string, self.context)
		self.assertIsInstance(statement, ast.Statement, msg='the parser did not return a statement')
		self.assertIsInstance(statement.expression, ast.LiteralExpressionBase, msg='the statement expression is not the correct type')
		value = statement.evaluate(None)
		self.assertEqual(value, python_value, msg=msg or "{0!r} does not evaluate to {1!r}".format(string, python_value))

	def assertLiteralStatementEqual(self, string, ast_expression, python_value, msg=None):
		statement = self._parse(string, self.context)
		self.assertIsInstance(statement, ast.Statement, msg='the parser did not return a statement')
		self.assertIsInstance(statement.expression, ast_expression, msg='the statement expression is not the correct literal type')
		self.assertEqual(statement.expression.value, python_value, msg=msg or "{0!r} does not evaluate to {1!r}".format(string, python_value))

	def test_parse_array(self):
		self.assertLiteralAttributeStatementEqual('[ ]', tuple())
		self.assertLiteralAttributeStatementEqual('[1, 2]', tuple((1.0, 2.0)))
		self.assertLiteralAttributeStatementEqual('[1, 2,]', tuple((1.0, 2.0)))

	def test_parse_array_getitem(self):
		cases = (
			('["t", "e", "s", "t", "i", "n", "g"]', '"testing"'),
			(('[0]', 't'), ('[1]', 'e'), ('[-1]', 'g'))
		)
		for (container, (getitem, answer)) in itertools.product(*cases):
			self.assertLiteralAttributeStatementEqual(container + getitem, answer)

	def test_parse_array_getslice(self):
		self.assertLiteralAttributeStatementEqual('"testing"[:]', 'testing')
		self.assertLiteralAttributeStatementEqual('"testing"[1:-1]', 'estin')
		self.assertLiteralAttributeStatementEqual('"testing"[1:6]', 'estin')
		self.assertLiteralAttributeStatementEqual('["t", "e", "s", "t", "i", "n", "g"][:]', tuple('testing'))
		self.assertLiteralAttributeStatementEqual('["t", "e", "s", "t", "i", "n", "g"][1:-1]', tuple('estin'))
		self.assertLiteralAttributeStatementEqual('["t", "e", "s", "t", "i", "n", "g"][1:6]', tuple('estin'))

	def test_parse_boolean(self):
		self.assertLiteralStatementEqual('true', ast.BooleanExpression, True)
		self.assertLiteralStatementEqual('false', ast.BooleanExpression, False)

	def test_parse_datetime(self):
		self.assertLiteralStatementEqual('d"2016-10-15"', ast.DatetimeExpression, datetime.datetime(2016, 10, 15, tzinfo=dateutil.tz.tzlocal()))
		self.assertLiteralStatementEqual('d"2016-10-15 12:30"', ast.DatetimeExpression, datetime.datetime(2016, 10, 15, 12, 30, tzinfo=dateutil.tz.tzlocal()))

	def test_parse_datetime_attributes(self):
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".date', datetime.datetime(2019, 9, 11, tzinfo=dateutil.tz.UTC))
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".day', 11)
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".hour', 20)
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".microsecond', 506406)
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".millisecond', 506.406)
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".minute', 46)
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".month', 9)
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".second', 57)
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".weekday', 'Wednesday')
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".year', 2019)
		self.assertLiteralAttributeStatementEqual('d"2019-09-11T20:46:57.506406+00:00".zone_name', 'UTC')

	def test_parse_datetime_syntax_errors(self):
		try:
			self._parse('d"this is wrong"', self.context)
		except errors.DatetimeSyntaxError as error:
			self.assertEqual(error.value, 'this is wrong')
		else:
			self.fail('DatetimeSyntaxError was not raised')

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

	def test_parse_null(self):
		self.assertLiteralStatementEqual('null', ast.NullExpression, None)

	def test_parse_string(self):
		self.assertLiteralStatementEqual("'Alice'", ast.StringExpression, 'Alice')
		self.assertLiteralStatementEqual('"Alice"', ast.StringExpression, 'Alice')

		self.assertLiteralStatementEqual("s'Alice'", ast.StringExpression, 'Alice')
		self.assertLiteralStatementEqual('s"Alice"', ast.StringExpression, 'Alice')

	def test_parse_string_attributes(self):
		self.assertLiteralAttributeStatementEqual('s"".is_empty', True)
		self.assertLiteralAttributeStatementEqual('s"Alice".length', 5)

	def test_parse_string_escapes(self):
		self.assertLiteralStatementEqual("'Alice\\\'s'", ast.StringExpression, 'Alice\'s')
		self.assertLiteralStatementEqual('"Alice\'s"', ast.StringExpression, 'Alice\'s')

if __name__ == '__main__':
	unittest.main()
