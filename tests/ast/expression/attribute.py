#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/ast/expression/attribute.py
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
import unittest

from .literal import context
import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors

import dateutil.tz

__all__ = ('GetAttributeExpressionTests',)

class GetAttributeExpressionTests(unittest.TestCase):
	def test_ast_expression_attribute_exception(self):
		symbol = ast.SymbolExpression(context, 'foo')
		expression = ast.GetAttributeExpression(context, symbol, 'bar')
		with self.assertRaises(errors.AttributeResolutionError):
			expression.evaluate({'foo': 'baz'})

	def test_ast_expression_datetime_attributes(self):
		timestamp = datetime.datetime(2019, 9, 11, 20, 46, 57, 506406, tzinfo=dateutil.tz.UTC)
		symbol = ast.DatetimeExpression(engine.Context(), timestamp)

		attributes = {
			'day': 11,
			'hour': 20,
			'microsecond': 506406,
			'millisecond': 506.406,
			'minute': 46,
			'month': 9,
			'second': 57,
			'weekday': timestamp.strftime('%A'),
			'year': 2019,
			'zone_name': 'UTC',
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate(None), value, "attribute {} failed".format(attribute_name))

	def test_ast_expression_string_attributes(self):
		string = 'Rule Engine'
		symbol = ast.StringExpression(engine.Context(), string)

		attributes = {
			'length': len(string),
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate(None), value, "attribute {} failed".format(attribute_name))

if __name__ == '__main__':
	unittest.main()
