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
import contextlib
import datetime
import os
import re
import types
import unittest

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

class EngineTests(unittest.TestCase):
	def test_engine_resolve_attribute(self):
		thing = collections.namedtuple('Person', ('name',))(name='alice')
		self.assertEqual(engine.resolve_attribute(thing, 'name'), thing.name)
		with self.assertRaises(errors.SymbolResolutionError):
			engine.resolve_attribute(thing, 'email')

	def test_engine_resolve_attribute_recursively(self):
		thing = collections.namedtuple('People', ('person',))(
			collections.namedtuple('Person', ('name',))(name='alice')
		)
		resolver = engine.to_recursive_resolver(engine.resolve_attribute)
		self.assertEqual(resolver(thing, 'person.name'), thing.person.name)
		with self.assertRaises(errors.SymbolResolutionError):
			resolver(thing, 'person.email')

	def test_engine_resolve_attribute_with_defaults(self):
		thing = collections.namedtuple('Person', ('name',))(name='alice')
		resolver = engine.to_default_resolver(engine.resolve_attribute)
		self.assertEqual(resolver(thing, 'name'), thing.name)
		self.assertIsNone(resolver(thing, 'email'))

	def test_engine_resolve_item(self):
		thing = {'name': 'Alice'}
		self.assertEqual(engine.resolve_item(thing, 'name'), thing['name'])
		with self.assertRaises(errors.SymbolResolutionError):
			engine.resolve_item(thing, 'email')

	def test_engine_resolve_item_recursively(self):
		thing = {'person': {'name': 'Alice'}}
		resolver = engine.to_recursive_resolver(engine.resolve_item)
		self.assertEqual(resolver(thing, 'person.name'), thing['person']['name'])
		with self.assertRaises(errors.SymbolResolutionError):
			resolver(thing, 'person.email')

	def test_engine_resolve_item_with_defaults(self):
		thing = {'name': 'Alice'}
		resolver = engine.to_default_resolver(engine.resolve_item)
		self.assertEqual(resolver(thing, 'name'), thing['name'])
		self.assertIsNone(resolver(thing, 'email'))

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

	def test_engine_builtins(self):
		builtins = engine.Builtins.from_defaults()
		self.assertIsInstance(builtins, engine.Builtins)
		self.assertIsNone(builtins.namespace)
		self.assertRegexpMatches(repr(builtins), r'<Builtins namespace=None keys=\(\'\S+\'(, \'\S+\')*\) >')

		self.assertIn('d', builtins)
		d_builtins = builtins['d']
		self.assertIsInstance(builtins, engine.Builtins)
		self.assertEqual(d_builtins.namespace, 'd')

		self.assertIn('today', d_builtins)
		today = d_builtins['today']
		self.assertIsInstance(today, datetime.date)

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
	def test_engin_rule_to_graphviz_2(self):
		rule = engine.Rule('"foo".length % 2 ? (bar > baz) : (bar < -baz)')
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

	def test_engine_rule_debug_parser(self):
		with open(os.devnull, 'w') as file_h:
			with contextlib.redirect_stderr(file_h):
				debug_rule = engine.DebugRule(self.rule_text)
		self.test_engine_rule_matches(rule=debug_rule)
		self.test_engine_rule_filter(rule=debug_rule)

if __name__ == '__main__':
	unittest.main()
