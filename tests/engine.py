#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/engine.py
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

import collections
import datetime
import decimal
import os
import re
import sys
import types
import unittest
import warnings

import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors

import dateutil.tz

try:
	import graphviz
except ImportError:
	has_graphviz = False
else:
	has_graphviz = True

class ContextTests(unittest.TestCase):
	def test_context_default_timezone(self):
		context = engine.Context(default_timezone='Local')
		self.assertEqual(context.default_timezone, dateutil.tz.tzlocal())

		context = engine.Context(default_timezone='UTC')
		self.assertEqual(context.default_timezone, dateutil.tz.tzutc())

	def test_context_default_timezone_errors(self):
		with self.assertRaises(ValueError):
			engine.Context(default_timezone='doesnotexist')
		with self.assertRaises(TypeError):
			engine.Context(default_timezone=600)

	def test_context_type_resolver_mapping(self):
		context = engine.Context(type_resolver={'name': ast.DataType.STRING})
		self.assertEqual(context.resolve_type('name'), ast.DataType.STRING)

	def test_context_mapping_attribute_lookup_default(self):
		context = engine.Context()
		self.assertTrue(context.mapping_attribute_lookup)

	def test_context_mapping_attribute_lookup_disabled(self):
		context = engine.Context(mapping_attribute_lookup=False)
		self.assertFalse(context.mapping_attribute_lookup)

	def test_context_mapping_attribute_lookup_parse_time_error(self):
		context = engine.Context(
			mapping_attribute_lookup=False,
			type_resolver={'facts': ast.DataType.MAPPING(ast.DataType.STRING, value_type=ast.DataType.STRING)},
		)
		with self.assertRaisesRegex(errors.EvaluationError, r'attribute access on a MAPPING is disabled'):
			engine.Rule('facts.abc == "xyz"', context=context)

	def test_context_mapping_attribute_lookup_parse_time_error_mentions_migration(self):
		context = engine.Context(
			mapping_attribute_lookup=False,
			type_resolver={'facts': ast.DataType.MAPPING(ast.DataType.STRING, value_type=ast.DataType.STRING)},
		)
		try:
			engine.Rule('facts.abc == "xyz"', context=context)
		except errors.EvaluationError as error:
			self.assertIn("mapping['abc']", error.message)
			self.assertIn('v6.0', error.message)
		else:
			self.fail('EvaluationError was not raised')

	def test_context_mapping_attribute_lookup_disabled_bracket_still_works(self):
		context = engine.Context(
			mapping_attribute_lookup=False,
			type_resolver={'facts': ast.DataType.MAPPING(ast.DataType.STRING, value_type=ast.DataType.STRING)},
		)
		rule = engine.Rule('facts["abc"] == "xyz"', context=context)
		self.assertTrue(rule.matches({'facts': {'abc': 'xyz'}}))

	def test_context_mapping_attribute_lookup_disabled_runtime_mapping(self):
		# result_type is UNDEFINED at parse time, but the object is a mapping at runtime — the fallback is refused
		context = engine.Context(mapping_attribute_lookup=False)
		rule = engine.Rule('facts.abc', context=context)
		with self.assertRaises(errors.AttributeResolutionError):
			rule.evaluate({'facts': {'abc': 'xyz'}})

	def test_context_mapping_attribute_lookup_warning_fires_once(self):
		context = engine.Context()
		rule = engine.Rule('facts.abc == "xyz"', context=context)
		thing = {'facts': {'abc': 'xyz'}}
		with warnings.catch_warnings(record=True) as captured:
			warnings.simplefilter('always', category=errors.MappingAttributeLookupDeprecation)
			rule.matches(thing)
			rule.matches(thing)
			rule.matches(thing)
		dep = [w for w in captured if issubclass(w.category, errors.MappingAttributeLookupDeprecation)]
		self.assertEqual(len(dep), 1)

	def test_context_mapping_attribute_lookup_warning_is_per_context(self):
		thing = {'facts': {'abc': 'xyz'}}
		with warnings.catch_warnings(record=True) as captured:
			warnings.simplefilter('always', category=errors.MappingAttributeLookupDeprecation)
			rule_a = engine.Rule('facts.abc == "xyz"', context=engine.Context())
			rule_a.matches(thing)
			rule_b = engine.Rule('facts.abc == "xyz"', context=engine.Context())
			rule_b.matches(thing)
		dep = [w for w in captured if issubclass(w.category, errors.MappingAttributeLookupDeprecation)]
		self.assertEqual(len(dep), 2)

	def test_context_mapping_attribute_lookup_warning_message_content(self):
		context = engine.Context()
		rule = engine.Rule('facts.abc == "xyz"', context=context)
		with warnings.catch_warnings(record=True) as captured:
			warnings.simplefilter('always', category=errors.MappingAttributeLookupDeprecation)
			rule.matches({'facts': {'abc': 'xyz'}})
		self.assertEqual(len(captured), 1)
		message = str(captured[0].message)
		self.assertIn("'abc'", message)
		self.assertIn("mapping['abc']", message)
		self.assertIn('v6.0', message)
		self.assertIn('MappingAttributeLookupDeprecation', message)

	def test_context_mapping_attribute_lookup_warning_concurrent(self):
		# spawn two threads both exercising the fallback against a shared Context; the warning should fire exactly once
		import threading
		context = engine.Context()
		rule = engine.Rule('facts.abc == "xyz"', context=context)
		thing = {'facts': {'abc': 'xyz'}}
		barrier = threading.Barrier(2)
		def worker():
			barrier.wait()
			rule.matches(thing)
		with warnings.catch_warnings(record=True) as captured:
			warnings.simplefilter('always', category=errors.MappingAttributeLookupDeprecation)
			t1 = threading.Thread(target=worker)
			t2 = threading.Thread(target=worker)
			t1.start()
			t2.start()
			t1.join()
			t2.join()
		dep = [w for w in captured if issubclass(w.category, errors.MappingAttributeLookupDeprecation)]
		self.assertEqual(len(dep), 1)

