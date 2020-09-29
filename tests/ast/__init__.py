#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/ast/__init__.py
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

import unittest

from .data_type import *
from .expression import *
from .value_is import *

import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors
import rule_engine.parser as parser

inf = float('inf')
nan = float('nan')

class AstTests(unittest.TestCase):
	context = engine.Context()
	thing = {'age': 21.0, 'name': 'Alice'}
	def test_ast_evaluates_arithmetic_comparisons(self):
		parser_ = parser.Parser()
		statement = parser_.parse('age >= 21', self.context)
		self.assertTrue(statement.evaluate(self.thing))
		statement = parser_.parse('age > 100', self.context)
		self.assertFalse(statement.evaluate(self.thing))

	def test_ast_evaluates_logic(self):
		parser_ = parser.Parser()
		self.assertTrue(parser_.parse('true and true', self.context).evaluate(None))
		self.assertFalse(parser_.parse('true and false', self.context).evaluate(None))

		self.assertTrue(parser_.parse('true or false', self.context).evaluate(None))
		self.assertFalse(parser_.parse('false or false', self.context).evaluate(None))

	def test_ast_evaluates_fuzzy_comparisons(self):
		parser_ = parser.Parser()
		statement = parser_.parse('name =~ ".lic."', self.context)
		self.assertTrue(statement.evaluate(self.thing))
		statement = parser_.parse('name =~~ "lic"', self.context)
		self.assertTrue(statement.evaluate(self.thing))

	def test_ast_evaluates_string_comparisons(self):
		parser_ = parser.Parser()
		statement = parser_.parse('name == "Alice"', self.context)
		self.assertTrue(statement.evaluate(self.thing))
		statement = parser_.parse('name == "calie"', self.context)
		self.assertFalse(statement.evaluate(self.thing))

	def test_ast_evaluates_unary_not(self):
		parser_ = parser.Parser()
		statement = parser_.parse('not false', self.context)
		self.assertTrue(statement.evaluate(None))
		statement = parser_.parse('not true', self.context)
		self.assertFalse(statement.evaluate(None))

		statement = parser_.parse('true and not false', self.context)
		self.assertTrue(statement.evaluate(None))
		statement = parser_.parse('false and not true', self.context)
		self.assertFalse(statement.evaluate(None))

	def test_ast_evaluates_unary_uminus(self):
		parser_ = parser.Parser()
		statement = parser_.parse('-(2 * 5)', self.context)
		self.assertEqual(statement.evaluate(None), -10)

	def test_ast_raises_type_mismatch_arithmetic_comparisons(self):
		parser_ = parser.Parser()
		statement = parser_.parse('symbol < 1', self.context)
		with self.assertRaises(errors.EvaluationError):
			statement.evaluate({'symbol': 'string'})
		with self.assertRaises(errors.EvaluationError):
			statement.evaluate({'symbol': True})
		self.assertTrue(statement.evaluate({'symbol': 0.0}))

	def test_ast_raises_type_mismatch_bitwise(self):
		parser_ = parser.Parser()
		statement = parser_.parse('symbol << 1', self.context)
		with self.assertRaises(errors.EvaluationError):
			statement.evaluate({'symbol': 1.1})
		with self.assertRaises(errors.EvaluationError):
			statement.evaluate({'symbol': 'string'})
		with self.assertRaises(errors.EvaluationError):
			statement.evaluate({'symbol': True})
		with self.assertRaises(errors.EvaluationError):
			statement.evaluate({'symbol': inf})
		with self.assertRaises(errors.EvaluationError):
			statement.evaluate({'symbol': nan})
		self.assertEqual(statement.evaluate({'symbol': 1}), 2)

		with self.assertRaises(errors.EvaluationError):
			parser_.parse('symbol << 1.1', self.context)
		with self.assertRaises(errors.EvaluationError):
			parser_.parse('symbol << "string"', self.context)
		with self.assertRaises(errors.EvaluationError):
			parser_.parse('symbol << true', self.context)
		with self.assertRaises(errors.EvaluationError):
			parser_.parse('inf << 1', self.context)
		with self.assertRaises(errors.EvaluationError):
			parser_.parse('nan << 1', self.context)

	def test_ast_raises_type_mismatch_fuzzy_comparisons(self):
		parser_ = parser.Parser()
		statement = parser_.parse('symbol =~ "string"', self.context)
		with self.assertRaises(errors.EvaluationError):
			statement.evaluate({'symbol': 1.1})
		with self.assertRaises(errors.EvaluationError):
			statement.evaluate({'symbol': True})
		self.assertTrue(statement.evaluate({'symbol': 'string'}))

		with self.assertRaises(errors.EvaluationError):
			parser_.parse('"string" =~ 1', self.context)
		with self.assertRaises(errors.EvaluationError):
			parser_.parse('"string" =~ true', self.context)

	def test_ast_reduces_arithmetic(self):
		thing = {'one': 1, 'two': 2}
		parser_ = parser.Parser()
		statement = parser_.parse('1 + 2', self.context)
		self.assertIsInstance(statement.expression, ast.FloatExpression)
		self.assertEqual(statement.evaluate(None), 3)

		statement = parser_.parse('one + 2', self.context)
		self.assertIsInstance(statement.expression, ast.ArithmeticExpression)
		self.assertEqual(statement.evaluate(thing), 3)

		statement = parser_.parse('1 + two', self.context)
		self.assertIsInstance(statement.expression, ast.ArithmeticExpression)
		self.assertEqual(statement.evaluate(thing), 3)

	def test_ast_reduces_array_literals(self):
		parser_ = parser.Parser()
		statement = parser_.parse('[1, 2, 1 + 2]', self.context)
		self.assertIsInstance(statement.expression, ast.ArrayExpression)
		self.assertTrue(statement.expression.is_reduced)
		self.assertEqual(statement.evaluate(None), (1, 2, 3))

		statement = parser_.parse('[foobar]', self.context)
		self.assertIsInstance(statement.expression, ast.ArrayExpression)
		self.assertFalse(statement.expression.is_reduced)

	def test_ast_reduces_attributes(self):
		parser_ = parser.Parser()
		statement = parser_.parse('"foobar".length', self.context)
		self.assertIsInstance(statement.expression, ast.FloatExpression)
		self.assertEqual(statement.evaluate(None), 6)

	def test_ast_reduces_bitwise(self):
		parser_ = parser.Parser()
		statement = parser_.parse('1 << 2', self.context)
		self.assertIsInstance(statement.expression, ast.FloatExpression)
		self.assertEqual(statement.evaluate(None), 4)

	def test_ast_reduces_ternary(self):
		parser_ = parser.Parser()
		statement = parser_.parse('true ? 1 : 0', self.context)
		self.assertIsInstance(statement.expression, ast.FloatExpression)
		self.assertEqual(statement.evaluate(None), 1)

	def test_ast_type_hints(self):
		parser_ = parser.Parser()
		cases = (
			# type,             type_is,             type_is_not
			('symbol << 1',     ast.DataType.FLOAT,  ast.DataType.STRING),
			('symbol + 1',      ast.DataType.FLOAT,  ast.DataType.STRING),
			('symbol[1]',       ast.DataType.STRING, ast.DataType.FLOAT),
			('symbol[1]',       ast.DataType.ARRAY,  ast.DataType.FLOAT),
			('symbol =~ "foo"', ast.DataType.STRING, ast.DataType.FLOAT),
		)
		for case, type_is, type_is_not in cases:
			parser_.parse(case, self.context)
			context = engine.Context(type_resolver=engine.type_resolver_from_dict({'symbol': type_is}))
			parser_.parse(case, context)
			context = engine.Context(type_resolver=engine.type_resolver_from_dict({'symbol': type_is_not}))
			with self.assertRaises(errors.EvaluationError, msg='case: ' + case):
				parser_.parse(case, context)

if __name__ == '__main__':
	unittest.main()
