#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/ast/expression/miscellaneous.py
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
import itertools
import random
import string
import unittest

from .literal import context, trueish, falseish
import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors
import rule_engine.types as types

import dateutil.tz

__all__ = (
	'CommentExpressionTests',
	'ComprehensionExpressionTests',
	'ContainsExpressionTests',
	'GetItemExpressionTests',
	'GetSliceExpressionTests',
	'SymbolExpressionTests',
	'SymbolExpressionConversionTests',
	'TernaryExpressionTests',
	'UnaryExpressionTests'
)

class CommentExpressionTests(unittest.TestCase):
	def test_ast_expression_comment(self):
		value = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		comment = ast.Comment(value)
		self.assertIn(value, repr(comment))

class ComprehensionExpressionTests(unittest.TestCase):
	def test_ast_conditional_comprehension(self):
		iterable = (None,)
		iterable_expression = ast.LiteralExpressionBase.from_value(context, iterable)
		comprehension = ast.ComprehensionExpression(
			context,
			ast.NullExpression(context),
			'test',
			iterable_expression,
			condition=ast.SymbolExpression(context, 'test')
		)
		self.assertEqual(comprehension.evaluate(None), ())

	def test_ast_conditional_comprehension_error(self):
		iterable_expression = ast.SymbolExpression(context, 'iterable')
		comprehension = ast.ComprehensionExpression(
			context,
			ast.NullExpression(context),
			'member',
			iterable_expression
		)
		with self.assertRaises(errors.EvaluationError):
			comprehension.evaluate({'iterable': None})

	def test_ast_unconditional_comprehension(self):
		iterable = (None,)
		iterable_expression = ast.LiteralExpressionBase.from_value(context, iterable)
		comprehension = ast.ComprehensionExpression(context, ast.NullExpression(context), 'test', iterable_expression)
		self.assertEqual(comprehension.evaluate(None), iterable)

	def test_ast_comprehension_result_type(self):
		iterable = (None,)
		iterable_expression = ast.LiteralExpressionBase.from_value(context, iterable)

		comprehension = ast.ComprehensionExpression(context, ast.NullExpression(context), 'test', iterable_expression)
		self.assertEqual(comprehension.result_type, types.DataType.ARRAY(types.DataType.NULL))

		comprehension = ast.ComprehensionExpression(context, ast.FloatExpression(context, 1), 'test', iterable_expression)
		self.assertEqual(comprehension.result_type, types.DataType.ARRAY(types.DataType.FLOAT))

class ContainsExpressionTests(unittest.TestCase):
	def test_ast_expression_contains(self):
		container = ast.LiteralExpressionBase.from_value(context, range(3))

		member = ast.FloatExpression(context, 1.0)
		contains = ast.ContainsExpression(context, container, member)
		self.assertTrue(contains.evaluate(None))
		self.assertIsInstance(contains.reduce(), ast.BooleanExpression)

		member = ast.FloatExpression(context, -1.0)
		contains = ast.ContainsExpression(context, container, member)
		self.assertFalse(contains.evaluate(None))
		self.assertIsInstance(contains.reduce(), ast.BooleanExpression)

		container = ast.StringExpression(context, 'Rule Engine')

		member = ast.StringExpression(context, ' ')
		self.assertTrue(ast.ContainsExpression(context, container, member).evaluate(None))

		member = ast.StringExpression(context, 'x')
		self.assertFalse(ast.ContainsExpression(context, container, member).evaluate(None))

	def test_ast_expression_contains_error(self):
		container = ast.StringExpression(context, 'Rule Engine')
		member = ast.FloatExpression(context, 1.0)
		with self.assertRaises(errors.EvaluationError):
			ast.ContainsExpression(context, container, member).evaluate(None)

		container = ast.FloatExpression(context, 1.0)
		with self.assertRaises(errors.EvaluationError):
			ast.ContainsExpression(context, container, member).evaluate(None)

