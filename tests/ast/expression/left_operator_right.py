#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/ast/expression/left_operator_right.py
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
import functools
import itertools
import unittest

from .literal import context, trueish, falseish
import rule_engine.ast as ast
import rule_engine.errors as errors

__all__ = (
	'ArithmeticExpressionTests',
	'BitwiseExpressionTests',
	'LogicExpressionTests',
	# comparison expressions
	'ComparisonExpressionTests',
	'ArithmeticComparisonExpressionTests',
	'FuzzyComparisonExpressionTests'
)

class LeftOperatorRightExpresisonTestsBase(unittest.TestCase):
	ExpressionClass = None
	false_value = False
	thing = {}
	def assertExpressionTests(self, operation, left_value=None, right_value=None, equals_value=None):
		left_value = left_value or self.left_value
		right_value = right_value or self.right_value
		equals_value = self.false_value if equals_value is None else equals_value
		expression = self.ExpressionClass(context, operation, left_value, right_value)
		self.assertIsInstance(expression, ast.LeftOperatorRightExpressionBase)
		message = "{0}({1!r} {2} {3!r})".format(self.ExpressionClass.__name__, left_value, operation, right_value)
		self.assertEqual(expression.evaluate(self.thing), equals_value, msg=message)

	def test_ast_expression_left_operator_right_operation_error(self):
		if self.ExpressionClass is None:
			return unittest.skip('skipped')
		with self.assertRaisesRegex(errors.EngineError, r'unsupported operator: fake'):
			self.ExpressionClass(context, 'fake', None, None)

################################################################################
# Left-Operator-Right Expressions
################################################################################
class ArithmeticExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.ArithmeticExpression
	false_value = 0.0
	left_value = two = ast.FloatExpression(context, 2.0)
	right_value = four = ast.FloatExpression(context, 4.0)
	def test_ast_expression_left_operator_right_arithmetic(self):
		self.assertExpressionTests('add', equals_value=6.0)
		self.assertExpressionTests('sub', equals_value=-2.0)
		self.assertExpressionTests('fdiv', equals_value=0.0)
		self.assertExpressionTests('tdiv', equals_value=0.5)
		self.assertExpressionTests('mod', equals_value=2.0)
		self.assertExpressionTests('mul', equals_value=8.0)
		self.assertExpressionTests('pow', equals_value=16.0)

	def test_ast_expression_left_operator_right_arithmetic_type_errors(self):
		for operation in ('add', 'sub', 'fdiv', 'tdiv', 'mod', 'mul', 'pow'):
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.FloatExpression(context, 2.0), ast.StringExpression(context, '4.0'))
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.StringExpression(context, '2.0'), ast.FloatExpression(context, 4.0))
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.FloatExpression(context, 2.0), ast.BooleanExpression(context, True))
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.BooleanExpression(context, True), ast.FloatExpression(context, 4.0))

class BitwiseExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.BitwiseExpression
	false_value = 0.0
	left_value = three = ast.FloatExpression(context, 3.0)
	right_value = five = ast.FloatExpression(context, 5.0)
	def test_ast_expression_left_operator_right_bitwise(self):
		self.assertExpressionTests('bwand', equals_value=1.0)
		self.assertExpressionTests('bwor', equals_value=7.0)
		self.assertExpressionTests('bwxor', equals_value=6.0)
		self.assertExpressionTests('bwlsh', equals_value=96.0)
		self.assertExpressionTests('bwrsh', equals_value=0.0)

	def test_ast_expression_left_operator_right_bitwise_type_errors(self):
		for operation in ('bwand', 'bwor', 'bwxor', 'bwlsh', 'bwrsh'):
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.FloatExpression(context, 3.1), ast.FloatExpression(context, 5.0))
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.FloatExpression(context, 3.0), ast.FloatExpression(context, 5.1))
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.FloatExpression(context, -3.0), ast.FloatExpression(context, 5.0))
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.FloatExpression(context, 3.0), ast.FloatExpression(context, -5.0))
			for left, right in itertools.product(trueish, falseish):
				if isinstance(left, ast.FloatExpression) and isinstance(right, ast.FloatExpression):
					continue
				with self.assertRaises(errors.EvaluationError):
					self.assertExpressionTests(operation, left, right)

class LogicExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.LogicExpression
	def test_ast_expression_left_operator_right_logical(self):
		for operator, left, right in itertools.product(('and', 'or'), trueish, falseish):
			self.assertExpressionTests(operator, left, right, operator == 'or')

		for operator, left, right in itertools.product(('and', 'or'), trueish, trueish):
			self.assertExpressionTests(operator, left, right, True)

		for operator, left, right in itertools.product(('and', 'or'), falseish, falseish):
			self.assertExpressionTests(operator, left, right, False)

