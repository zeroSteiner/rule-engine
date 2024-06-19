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
import rule_engine.engine as engine
import rule_engine.errors as errors

__all__ = (
	'ArithmeticExpressionTests',
	'AddExpressionTests',
	'AddDatetimeExpressionTests',
	'SubtractExpressionTests',
	'BitwiseExpressionTests',
	'BitwiseExpressionSetTests',
	'BitwiseShiftExpressionTests',
	'LogicExpressionTests',
	# comparison expressions
	'ComparisonExpressionTests',
	'ArithmeticComparisonExpressionTests',
	'FuzzyComparisonExpressionTests'
)

class LeftOperatorRightExpresisonTestsBase(unittest.TestCase):
	ExpressionClass = None
	false_value = False
	def assertExpressionTests(self, operation, left_value=None, right_value=None, equals_value=None):
		left_value = left_value or self.left_value
		right_value = right_value or self.right_value
		equals_value = self.false_value if equals_value is None else equals_value

		# test #1: literals
		expression = self.ExpressionClass(context, operation, left_value, right_value)
		self.assertIsInstance(expression, ast.LeftOperatorRightExpressionBase)
		message = "{0}({1!r} {2} {3!r})".format(self.ExpressionClass.__name__, left_value, operation, right_value)
		self.assertEqual(expression.evaluate(None), equals_value, msg=message)

		# test #2: symbols
		expression = self.ExpressionClass(context, operation, ast.SymbolExpression(context, 'left_value'), ast.SymbolExpression(context, 'right_value'))
		self.assertIsInstance(expression, ast.LeftOperatorRightExpressionBase)
		message = "{0}({1!r} {2} {3!r})".format(self.ExpressionClass.__name__, left_value, operation, right_value)
		self.assertEqual(expression.evaluate({'left_value': left_value.evaluate(None), 'right_value': right_value.evaluate(None)}), equals_value, msg=message)

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
		self.assertExpressionTests('fdiv', equals_value=0.0)
		self.assertExpressionTests('tdiv', equals_value=0.5)
		self.assertExpressionTests('mod', equals_value=2.0)
		self.assertExpressionTests('mul', equals_value=8.0)
		self.assertExpressionTests('pow', equals_value=16.0)

	def test_ast_expression_left_operator_right_arithmetic_type_errors(self):
		for operation in ('fdiv', 'tdiv', 'mod', 'mul', 'pow'):
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.FloatExpression(context, 2.0), ast.StringExpression(context, '4.0'))
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.StringExpression(context, '2.0'), ast.FloatExpression(context, 4.0))
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.FloatExpression(context, 2.0), ast.BooleanExpression(context, True))
			with self.assertRaises(errors.EvaluationError):
				self.assertExpressionTests(operation, ast.BooleanExpression(context, True), ast.FloatExpression(context, 4.0))

class AddExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.AddExpression
	false_value = 0.0
	left_value = two = ast.FloatExpression(context, 2.0)
	right_value = four = ast.FloatExpression(context, 4.0)
	def test_ast_expression_left_operator_right_add(self):
		self.assertExpressionTests('add', equals_value=6.0)
		self.assertExpressionTests('add', left_value=ast.StringExpression(context,'a'), right_value=ast.StringExpression(context,'b'), equals_value='ab')

	def test_ast_expression_left_operator_right_add_type_errors(self):
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.FloatExpression(context, 2.0), ast.StringExpression(context, '4.0'))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.StringExpression(context, '2.0'), ast.FloatExpression(context, 4.0))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.FloatExpression(context, 2.0), ast.BooleanExpression(context, True))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.BooleanExpression(context, True), ast.FloatExpression(context, 4.0))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.BooleanExpression(context, True), ast.StringExpression(context, 'b'))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.StringExpression(context, 'b'), ast.BooleanExpression(context, True))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.DatetimeExpression(context, datetime.datetime.now()), ast.StringExpression(context, 'abc'))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.DatetimeExpression(context, datetime.datetime.now()), ast.FloatExpression(context, 6.0))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.DatetimeExpression(context, datetime.datetime.now()), ast.BooleanExpression(context, False))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.DatetimeExpression(context, datetime.datetime.now()), ast.DatetimeExpression(context, datetime.datetime.now()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.StringExpression(context, 'abc'), ast.DatetimeExpression(context, datetime.datetime.now()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.FloatExpression(context, 6.0), ast.DatetimeExpression(context, datetime.datetime.now()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.BooleanExpression(context, False), ast.DatetimeExpression(context, datetime.datetime.now()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.TimedeltaExpression(context, datetime.timedelta()), ast.StringExpression(context, 'abc'))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.TimedeltaExpression(context, datetime.timedelta()), ast.FloatExpression(context, 6.0))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.TimedeltaExpression(context, datetime.timedelta()), ast.BooleanExpression(context, False))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.StringExpression(context, 'abc'), ast.TimedeltaExpression(context, datetime.timedelta()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.FloatExpression(context, 6.0), ast.TimedeltaExpression(context, datetime.timedelta()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('add', ast.BooleanExpression(context, False), ast.TimedeltaExpression(context, datetime.timedelta()))

class AddDatetimeExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.AddExpression
	def test_add_datetime_to_timedelta(self):
		start_datetime = datetime.datetime(year=2022, month=6, day=28, hour=1, minute=2, second=3, tzinfo=context.default_timezone)
		start_datetime_expr = ast.DatetimeExpression(context, start_datetime)
		assert_func = functools.partial(self.assertExpressionTests, 'add')
		td_expr_func = functools.partial(ast.TimedeltaExpression, context)

		assert_func(
			left_value=start_datetime_expr,
			right_value=td_expr_func(datetime.timedelta(hours=3, minutes=2, seconds=1)),
			equals_value=start_datetime.replace(hour=4, minute=4, second=4),
		)
		assert_func(
			left_value=td_expr_func(datetime.timedelta(days=1, minutes=30, seconds=5)),
			right_value=start_datetime_expr,
			equals_value=start_datetime.replace(day=29, minute=32, second=8),
		)
		assert_func(
			left_value=start_datetime_expr,
			right_value=ast.TimedeltaExpression(context, datetime.timedelta()),
			equals_value=start_datetime,
		)

	def test_add_timedeltas(self):
		assert_func = functools.partial(self.assertExpressionTests, 'add')
		td_expr_func = functools.partial(ast.TimedeltaExpression, context)

		assert_func(
			left_value=td_expr_func(datetime.timedelta(weeks=6, days=5, hours=4, minutes=3, seconds=2)),
			right_value=td_expr_func(datetime.timedelta(seconds=4)),
			equals_value=datetime.timedelta(weeks=6, days=5, hours=4, minutes=3, seconds=6),
		)
		assert_func(
			left_value=td_expr_func(datetime.timedelta()),
			right_value=td_expr_func(datetime.timedelta(days=6, minutes=25, seconds=42)),
			equals_value=datetime.timedelta(days=6, minutes=25, seconds=42),
		)
		assert_func(
			left_value=td_expr_func(datetime.timedelta(hours=4)),
			right_value=td_expr_func(datetime.timedelta(days=1, seconds=54)),
			equals_value=datetime.timedelta(days=1, hours=4, seconds=54),
		)

class SubtractExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.SubtractExpression
	false_value = 0.0
	left_value = ten = ast.FloatExpression(context, 10.0)
	right_value = five = ast.FloatExpression(context, 5.0)
	def test_ast_expression_left_operator_right_subtract(self):
		self.assertExpressionTests('sub', equals_value=5.0)
		self.assertExpressionTests('sub', left_value=self.right_value, right_value=self.left_value, equals_value=-5.0)

	def test_ast_expression_left_operator_right_subtract_type_errors(self):
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.FloatExpression(context, 12.0), ast.StringExpression(context, "abc"))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.StringExpression(context, "def"), ast.FloatExpression(context, 4.0))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.FloatExpression(context, 14.5), ast.BooleanExpression(context, True))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.BooleanExpression(context, False), ast.FloatExpression(context, 9.9))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.DatetimeExpression(context, datetime.datetime.now()), ast.StringExpression(context, "ghi"))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.DatetimeExpression(context, datetime.datetime.now()), ast.FloatExpression(context, 8.4))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.DatetimeExpression(context, datetime.datetime.now()), ast.BooleanExpression(context, True))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.StringExpression(context, "jkl"), ast.DatetimeExpression(context, datetime.datetime.now()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.FloatExpression(context, 7.7), ast.DatetimeExpression(context, datetime.datetime.now()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.BooleanExpression(context, False), ast.DatetimeExpression(context, datetime.datetime.now()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.TimedeltaExpression(context, datetime.timedelta()), ast.DatetimeExpression(context, datetime.datetime.now()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.TimedeltaExpression(context, datetime.timedelta()), ast.StringExpression(context, "ghi"))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.TimedeltaExpression(context, datetime.timedelta()), ast.FloatExpression(context, 8.4))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.TimedeltaExpression(context, datetime.timedelta()), ast.BooleanExpression(context, True))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.StringExpression(context, "jkl"), ast.TimedeltaExpression(context, datetime.timedelta()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.FloatExpression(context, 7.7), ast.TimedeltaExpression(context, datetime.timedelta()))
		with self.assertRaises(errors.EvaluationError):
			self.assertExpressionTests('sub', ast.BooleanExpression(context, False), ast.TimedeltaExpression(context, datetime.timedelta()))

class SubtractDatetimeExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.SubtractExpression
	def test_subtract_datetime_from_datetime(self):
		dt_expr_func = functools.partial(ast.DatetimeExpression, context)
		start_datetime_expr = dt_expr_func(datetime.datetime(year=2022, month=3, day=15, hour=13, minute=6, second=12))
		assert_func = functools.partial(self.assertExpressionTests, 'sub')

		assert_func(
			left_value=start_datetime_expr,
			right_value=dt_expr_func(datetime.datetime(year=2022, month=3, day=12, hour=9, minute=34, second=11)),
			equals_value=datetime.timedelta(days=3, seconds=12721),
		)
		assert_func(
			left_value=start_datetime_expr,
			right_value=dt_expr_func(datetime.datetime(year=2022, month=4, day=2, hour=3, minute=56, second=22)),
			equals_value=datetime.timedelta(days=-18, seconds=32990),
		)

	def test_subtract_timedelta_from_datetime(self):
		start_datetime = datetime.datetime(year=2022, month=1, day=24, hour=16, minute=19, second=44)
		start_datetime_expr = ast.DatetimeExpression(context, start_datetime)
		assert_func = functools.partial(self.assertExpressionTests, 'sub')
		td_expr_func = functools.partial(ast.TimedeltaExpression, context)

		assert_func(
			left_value=start_datetime_expr,
			right_value=td_expr_func(datetime.timedelta(days=21, hours=2)),
			equals_value=start_datetime.replace(day=3, hour=14),
		)
		assert_func(
			left_value=start_datetime_expr,
			right_value=td_expr_func(-datetime.timedelta(hours=10, minutes=39, seconds=20)),
			equals_value=start_datetime.replace(day=25, hour=2, minute=59, second=4),
		)

	def test_subtract_timedelta_from_timedelta(self):
		assert_func = functools.partial(self.assertExpressionTests, 'sub')
		td_expr_func = functools.partial(ast.TimedeltaExpression, context)

		assert_func(
			left_value=td_expr_func(datetime.timedelta(days=8, minutes=44, seconds=12)),
			right_value=td_expr_func(datetime.timedelta(seconds=23)),
			equals_value=datetime.timedelta(days=8, seconds=2629),
		)
		assert_func(
			left_value=td_expr_func(datetime.timedelta(hours=15, minutes=35)),
			right_value=td_expr_func(datetime.timedelta(minutes=41, seconds=45)),
			equals_value=datetime.timedelta(seconds=53595),
		)

class BitwiseExpressionTests(LeftOperatorRightExpresisonTestsBase):
	ExpressionClass = ast.BitwiseExpression
	false_value = 0.0
	left_value = three = ast.FloatExpression(context, 3.0)
	right_value = five = ast.FloatExpression(context, 5.0)
	def test_ast_expression_left_operator_right_bitwise(self):
		self.assertExpressionTests('bwand', equals_value=1.0)
		self.assertExpressionTests('bwor', equals_value=7.0)
		self.assertExpressionTests('bwxor', equals_value=6.0)

	def test_ast_expression_left_operator_right_bitwise_type_errors(self):
		for operation in ('bwand', 'bwor', 'bwxor'):
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

class BitwiseExpressionSetTests(BitwiseExpressionTests):
	false_value = set()
	left_value = ast.LiteralExpressionBase.from_value(context, set([1, 2, 3]))
	right_value = ast.LiteralExpressionBase.from_value(context, set([3, 4, 5]))
	def test_ast_expression_left_operator_right_bitwise(self):
		self.assertExpressionTests('bwand', equals_value=set([3]))
		self.assertExpressionTests('bwor', equals_value=set([1, 2, 3, 4, 5]))
		self.assertExpressionTests('bwxor', equals_value=set([1, 2, 4, 5]))

class BitwiseShiftExpressionTests(BitwiseExpressionTests):
	ExpressionClass = ast.BitwiseShiftExpression
	def test_ast_expression_left_operator_right_bitwise(self):
		self.assertExpressionTests('bwlsh', equals_value=96.0)
		self.assertExpressionTests('bwrsh', equals_value=0.0)

	def test_ast_expression_left_operator_right_bitwise_type_errors(self):
		for operation in ('bwlsh', 'bwrsh'):
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
		chain = tuple(itertools.chain(
			(ast.FloatExpression(context, 3.14159),),
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

	def test_ast_expression_left_operator_right_arithmeticcomparison_timedelta(self):
		smaller_period = ast.TimedeltaExpression(context, datetime.timedelta(seconds=1))
		larger_period = ast.TimedeltaExpression(context, datetime.timedelta(minutes=1))
		self.assertExpressionTests('ge', smaller_period, larger_period, False)
		self.assertExpressionTests('gt', smaller_period, larger_period, False)
		self.assertExpressionTests('le', smaller_period, larger_period, True)
		self.assertExpressionTests('lt', smaller_period, larger_period, True)

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
		darth = ast.StringExpression(context, 'Vader')
		self.assertExpressionTests('eq_fzm', right_value=self.luke, equals_value=True)
		self.assertExpressionTests('eq_fzm', right_value=darth, equals_value=False)

		self.assertExpressionTests('eq_fzs', right_value=self.luke, equals_value=True)
		self.assertExpressionTests('eq_fzs', right_value=darth, equals_value=False)

		self.assertExpressionTests('ne_fzm', right_value=self.luke, equals_value=False)
		self.assertExpressionTests('ne_fzm', right_value=darth, equals_value=True)

		self.assertExpressionTests('ne_fzs', right_value=self.luke, equals_value=False)
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