class GetItemExpressionTests(unittest.TestCase):
	containers = {
		types.DataType.ARRAY:   ast.LiteralExpressionBase.from_value(context, ['one', 'two']),  # ARRAY
		types.DataType.BYTES:   ast.LiteralExpressionBase.from_value(context, b'Rule Engine!'), # BYTES
		types.DataType.MAPPING: ast.LiteralExpressionBase.from_value(context, {'foo': 'bar'}),  # MAPPING
		types.DataType.STRING:  ast.LiteralExpressionBase.from_value(context, 'Rule Engine!')   # STRING
	}
	def test_ast_expression_getitem(self):
		container = self.containers[types.DataType.ARRAY]
		item_0 = ast.FloatExpression(context, 0.0)
		get_item = ast.GetItemExpression(context, container, item_0)
		self.assertEqual(get_item.evaluate(None), 'one')
		self.assertIsInstance(get_item.reduce(), ast.StringExpression)

		item_n1 = ast.FloatExpression(context, -1.0)
		get_item = ast.GetItemExpression(context, container, item_n1)
		self.assertEqual(get_item.evaluate(None), 'two')
		self.assertIsInstance(get_item.reduce(), ast.StringExpression)

		container = self.containers[types.DataType.STRING]
		get_item = ast.GetItemExpression(context, container, item_0)
		self.assertEqual(get_item.evaluate(None), 'R')
		self.assertIsInstance(get_item.reduce(), ast.StringExpression)

		get_item = ast.GetItemExpression(context, container, item_n1)
		self.assertEqual(get_item.evaluate(None), '!')
		self.assertIsInstance(get_item.reduce(), ast.StringExpression)

	def test_ast_expression_getitem_mapping(self):
		container = self.containers[types.DataType.MAPPING]
		item = ast.StringExpression(context, 'foo')
		get_item = ast.GetItemExpression(context, container, item)
		self.assertEqual(get_item.evaluate(None), 'bar')
		self.assertIsInstance(get_item.reduce(), ast.StringExpression)

	def test_ast_expression_getitem_error(self):
		for container in self.containers.values():
			member = ast.FloatExpression(context, 100.0)
			with self.assertRaises(errors.LookupError):
				ast.GetItemExpression(context, container, member).evaluate(None)
			member = ast.FloatExpression(context, 1.1)
			with self.assertRaises(errors.EvaluationError):
				ast.GetItemExpression(context, container, member).evaluate(None)
			member = ast.NullExpression(context)
			with self.assertRaises(errors.EvaluationError):
				ast.GetItemExpression(context, container, member)

	def test_ast_expression_getitem_safe(self):
		sym_name = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		container = ast.SymbolExpression(context, sym_name)
		member = ast.FloatExpression(context, 0)
		get_item = ast.GetItemExpression(context, container, member)
		with self.assertRaises(errors.EvaluationError):
			get_item.evaluate({sym_name: None})
		get_item = ast.GetItemExpression(context, container, member, safe=True)
		self.assertIsNone(get_item.evaluate({sym_name: None}))

		get_item = ast.GetItemExpression(context, container, member, safe=True)
		self.assertIsNone(get_item.evaluate({sym_name: ''}))

	def test_ast_expression_getitem_reduces(self):
		container = ast.MappingExpression(context, (('one', 1), ('two', 2)))
		member = ast.FloatExpression(context, 0)
		with self.assertRaises(errors.LookupError):
			get_item = ast.GetItemExpression(context, container, member)
		get_item = ast.GetItemExpression(context, container, member, safe=True)
		self.assertIsInstance(get_item.reduce(), ast.NullExpression)

class GetSliceExpressionTests(unittest.TestCase):
	def test_ast_expression_getslice(self):
		ary_value = tuple(random.choice(string.ascii_letters) for _ in range(12))
		str_value = ''.join(ary_value)
		byt_value = str_value.encode()
		cases = (
			(ary_value, byt_value, str_value),
			(None,  0,  2),
			(None, -1, -3),
		)
		for container, start, end in itertools.product(*cases):
			get_slice = ast.GetSliceExpression(
				context,
				ast.LiteralExpressionBase.from_value(context, container),
				start=(None if start is None else ast.LiteralExpressionBase.from_value(context, start)),
				stop=(None if end is None else ast.LiteralExpressionBase.from_value(context, end))
			)
			self.assertEqual(get_slice.evaluate({}), container[start:end])

	def test_ast_expression_getslice_error(self):
		with self.assertRaises(errors.EvaluationError):
			ast.GetSliceExpression(context, ast.LiteralExpressionBase.from_value(context, 1.0))
		with self.assertRaises(errors.EvaluationError):
			ast.GetSliceExpression(context, ast.LiteralExpressionBase.from_value(context, None))
		with self.assertRaises(errors.EvaluationError):
			ast.GetSliceExpression(context, ast.LiteralExpressionBase.from_value(context, True))

	def test_ast_expression_getslice_safe(self):
		sym_name = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		container = ast.SymbolExpression(context, sym_name)
		start = ast.FloatExpression(context, 0)
		stop = ast.FloatExpression(context, -1)
		get_slice = ast.GetSliceExpression(context, container, start, stop)
		with self.assertRaises(errors.EvaluationError):
			get_slice.evaluate({sym_name: None})
		get_slice = ast.GetSliceExpression(context, container, start, stop, safe=True)
		self.assertIsNone(get_slice.evaluate({sym_name: None}))

