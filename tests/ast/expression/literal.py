#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/ast/expression/literal.py
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
import decimal
import unittest

import rule_engine.ast as ast
import rule_engine.builtins as builtins
import rule_engine.engine as engine
import rule_engine.errors as errors

__all__ = ('LiteralExpressionTests',)

context = engine.Context()
context.builtins = builtins.Builtins.from_defaults(
	{'test': {'one': 1.0, 'two': 2.0}}
)
# literal expressions which should evaluate to false
falseish = (
	ast.ArrayExpression(context, tuple()),
	ast.BooleanExpression(context, False),
	ast.TimedeltaExpression(context, datetime.timedelta()),
	ast.FloatExpression(context, 0.0),
	ast.NullExpression(context),
	ast.StringExpression(context, '')
)
# literal expressions which should evaluate to true
trueish = (
	ast.ArrayExpression(context, tuple((ast.NullExpression(context),))),
	ast.ArrayExpression(context, tuple((ast.FloatExpression(context, 1.0),))),
	ast.BooleanExpression(context, True),
	ast.DatetimeExpression(context, datetime.datetime.now()),
	ast.TimedeltaExpression(context, datetime.timedelta(seconds=1)),
	ast.FloatExpression(context, float('-inf')),
	ast.FloatExpression(context, -1.0),
	ast.FloatExpression(context, 1.0),
	ast.FloatExpression(context, float('inf')),
	ast.StringExpression(context, 'non-empty')
)

class UnknownType(object):
	pass

class LiteralExpressionTests(unittest.TestCase):
	context = engine.Context()
	def assertLiteralTests(self, ExpressionClass, false_value, *true_values):
		with self.assertRaises(TypeError):
			ast.StringExpression(self.context, UnknownType())

		expression = ExpressionClass(self.context, false_value)
		self.assertIsInstance(expression, ast.LiteralExpressionBase)
		self.assertFalse(expression.evaluate(None))

		for true_value in true_values:
			expression = ExpressionClass(self.context, true_value)
			self.assertTrue(expression.evaluate(None))

	def test_ast_expression_literal(self):
		expressions = (
			(ast.ArrayExpression, ()),
			(ast.BooleanExpression, False),
			(ast.BytesExpression, b''),
			(ast.DatetimeExpression, datetime.datetime(2020, 1, 1)),
			(ast.FloatExpression, 0),
			(ast.MappingExpression, {}),
			(ast.SetExpression, set()),
			(ast.StringExpression, ''),
			(ast.TimedeltaExpression, datetime.timedelta(seconds=42)),
		)
		for expression_class, value in expressions:
			expression = ast.LiteralExpressionBase.from_value(context, value)
			self.assertIsInstance(expression, expression_class)

		with self.assertRaises(TypeError):
			ast.LiteralExpressionBase.from_value(context, object())

	def test_ast_expression_literal_array(self):
		self.assertLiteralTests(ast.ArrayExpression, tuple(), tuple((ast.NullExpression(self.context),)))

	def test_ast_expression_literal_boolean(self):
		self.assertLiteralTests(ast.BooleanExpression, False, True)

	def test_ast_expression_literal_bytes(self):
		self.assertLiteralTests(ast.BytesExpression, b'', b'\x00')

	def test_ast_expression_literal_float(self):
		trueish_floats = (expression.value for expression in trueish if isinstance(expression, ast.FloatExpression))
		self.assertLiteralTests(ast.FloatExpression, 0.0, float('nan'), *trueish_floats)
		# converts ints to floats automatically
		int_float = ast.FloatExpression(context, 1)
		self.assertIsInstance(int_float.value, decimal.Decimal)
		self.assertEqual(int_float.value, 1.0)

	def test_ast_expression_literal_mapping(self):
		self.assertLiteralTests(ast.MappingExpression, {}, {ast.StringExpression(context, 'one'): ast.FloatExpression(context, 1)})

		with self.assertRaises(errors.EngineError):
			expression = ast.MappingExpression(context, {ast.MappingExpression(context, {}): ast.NullExpression(context)})

		expression = ast.MappingExpression(context, {ast.SymbolExpression(context, 'map'): ast.NullExpression(context)})
		with self.assertRaises(errors.EngineError):
			expression.evaluate({'map': {}})

	def test_ast_expression_literal_null(self):
		expression = ast.NullExpression(self.context)
		self.assertIsNone(expression.evaluate(None))
		with self.assertRaises(TypeError):
			ast.NullExpression(self.context, False)

	def test_ast_expression_literal_string(self):
		self.assertLiteralTests(ast.StringExpression, '', 'non-empty')

	def test_ast_expression_literal_timedelta(self):
		with self.assertRaises(errors.TimedeltaSyntaxError):
			ast.TimedeltaExpression.from_string(self.context, 'INVALID')

if __name__ == '__main__':
	unittest.main()