class EngineTests(unittest.TestCase):
	def test_engine_resolve_attribute(self):
		thing = collections.namedtuple('Person', ('name',))(name='alice')
		self.assertEqual(engine.resolve_attribute(thing, 'name'), thing.name)
		with self.assertRaises(errors.SymbolResolutionError):
			engine.resolve_attribute(thing, 'email')

	def test_engine_resolve_attribute_with_defaults(self):
		thing = collections.namedtuple('Person', ('name',))(name='alice')
		context = engine.Context(resolver=engine.resolve_attribute, default_value=None)
		self.assertEqual(engine.Rule('name', context=context).evaluate(thing), thing.name)
		self.assertIsNone(engine.Rule('name.first', context=context).evaluate(thing))
		self.assertIsNone(engine.Rule('address', context=context).evaluate(thing))
		self.assertIsNone(engine.Rule('address.city', context=context).evaluate(thing))

	def test_engine_resolve_item(self):
		thing = {'name': 'Alice'}
		self.assertEqual(engine.resolve_item(thing, 'name'), thing['name'])
		with self.assertRaises(errors.SymbolResolutionError):
			engine.resolve_item(thing, 'email')

	def test_engine_resolve_item_with_defaults(self):
		thing = {'name': 'Alice'}
		context = engine.Context(resolver=engine.resolve_item, default_value=None)
		self.assertEqual(engine.Rule('name', context=context).evaluate(thing), thing['name'])
		self.assertIsNone(engine.Rule('name.first', context=context).evaluate(thing))
		self.assertIsNone(engine.Rule('address', context=context).evaluate(thing))
		self.assertIsNone(engine.Rule('address.city', context=context).evaluate(thing))

	def test_engine_type_resolver_from_dict(self):
		type_resolver = engine.type_resolver_from_dict({
			'string': ast.DataType.STRING,
			'float': ast.DataType.FLOAT
		})
		self.assertTrue(callable(type_resolver))
		self.assertEqual(type_resolver('string'), ast.DataType.STRING)
		self.assertEqual(type_resolver('float'), ast.DataType.FLOAT)
		with self.assertRaises(errors.SymbolResolutionError):
			type_resolver('doesnotexist')

