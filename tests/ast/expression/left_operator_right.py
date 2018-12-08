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
	'RegexComparisonExpressionTests'
)

class LeftOperatorRightExpresisonTestsBase(unittest.TestCase):
	ExpressionClass = None
	false_value = ast.BooleanExpression(context, False)
	def assertExpressionTests(self, operation, left_value=None, right_value=None, equals_value=None):
		left_value = left_value or self.left_value
		right_value = right_value or self.right_value
		equals_value = self.false_value if equals_value is None else equals_value
		expression = self.ExpressionClass(context, operation, left_value, right_value)
		self.assertIsInstance(expression, ast.LeftOperatorRightExpressionBase)
		message = "{0}({1!r} {2} {3!r})".format(self.ExpressionClass.__name__, left_value, operation, right_value)
		self.assertEqual(expression.evaluate(None), equals_value, msg=message)

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
	false_value = ast.FloatExpression(context, 0.0)
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
	false_value = ast.FloatExpression(context, 0.0)
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
	def test_ast_expression_left_operator_right_comparison(self):
		for left, right in itertools.product(itertools.chain(trueish, falseish), itertools.chain(trueish, falseish)):
			self.assertExpressionTests('eq', left, right, left is right)
		for left, right in itertools.product(itertools.chain(trueish, falseish), itertools.chain(trueish, falseish)):
			self.assertExpressionTests('ne', left, right, left is not right)

class ArithmeticComparisonExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.ArithmeticComparisonExpression
	def test_ast_expression_left_operator_right_arithmeticcomparison(self):
		neg_one = ast.FloatExpression(context, -1.0)
		zero = ast.FloatExpression(context, 0.0)
		one = ast.FloatExpression(context, 1.0)
		numbers = (neg_one, zero, one)
		for number in numbers:
			self.assertExpressionTests('ge', number, zero, number is zero or number is one)
			self.assertExpressionTests('gt', number, zero, number is one)
			self.assertExpressionTests('le', number, zero, number is zero or number is neg_one)
			self.assertExpressionTests('lt', number, zero, number is neg_one)

	def test_ast_expression_left_operator_right_arithmeticcomparison_type_errors(self):
		for operation, left, right in itertools.product(('ge', 'gt', 'le', 'lt'), trueish, falseish):
			if isinstance(left, ast.FloatExpression) and isinstance(right, ast.FloatExpression):
				continue
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, left, right)

class RegexComparisonExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.RegexComparisonExpression
	left_value = luke = ast.StringExpression(context, 'Luke Skywalker')
	def test_ast_expression_left_operator_right_regexcomparison(self):
		regex = functools.partial(ast.StringExpression, context)
		darth = ast.StringExpression(context, 'Darth Vader')
		self.assertExpressionTests('eq_rem', right_value=self.luke, equals_value=True)
		self.assertExpressionTests('eq_rem', right_value=regex('Skywalker'), equals_value=False)
		self.assertExpressionTests('eq_rem', right_value=darth, equals_value=False)

		self.assertExpressionTests('eq_res', right_value=self.luke, equals_value=True)
		self.assertExpressionTests('eq_res', right_value=regex('Skywalker'), equals_value=True)
		self.assertExpressionTests('eq_res', right_value=darth, equals_value=False)

		self.assertExpressionTests('ne_rem', right_value=self.luke, equals_value=False)
		self.assertExpressionTests('ne_rem', right_value=regex('Skywalker'), equals_value=True)
		self.assertExpressionTests('ne_rem', right_value=darth, equals_value=True)

		self.assertExpressionTests('ne_res', right_value=self.luke, equals_value=False)
		self.assertExpressionTests('ne_res', right_value=regex('Skywalker'), equals_value=False)
		self.assertExpressionTests('ne_res', right_value=darth, equals_value=True)

	def test_ast_expression_left_operator_right_regexcomparison_type_errors(self):
		for operation, left, right in itertools.product(('eq_rem', 'eq_res', 'ne_rem', 'ne_res'), trueish, falseish):
			if isinstance(left, ast.StringExpression) and isinstance(right, ast.StringExpression):
				continue
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, left, right)

	def test_ast_expression_left_operator_right_regexcomparison_syntax_errors(self):
		for operation in ('eq_rem', 'eq_res', 'ne_rem', 'ne_res'):
			with self.assertRaises(errors.RegexSyntaxError):
				self.assertExpressionTests(operation, right_value=ast.StringExpression(context, '*'))
