#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/ast/expression/function_call.py
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

from .literal import context
import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors

__all__ = (
	'FunctionCallExpressionTests',
)

class FunctionCallExpressionTests(unittest.TestCase):
	def test_ast_expression_function_call(self):
		def _function():
			return True
		symbol = ast.SymbolExpression(context, 'function')
		function_call = ast.FunctionCallExpression(context, symbol, [])
		self.assertTrue(function_call.evaluate({'function': _function}))

	def test_ast_expression_function_call_error_on_function_type_mismatch(self):
		# function type mismatch
		with self.assertRaises(errors.EvaluationError):
			context = engine.Context(
				type_resolver=engine.type_resolver_from_dict({
					'function': ast.DataType.NULL
				})
			)
			ast.FunctionCallExpression(
				context,
				ast.SymbolExpression(context, 'function'),
				[]
			)

	def test_ast_expression_function_call_error_on_function_argument_type_mismatch(self):
		# function argument type mismatch
		with self.assertRaises(errors.EvaluationError):
			context = engine.Context(
				type_resolver=engine.type_resolver_from_dict({
					'function': ast.DataType.FUNCTION(
						'function',
						argument_types=(ast.DataType.FLOAT,)
					)
				})
			)
			ast.FunctionCallExpression(
				context,
				ast.SymbolExpression(context, 'function'),
				[ast.StringExpression(context, '1')]
			)

	def test_ast_expression_function_call_error_on_uncallable_value(self):
		context = engine.Context()
		symbol = ast.SymbolExpression(context, 'function')
		function_call = ast.FunctionCallExpression(context, symbol, [ast.FloatExpression(context, 1)])

		# function is not callable
		with self.assertRaises(errors.EvaluationError):
			self.assertTrue(function_call.evaluate({'function': True}))

	def test_ast_expression_function_call_error_on_to_few_arguments(self):
		context = engine.Context(
			type_resolver=engine.type_resolver_from_dict({
				'function': ast.DataType.FUNCTION(
					'function',
					return_type=ast.DataType.FLOAT,
					argument_types=(ast.DataType.FLOAT, ast.DataType.FLOAT,),
					minimum_arguments=1
				)
			})
		)
		symbol = ast.SymbolExpression(context, 'function')

		# function is missing arguments
		with self.assertRaises(errors.FunctionCallError):
			ast.FunctionCallExpression(context, symbol, [])

	def test_ast_expression_function_call_error_on_to_many_arguments(self):
		context = engine.Context(
			type_resolver=engine.type_resolver_from_dict({
				'function': ast.DataType.FUNCTION(
					'function',
					return_type=ast.DataType.FLOAT,
					argument_types=(ast.DataType.FLOAT,),
					minimum_arguments=1
				)
			})
		)
		symbol = ast.SymbolExpression(context, 'function')

		# function is missing arguments
		with self.assertRaises(errors.FunctionCallError):
			ast.FunctionCallExpression(context, symbol, [
				ast.FloatExpression(context, 1),
				ast.FloatExpression(context, 1)
			])

	def test_ast_expression_function_call_error_on_exception(self):
		symbol = ast.SymbolExpression(context, 'function')
		function_call = ast.FunctionCallExpression(context, symbol, [ast.FloatExpression(context, 1)])

		# function raises an exception
		class SomeException(Exception):
			pass
		def _function():
			raise SomeException()
		with self.assertRaises(errors.EvaluationError):
			function_call.evaluate({'function': _function})

	def test_ast_expression_function_call_error_on_incompatible_return_type(self):
		symbol = ast.SymbolExpression(context, 'function')
		function_call = ast.FunctionCallExpression(context, symbol, [])
		function_call.result_type = ast.DataType.FUNCTION('function', return_type=ast.DataType.FLOAT)

		def _function():
			return ''
		with self.assertRaises(errors.FunctionCallError):
			function_call.evaluate({'function': _function})