class EngineRuleTests(unittest.TestCase):
	rule_text = 'first_name == "Luke" and email =~ ".*@rebels.org$"'
	true_item = {'first_name': 'Luke', 'last_name': 'Skywalker', 'email': 'luke@rebels.org'}
	false_item = {'first_name': 'Darth', 'last_name': 'Vader', 'email': 'dvader@empire.net'}
	def test_engine_rule_is_valid(self):
		self.assertTrue(engine.Rule.is_valid(self.rule_text))
		self.assertTrue(engine.Rule.is_valid('test == 1'))
		self.assertFalse(engine.Rule.is_valid('test =='))

	def test_engine_rule_raises(self):
		with self.assertRaises(errors.RuleSyntaxError):
			engine.Rule('test ==')

	@unittest.skipUnless(has_graphviz, 'graphviz is unavailable')
	def test_engine_rule_to_graphviz_1(self):
		rule = engine.Rule(self.rule_text)
		digraph = rule.to_graphviz()
		self.assertIsInstance(digraph, graphviz.Digraph)
		self.assertEqual(digraph.comment, self.rule_text)

	@unittest.skipUnless(has_graphviz, 'graphviz is unavailable')
	def test_engine_rule_to_graphviz_2(self):
		rule = engine.Rule('null in [foo.length % [2, 4, 6][s:e][boz] ? (bar > baz) : (bar < -baz)] # comment')
		digraph = rule.to_graphviz()
		self.assertIsInstance(digraph, graphviz.Digraph)

	@unittest.skipUnless(has_graphviz, 'graphviz is unavailable')
	def test_engine_rule_to_graphviz_3(self):
		rule = engine.Rule('[member for member in iterable if member]')
		digraph = rule.to_graphviz()
		self.assertIsInstance(digraph, graphviz.Digraph)

	def test_engine_rule_to_strings(self):
		rule = engine.Rule(self.rule_text)
		self.assertEqual(str(rule), self.rule_text)
		self.assertRegex(repr(rule), "<Rule text='{0}' >".format(re.escape(self.rule_text)))

	def test_engine_rule_matches(self, rule=None):
		rule = rule or engine.Rule(self.rule_text)
		result = rule.matches(self.true_item)
		self.assertIsInstance(result, bool)
		self.assertTrue(result)
		result = rule.matches(self.false_item)
		self.assertIsInstance(result, bool)
		self.assertFalse(result)

	def test_engine_rule_filter(self, rule=None):
		rule = rule or engine.Rule(self.rule_text)
		result = rule.filter([self.true_item, self.false_item])
		self.assertIsInstance(result, types.GeneratorType)
		result = tuple(result)
		self.assertIn(self.true_item, result)
		self.assertNotIn(self.false_item, result)

	def test_engine_rule_evaluate(self):
		rule = engine.Rule('"string"')
		self.assertEqual(rule.evaluate(None), 'string')

	def test_engine_rule_evaluate_attributes(self):
		# ensure that multiple levels can be evaluated as attributes
		rule = engine.Rule('a.b.c')
		with warnings.catch_warnings():
			warnings.simplefilter('ignore', category=errors.MappingAttributeLookupDeprecation)
			self.assertTrue(rule.evaluate({'a': {'b': {'c': True}}}))

			value = rule.evaluate({'a': {'b': {'c': 1}}})
			self.assertIsInstance(value, decimal.Decimal)
			self.assertEqual(value, 1.0)

			value = rule.evaluate({'a': {'b': {'c': {'d': None}}}})
			self.assertIsInstance(value, dict)
			self.assertIn('d', value)

			with self.assertRaises(errors.AttributeResolutionError):
				rule.evaluate({'a': {}})

	def test_engine_rule_debug_parser(self):
		with open(os.devnull, 'w') as file_h:
			original_stderr = sys.stderr
			sys.stderr = file_h
			debug_rule = engine.DebugRule(self.rule_text)
			sys.stderr = original_stderr
		self.test_engine_rule_matches(rule=debug_rule)
		self.test_engine_rule_filter(rule=debug_rule)


class EngineDatetimeRuleTests(unittest.TestCase):
	def test_add_timedeltas(self):
		rule = engine.Rule("t'P4DT2H31S' + t'P1WT45M17S' == t'P1W4DT2H45M48S'")
		self.assertTrue(rule.evaluate({}))

	def test_add_empty_timedelta(self):
		rule = engine.Rule("t'P1DT3S' + t'PT' == t'P1DT3S'")
		self.assertTrue(rule.evaluate({}))

	def test_add_to_today(self):
		rule = engine.Rule("$today + t'PT' == $today")
		self.assertTrue(rule.evaluate({}))

	def test_add_datetime_to_timedelta(self):
		rule = engine.Rule("d'2022-05-23 08:23' + t'PT4H3M2S' == d'2022-05-23 12:26:02'")
		self.assertTrue(rule.evaluate({}))

		rule = engine.Rule("start + t'PT1H' == end")
		self.assertTrue(rule.evaluate({
			"start": datetime.datetime(year=2022, month=2, day=28, hour=23, minute=32, second=56),
			"end": datetime.datetime(year=2022, month=3, day=1, hour=0, minute=32, second=56),
		}))

	def test_subtract_timedeltas(self):
		rule = engine.Rule("t'P4DT2H31S' - t'P1DT45S' == t'P3DT1H59M46S'")
		self.assertTrue(rule.evaluate({}))

		rule = engine.Rule("t'P4DT2H31S' - t'P1WT45M17S' == -t'P2DT22H44M46S'")
		self.assertTrue(rule.evaluate({}))

	def test_subtract_empty_timedelta(self):
		rule = engine.Rule("t'P1DT3S' - t'PT' == t'P1DT3S'")
		self.assertTrue(rule.evaluate({}))

	def test_subtract_from_today(self):
		rule = engine.Rule("$today - t'PT' == $today")
		self.assertTrue(rule.evaluate({}))

	def test_subtract_datetime_from_datetime(self):
		rule = engine.Rule("d'2022-05-23 14:12' - d'2022-05-23 12:15' == t'PT1H57M'")
		self.assertTrue(rule.evaluate({}))

		rule = engine.Rule("end - t'PT1H' == start")
		self.assertTrue(rule.evaluate({
			"start": datetime.datetime(year=2022, month=2, day=28, hour=23, minute=32, second=56),
			"end": datetime.datetime(year=2022, month=3, day=1, hour=0, minute=32, second=56),
		}))

	def test_subtract_timedelta_from_datetime(self):
		rule = engine.Rule("d'2022-06-12' - t'P1D' == d'2022-06-11'")
		self.assertTrue(rule.evaluate({}))

if __name__ == '__main__':
	unittest.main()
