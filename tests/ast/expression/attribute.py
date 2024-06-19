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
import decimal
import math
import unittest

from .literal import context
import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors
import rule_engine.types as types

import dateutil.tz

__all__ = ('GetAttributeExpressionTests',)

class BadAttributeResolver(engine._AttributeResolver):
	@engine._AttributeResolver.attribute('undefined', ast.DataType.STRING)
	@engine._AttributeResolver.attribute('unsupported', ast.DataType.STRING, result_type=ast.DataType.BOOLEAN)
	def string_attribute(self, value):
		return None

class GetAttributeExpressionTests(unittest.TestCase):
	def test_ast_expression_attribute_error(self):
		symbol = ast.SymbolExpression(context, 'foo')
		expression = ast.GetAttributeExpression(context, symbol, 'bar')
		with self.assertRaises(errors.AttributeResolutionError):
			expression.evaluate({'foo': 1})
		with self.assertRaises(errors.AttributeResolutionError):
			expression.evaluate({'foo': 'baz'})

	def test_ast_expression_attribute_type_error(self):
		symbol = ast.StringExpression(context, 'foo')

		expression = ast.GetAttributeExpression(context, symbol, 'undefined')
		self.assertIsNone(expression.evaluate(None))

		expression = ast.GetAttributeExpression(context, symbol, 'unsupported')
		with self.assertRaises(errors.AttributeTypeError):
			expression.evaluate(None)

	def test_ast_expression_attribute_safe(self):
		symbol = ast.StringExpression(context, 'foo')

		expression = ast.GetAttributeExpression(context, symbol, 'undefined', safe=True)
		expression.evaluate(None)

		expression = ast.GetAttributeExpression(context, ast.NullExpression(context), 'undefined', safe=True)
		self.assertIsNone(expression.evaluate(None))

	def test_ast_expression_array_attributes(self):
		ary = (decimal.Decimal(1), decimal.Decimal(2), decimal.Decimal(3))
		symbol = ast.SymbolExpression(context, 'ary')

		attributes = {
			'length': len(ary),
			'to_ary': ary,
			'to_set': set(ary)
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate({'ary': ary}), value, "attribute {} failed".format(attribute_name))

		# test that compound type information is propagated through attributes
		typed_context = engine.Context(
			type_resolver=engine.type_resolver_from_dict({
				symbol.name: types.DataType.ARRAY(types.DataType.FLOAT)
			})
		)
		typed_symbol = ast.SymbolExpression(typed_context, symbol.name)
		expression = ast.GetAttributeExpression(typed_context, typed_symbol, 'to_ary')
		self.assertEqual(expression.result_type, typed_context.resolve_type(symbol.name))

	def test_ast_expression_array_method_ends_with(self):
		combos = [
			(('Rule',), False),
			(('Engine',), True),
		]
		for suffix, result in combos:
			array_expression = ast.ArrayExpression(context, [
				ast.StringExpression(context, 'Rule'),
				ast.StringExpression(context, 'Engine')
			])
			expression = ast.GetAttributeExpression(context, array_expression, 'ends_with')
			method = expression.evaluate(None)
			self.assertTrue(callable(method), "attribute ends_with failed (method not callable)")
			self.assertEqual(method(suffix), result)

	def test_ast_expression_array_method_starts_with(self):
		combos = [
			(('Rule',), True),
			(('Engine',), False),
		]
		for prefix, result in combos:
			array_expression = ast.ArrayExpression(context, [
				ast.StringExpression(context, 'Rule'),
				ast.StringExpression(context, 'Engine')
			])
			expression = ast.GetAttributeExpression(context, array_expression, 'starts_with')
			method = expression.evaluate(None)
			self.assertTrue(callable(method), "attribute starts_with failed (method not callable)")
			self.assertEqual(method(prefix), result)

	def test_ast_expression_bytes_attributes(self):
		value = b'Rule Engine'
		symbol = ast.BytesExpression(context, value)

		attributes = {
			'to_ary': tuple(value),
			'to_set': set(value),
			'length': len(value),
			'is_empty': False
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate(None), value, "attribute {} failed".format(attribute_name))

	def test_ast_expression_bytes_method_decode(self):
		combos = [
			('utf-8', 'Rule Engine'),
			('hex', '52756c6520456e67696e65'),
			('base16', '52756c6520456e67696e65'),
			('base64', 'UnVsZSBFbmdpbmU=')
		]
		for encoding, string in combos:
			bytes_expression = ast.BytesExpression(context, b'Rule Engine')
			expression = ast.GetAttributeExpression(context, bytes_expression, 'decode')
			method = expression.evaluate(None)
			self.assertTrue(callable(method), "attribute decode failed (method not callable)")
			self.assertEqual(method(encoding), string)
		with self.assertRaises(errors.FunctionCallError):
			method('invalid-encoding')

	def test_ast_expression_bytes_method_ends_with(self):
		combos = [
			(b'Rule', False),
			(b'Engine', True),
		]
		for suffix, result in combos:
			bytes_expression = ast.BytesExpression(context, b'Rule Engine')
			expression = ast.GetAttributeExpression(context, bytes_expression, 'ends_with')
			method = expression.evaluate(None)
			self.assertTrue(callable(method), "attribute ends_with failed (method not callable)")
			self.assertEqual(method(suffix), result)

	def test_ast_expression_bytes_method_starts_with(self):
		combos = [
			(b'Rule', True),
			(b'Engine', False),
		]
		for prefix, result in combos:
			bytes_expression = ast.BytesExpression(context, b'Rule Engine')
			expression = ast.GetAttributeExpression(context, bytes_expression, 'starts_with')
			method = expression.evaluate(None)
			self.assertTrue(callable(method), "attribute starts_with failed (method not callable)")
			self.assertEqual(method(prefix), result)

	def test_ast_expression_datetime_attributes(self):
		timestamp = datetime.datetime(2019, 9, 11, 20, 46, 57, 506406, tzinfo=dateutil.tz.UTC)
		symbol = ast.DatetimeExpression(context, timestamp)

		attributes = {
			'to_epoch': decimal.Decimal(str(timestamp.timestamp())),
			'day': 11,
			'hour': 20,
			'microsecond': 506406,
			'millisecond': decimal.Decimal('506.406'),
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

	def test_ast_expression_timedelta_attributes(self):
		timedelta = datetime.timedelta(weeks=7, days=6, hours=5, minutes=4, seconds=3, milliseconds=2, microseconds=1)
		symbol = ast.TimedeltaExpression(context, timedelta)

		attributes = {
			'days': 55,
			'seconds': 18243,
			'microseconds': 2001,
			'total_seconds': decimal.Decimal('4770243.002001'),
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate(None), value, "attribute {} failed".format(attribute_name))

	def test_ast_expression_float_attributes(self):
		flt = decimal.Decimal('3.14159')
		symbol = ast.SymbolExpression(context, 'flt')

		attributes = {
			'ceiling': decimal.Decimal('4'),
			'floor': decimal.Decimal('3'),
			'is_nan': False,
			'to_flt': flt,
			'to_str': '3.14159'
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate({'flt': flt}), value, "attribute {} failed".format(attribute_name))

		expression = ast.GetAttributeExpression(context, symbol, 'to_int')
		self.assertEqual(
			expression.evaluate({'flt': decimal.Decimal('3')}),
			decimal.Decimal('3'),
			'attribute to_int failed'
		)

		# check special values too
		expression = ast.GetAttributeExpression(context, symbol, 'to_str')
		for value in ('nan', 'inf', '-inf'):
			flt = decimal.Decimal(value)
			self.assertEqual(expression.evaluate({'flt': flt}), value, "attribute {} failed".format(attribute_name))

	def test_ast_expression_mapping_attributes(self):
		mapping = dict(one=1, two=2, three=3)
		symbol = ast.SymbolExpression(context, 'map')

		attributes = {
			'keys': tuple(mapping.keys()),
			'is_empty': len(mapping) == 0,
			'length': len(mapping),
			'values': tuple(mapping.values())
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate({'map': mapping}), value, "attribute {} failed".format(attribute_name))

		# verify that accessing mapping keys as attributes maintains the preference of attributes over keys
		expression = ast.GetAttributeExpression(context, symbol, 'length')
		self.assertEqual(expression.evaluate({'map': {'length': -1}}), 1)

	def test_ast_expression_set_attributes(self):
		set_ = {1, 2, 3}
		symbol = ast.SymbolExpression(context, 'set')

		attributes = {
			'length': len(set_),
			'to_ary': tuple(set_),
			'to_set': set_
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate({'set': set_}), value, "attribute {} failed".format(attribute_name))

		# test that compound type information is propagated through attributes
		typed_context = engine.Context(
			type_resolver=engine.type_resolver_from_dict({
				symbol.name: types.DataType.SET(types.DataType.FLOAT)
			})
		)
		typed_symbol = ast.SymbolExpression(typed_context, symbol.name)
		expression = ast.GetAttributeExpression(typed_context, typed_symbol, 'to_set')
		self.assertEqual(expression.result_type, typed_context.resolve_type(symbol.name))

	def test_ast_expression_string_attributes(self):
		string = 'Rule Engine'
		symbol = ast.StringExpression(context, string)

		attributes = {
			'as_lower': string.lower(),
			'as_upper': string.upper(),
			'to_ary': tuple(string),
			'to_set': set(string),
			'to_str': string,
			'length': len(string),
			'is_empty': False
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate(None), value, "attribute {} failed".format(attribute_name))

	def test_ast_expression_string_method_encode(self):
		combos = [
			('utf-8', 'Rule Engine'),
			('hex', '52756c6520456e67696e65'),
			('base16', '52756c6520456e67696e65'),
			('base64', 'UnVsZSBFbmdpbmU=')
		]
		for encoding, string in combos:
			string_expression = ast.StringExpression(context, string)
			expression = ast.GetAttributeExpression(context, string_expression, 'encode')
			method = expression.evaluate(None)
			self.assertTrue(callable(method), "attribute encode failed (method not callable)")
			self.assertEqual(method(encoding), b'Rule Engine')
		with self.assertRaises(errors.FunctionCallError):
			method('invalid-encoding')
		with self.assertRaises(errors.FunctionCallError):
			method('base16') # last one is base64 so this should fail

	def test_ast_expression_string_method_ends_with(self):
		combos = [
			('Rule', False),
			('Engine', True),
		]
		for suffix, result in combos:
			string_expression = ast.StringExpression(context, 'Rule Engine')
			expression = ast.GetAttributeExpression(context, string_expression, 'ends_with')
			method = expression.evaluate(None)
			self.assertTrue(callable(method), "attribute ends_with failed (method not callable)")
			self.assertEqual(method(suffix), result)

	def test_ast_expression_string_method_starts_with(self):
		combos = [
			('Rule', True),
			('Engine', False),
		]
		for prefix, result in combos:
			string_expression = ast.StringExpression(context, 'Rule Engine')
			expression = ast.GetAttributeExpression(context, string_expression, 'starts_with')
			method = expression.evaluate(None)
			self.assertTrue(callable(method), "attribute starts_with failed (method not callable)")
			self.assertEqual(method(prefix), result)

	def test_ast_expression_string_attributes_flt(self):
		combos = (
			('3.14159', decimal.Decimal('3.14159')),
			('0xdead', 0xdead),
			('3.14e5', decimal.Decimal('3.14e5'))
		)
		for str_value, flt_value in combos:
			symbol = ast.StringExpression(context, str_value)
			expression = ast.GetAttributeExpression(context, symbol, 'to_flt')
			self.assertEqual(expression.evaluate(None), flt_value, "attribute {} failed".format(str_value))

	def test_ast_expression_string_attributes_int(self):
		tens = ('0b1010', '0o12', '10', '0xa', '1e1')
		for ten in tens:
			symbol = ast.StringExpression(context, ten)
			expression = ast.GetAttributeExpression(context, symbol, 'to_int')
			self.assertEqual(expression.evaluate(None), 10, "attribute {} failed".format(ten))

		symbol = ast.StringExpression(context, '3.14159')
		expression = ast.GetAttributeExpression(context, symbol, 'to_int')
		with self.assertRaises(errors.EvaluationError):
			expression.evaluate(None)

	def test_ast_expression_string_attributes_numeric(self):
		symbol = ast.StringExpression(context, '123')
		attributes = {
			'to_int': 123.0,
			'to_flt': 123.0,
		}
		for attribute_name, value in attributes.items():
			expression = ast.GetAttributeExpression(context, symbol, attribute_name)
			self.assertEqual(expression.evaluate(None), value, "attribute {} failed".format(attribute_name))

		expression = ast.GetAttributeExpression(context, ast.StringExpression(context, 'Foobar'), 'to_flt')
		self.assertTrue(math.isnan(expression.evaluate(None)))
		with self.assertRaises(errors.EvaluationError):
			expression = ast.GetAttributeExpression(context, ast.StringExpression(context, 'Foobar'), 'to_int')
			self.assertEqual(expression.evaluate(None), float('nan'))

		expression = ast.GetAttributeExpression(context, ast.StringExpression(context, 'inf'), 'to_flt')
		self.assertEqual(expression.evaluate(None), float('inf'))

if __name__ == '__main__':
	unittest.main()