################################################################################
# Left-Operator-Right Comparison Expressions
################################################################################
class ComparisonExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.ComparisonExpression
	thing = {'pi': 3.14159}
	def test_ast_expression_left_operator_right_comparison(self):
		chain = tuple(itertools.chain(
			(ast.SymbolExpression(context, 'pi'),),
			trueish,
			falseish
		))
		for left, right in itertools.product(chain, chain):
			self.assertExpressionTests('eq', left, right, left is right)
		for left, right in itertools.product(chain, chain):
			self.assertExpressionTests('ne', left, right, left is not right)

	def test_ast_expression_left_operator_right_comparison_compound(self):
		names1 = ast.LiteralExpressionBase.from_value(context, ('Alice', 'Bob'))
		names2 = ast.LiteralExpressionBase.from_value(context, ('Alice', 'Bob', 'Charlie'))
		self.assertExpressionTests('eq', names1, names1, True)
		self.assertExpressionTests('eq', names1, names2, False)
		self.assertExpressionTests('ne', names1, names1, False)
		self.assertExpressionTests('ne', names1, names2, True)

class ArithmeticComparisonExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.ArithmeticComparisonExpression
	def test_ast_expression_left_operator_right_arithmeticcomparison_array(self):
		left_expr = ast.LiteralExpressionBase.from_value(context, ((1, 2, 3),))
		right_expr = ast.LiteralExpressionBase.from_value(context, ((1, 2, 3),))
		self.assertExpressionTests('ge', left_expr, right_expr, True)
		self.assertExpressionTests('gt', left_expr, right_expr, False)
		self.assertExpressionTests('le', left_expr, right_expr, True)
		self.assertExpressionTests('lt', left_expr, right_expr, False)
		right_expr = ast.LiteralExpressionBase.from_value(context, ((1, 2, 3, 4),))
		self.assertExpressionTests('ge', left_expr, right_expr, False)
		self.assertExpressionTests('gt', left_expr, right_expr, False)
		self.assertExpressionTests('le', left_expr, right_expr, True)
		self.assertExpressionTests('lt', left_expr, right_expr, True)

	def test_ast_expression_left_operator_right_arithmeticcomparison_boolean(self):
		for left, right in itertools.product([True, False], repeat=2):
			left_expr = ast.BooleanExpression(context, left)
			right_expr = ast.BooleanExpression(context, right)
			self.assertExpressionTests('ge', left_expr, right_expr, left >= right)
			self.assertExpressionTests('gt', left_expr, right_expr, left > right)
			self.assertExpressionTests('le', left_expr, right_expr, left <= right)
			self.assertExpressionTests('lt', left_expr, right_expr, left < right)

	def test_ast_expression_left_operator_right_arithmeticcomparison_datetime(self):
		past_date = ast.DatetimeExpression(context, datetime.datetime(2016, 10, 15))
		now = ast.DatetimeExpression(context, datetime.datetime.now())
		self.assertExpressionTests('ge', past_date, now, False)
		self.assertExpressionTests('gt', past_date, now, False)
		self.assertExpressionTests('le', past_date, now, True)
		self.assertExpressionTests('lt', past_date, now, True)

	def test_ast_expression_left_operator_right_arithmeticcomparison_float(self):
		neg_one = ast.FloatExpression(context, -1.0)
		zero = ast.FloatExpression(context, 0.0)
		one = ast.FloatExpression(context, 1.0)
		values = (neg_one, zero, one)
		for number in values:
			self.assertExpressionTests('ge', number, zero, number is zero or number is one)
			self.assertExpressionTests('gt', number, zero, number is one)
			self.assertExpressionTests('le', number, zero, number is zero or number is neg_one)
			self.assertExpressionTests('lt', number, zero, number is neg_one)

	def test_ast_expression_left_operator_right_arithmeticcomparison_null(self):
		left_expr = ast.NullExpression(context)
		right_expr = ast.NullExpression(context)
		self.assertExpressionTests('ge', left_expr, right_expr, True)
		self.assertExpressionTests('gt', left_expr, right_expr, False)
		self.assertExpressionTests('le', left_expr, right_expr, True)
		self.assertExpressionTests('lt', left_expr, right_expr, False)

	def test_ast_expression_left_operator_right_arithmeticcomparison_string(self):
		string1 = ast.StringExpression(context, 'abcd')
		string2 = ast.StringExpression(context, 'ABCD')
		self.assertExpressionTests('ge', string1, string2, True)
		self.assertExpressionTests('gt', string1, string2, True)
		self.assertExpressionTests('le', string1, string2, False)
		self.assertExpressionTests('lt', string1, string2, False)

	def test_ast_expression_left_operator_right_arithmeticcomparison_type_errors(self):
		for operation, left, right in itertools.product(('ge', 'gt', 'le', 'lt'), trueish, falseish):
			if type(left) is type(right):
				continue
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, left, right)

class FuzzyComparisonExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.FuzzyComparisonExpression
	left_value = luke = ast.StringExpression(context, 'Luke Skywalker')
	thing = {'darth': 'Vader', 'luke': 'Skywalker', 'zero': 0.0}
	def test_ast_expression_left_operator_right_fuzzycomparison_literal(self):
		fuzzy = functools.partial(ast.StringExpression, context)
		darth = ast.StringExpression(context, 'Darth Vader')
		self.assertExpressionTests('eq_fzm', right_value=self.luke, equals_value=True)
		self.assertExpressionTests('eq_fzm', right_value=fuzzy('Skywalker'), equals_value=False)
		self.assertExpressionTests('eq_fzm', right_value=darth, equals_value=False)

		self.assertExpressionTests('eq_fzs', right_value=self.luke, equals_value=True)
		self.assertExpressionTests('eq_fzs', right_value=fuzzy('Skywalker'), equals_value=True)
		self.assertExpressionTests('eq_fzs', right_value=darth, equals_value=False)

		self.assertExpressionTests('ne_fzm', right_value=self.luke, equals_value=False)
		self.assertExpressionTests('ne_fzm', right_value=fuzzy('Skywalker'), equals_value=True)
		self.assertExpressionTests('ne_fzm', right_value=darth, equals_value=True)

		self.assertExpressionTests('ne_fzs', right_value=self.luke, equals_value=False)
		self.assertExpressionTests('ne_fzs', right_value=fuzzy('Skywalker'), equals_value=False)
		self.assertExpressionTests('ne_fzs', right_value=darth, equals_value=True)

	def test_ast_expression_left_operator_right_fuzzycomparison_nulls(self):
		darth = ast.StringExpression(context, 'Darth Vader')
		null = ast.NullExpression(context)
		for operation, left, right in itertools.product(('eq_fzm', 'eq_fzs'), (darth, null), (darth, null)):
			self.assertExpressionTests(operation, left_value=left, right_value=right, equals_value=left is right)
		for operation, left, right in itertools.product(('ne_fzm', 'ne_fzs'), (darth, null), (darth, null)):
			self.assertExpressionTests(operation, left_value=left, right_value=right, equals_value=left is not right)

	def test_ast_expression_left_operator_right_fuzzycomparison_symbolic(self):
		fuzzy = functools.partial(ast.SymbolExpression, context)
		darth = ast.SymbolExpression(context, 'darth')
		self.assertExpressionTests('eq_fzm', right_value=self.luke, equals_value=True)
		self.assertExpressionTests('eq_fzm', right_value=fuzzy('luke'), equals_value=False)
		self.assertExpressionTests('eq_fzm', right_value=darth, equals_value=False)

		self.assertExpressionTests('eq_fzs', right_value=self.luke, equals_value=True)
		self.assertExpressionTests('eq_fzs', right_value=fuzzy('luke'), equals_value=True)
		self.assertExpressionTests('eq_fzs', right_value=darth, equals_value=False)

		self.assertExpressionTests('ne_fzm', right_value=self.luke, equals_value=False)
		self.assertExpressionTests('ne_fzm', right_value=fuzzy('luke'), equals_value=True)
		self.assertExpressionTests('ne_fzm', right_value=darth, equals_value=True)

		self.assertExpressionTests('ne_fzs', right_value=self.luke, equals_value=False)
		self.assertExpressionTests('ne_fzs', right_value=fuzzy('luke'), equals_value=False)
		self.assertExpressionTests('ne_fzs', right_value=darth, equals_value=True)

	def test_ast_expression_left_operator_right_fuzzycomparison_type_errors(self):
		operations = ('eq_fzm', 'eq_fzs', 'ne_fzm', 'ne_fzs')
		for operation, left, right in itertools.product(operations, trueish, falseish):
			if isinstance(left, (ast.NullExpression, ast.StringExpression)) and isinstance(right, (ast.NullExpression, ast.StringExpression)):
				continue
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, left, right)
		string = ast.StringExpression(context, 'string')
		symbol = ast.SymbolExpression(context, 'zero')
		for operation in operations:
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, string, symbol)
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, symbol, string)

	def test_ast_expression_left_operator_right_fuzzycomparison_syntax_errors(self):
		for operation in ('eq_fzm', 'eq_fzs', 'ne_fzm', 'ne_fzs'):
			try:
				self.assertExpressionTests(operation, right_value=ast.StringExpression(context, '*'))
			except errors.RegexSyntaxError as error:
				self.assertEqual(error.value, '*')
			else:
				self.fail('fuzzySyntaxError was not raised')