class SymbolExpressionTests(unittest.TestCase):
	def setUp(self):
		self.sym_aryname = ''.join(random.choice(string.ascii_letters) for _ in range(12))
		self.sym_aryvalue = [1.0, 2.0]
		self.sym_aryname_nontyped = ''.join(random.choice(string.ascii_letters) for _ in range(12))
		self.sym_aryvalue_nontyped = self.sym_aryvalue
		self.sym_aryname_nullable = ''.join(random.choice(string.ascii_letters) for _ in range(12))
		self.sym_aryvalue_nullable = [1.0, 2.0, None]
		self.sym_strname = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		self.sym_strvalue = ''.join(random.choice(string.ascii_letters) for _ in range(10))

	def _type_resolver(self, name):
		if name == self.sym_aryname:
			return types.DataType.ARRAY(types.DataType.FLOAT, value_type_nullable=False)
		elif name == self.sym_aryname_nontyped:
			return types.DataType.ARRAY
		elif name == self.sym_aryname_nullable:
			return types.DataType.ARRAY(types.DataType.FLOAT, value_type_nullable=True)
		elif name == self.sym_strname:
			return types.DataType.STRING
		return types.DataType.UNDEFINED

	def test_ast_expression_symbol(self):
		symbol = ast.SymbolExpression(engine.Context(), self.sym_strname)
		self.assertIs(symbol.result_type, types.DataType.UNDEFINED)
		self.assertEqual(symbol.name, self.sym_strname)
		self.assertEqual(symbol.evaluate({self.sym_strname: self.sym_strvalue}), self.sym_strvalue)

	def test_ast_expression_symbol_scope(self):
		symbol = ast.SymbolExpression(context, 'test', scope='built-in')
		expression = ast.GetAttributeExpression(context, symbol, 'one')
		value = expression.evaluate(None)
		self.assertIsInstance(value, decimal.Decimal)
		self.assertEqual(value, 1.0)

	def test_ast_expression_symbol_scope_error(self):
		symbol = ast.SymbolExpression(context, 'fake-name', scope='fake-scope')
		try:
			symbol.evaluate(None)
		except errors.SymbolResolutionError as error:
			self.assertEqual(error.symbol_name, 'fake-name')
			self.assertEqual(error.symbol_scope, 'fake-scope')
		else:
			self.fail('SymbolResolutionError was not raised')

	def test_ast_expression_symbol_type(self):
		context = engine.Context(type_resolver=self._type_resolver)
		symbol = ast.SymbolExpression(context, self.sym_strname)
		self.assertIs(symbol.result_type, types.DataType.STRING)
		self.assertEqual(symbol.name, self.sym_strname)
		self.assertEqual(symbol.evaluate({self.sym_strname: self.sym_strvalue}), self.sym_strvalue)

	def test_ast_expression_symbol_type_errors(self):
		context = engine.Context(type_resolver=self._type_resolver)
		symbol = ast.SymbolExpression(context, self.sym_strname)
		self.assertIs(symbol.result_type, types.DataType.STRING)
		self.assertEqual(symbol.name, self.sym_strname)
		with self.assertRaises(errors.SymbolTypeError):
			self.assertEqual(symbol.evaluate({self.sym_strname: not self.sym_strvalue}), self.sym_strvalue)
		self.assertIsNone(symbol.evaluate({self.sym_strname: None}))

		symbol = ast.SymbolExpression(context, self.sym_aryname)
		with self.assertRaises(errors.SymbolTypeError):
			symbol.evaluate({self.sym_aryname: self.sym_aryvalue_nullable})
		try:
			symbol.evaluate({self.sym_aryname: self.sym_aryvalue})
		except errors.SymbolTypeError:
			self.fail('raises SymbolTypeError when it should not')

		symbol = ast.SymbolExpression(context, self.sym_aryname_nontyped)
		try:
			symbol.evaluate({self.sym_aryname_nontyped: self.sym_aryvalue})
			symbol.evaluate({self.sym_aryname_nontyped: self.sym_aryvalue_nontyped})
			symbol.evaluate({self.sym_aryname_nontyped: self.sym_aryvalue_nullable})
		except errors.SymbolTypeError:
			self.fail('raises SymbolTypeError when it should not')

		symbol = ast.SymbolExpression(context, self.sym_aryname_nullable)
		try:
			symbol.evaluate({self.sym_aryname_nullable: self.sym_aryvalue})
			symbol.evaluate({self.sym_aryname_nullable: self.sym_aryvalue_nullable})
		except errors.SymbolTypeError:
			self.fail('raises SymbolTypeError when it should not')

class SymbolExpressionConversionTests(unittest.TestCase):
	def setUp(self):
		self.sym_name = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		self.symbol = ast.SymbolExpression(context, self.sym_name)
		self.assertEqual(self.symbol.name, self.sym_name)

	def test_ast_expression_symbol_type_converts_date(self):
		result = self.symbol.evaluate({self.sym_name: datetime.date(2016, 10, 15)})
		self.assertIsInstance(result, datetime.datetime)
		self.assertEqual(result, datetime.datetime(2016, 10, 15, tzinfo=dateutil.tz.tzlocal()))

	def test_ast_expression_symbol_type_converts_int(self):
		result = self.symbol.evaluate({self.sym_name: 1})
		self.assertIsInstance(result, decimal.Decimal)
		self.assertEqual(result, 1.0)

	def test_ast_expression_symbol_type_converts_range(self):
		result = self.symbol.evaluate({self.sym_name: range(3)})
		self.assertIsInstance(result, tuple)
		self.assertEqual(result, (0, 1, 2))

class TernaryExpressionTests(unittest.TestCase):
	left_value = ast.StringExpression(context, 'left')
	right_value = ast.StringExpression(context, 'right')
	def test_ast_expression_ternary(self):
		for value in trueish:
			ternary = ast.TernaryExpression(context, value, case_true=self.left_value, case_false=self.right_value)
			self.assertEqual(ternary.evaluate(None), self.left_value.value)
		for value in falseish:
			ternary = ast.TernaryExpression(context, value, case_true=self.left_value, case_false=self.right_value)
			self.assertEqual(ternary.evaluate(None), self.right_value.value)

class UnaryExpressionTests(unittest.TestCase):
	def test_ast_expression_unary(self):
		with self.assertRaises(ValueError):
			ast.UnaryExpression(context, 'type', ast.NullExpression(context))

	def test_ast_expression_unary_not(self):
		for value in trueish:
			unary = ast.UnaryExpression(context, 'not', value)
			self.assertFalse(unary.evaluate(None))
		for value in falseish:
			unary = ast.UnaryExpression(context, 'not', value)
			self.assertTrue(unary.evaluate(None))

	def test_ast_expression_unary_uminus(self):
		for value in trueish:
			if not isinstance(value, (ast.FloatExpression, ast.TimedeltaExpression)):
				continue
			unary = ast.UnaryExpression(context, 'uminus', value)
			result = unary.evaluate(None)
			self.assertTrue(result)
			self.assertNotEqual(result, value.value)
		for value in falseish:
			if not isinstance(value, (ast.FloatExpression, ast.TimedeltaExpression)):
				continue
			unary = ast.UnaryExpression(context, 'uminus', value)
			result = unary.evaluate(None)
			self.assertFalse(result)
			self.assertEqual(result, value.value)

	def test_ast_expresison_unary_minus_type_errors(self):
		for value in trueish + falseish:
			if isinstance(value, (ast.FloatExpression, ast.TimedeltaExpression)):
				continue
			unary = ast.UnaryExpression(context, 'uminus', value)
			with self.assertRaises(errors.EvaluationError):
				unary.evaluate(None)

if __name__ == '__main__':
	unittest.main()
