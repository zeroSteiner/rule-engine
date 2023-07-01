#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/builtins.py
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
import random
import string
import unittest

import rule_engine.ast as ast
import rule_engine.builtins as builtins
import rule_engine.engine as engine
import rule_engine.errors as errors

import dateutil.tz

try:
	import graphviz
except ImportError:
	has_graphviz = False
else:
	has_graphviz = True

class BuiltinsTests(unittest.TestCase):
	def assertBuiltinFunction(self, name, expected_result, *arguments):
		blts = builtins.Builtins.from_defaults()
		function = blts[name]
		function_type = blts.resolve_type(name)
		self.assertIsNot(
			function_type.minimum_arguments,
			ast.DataType.UNDEFINED,
			msg='builtin function should have a defined minimum number of arguments'
		)
		self.assertTrue(callable(function), msg='builtin functions should be callable')
		result = function(*arguments)
		self.assertEqual(result, expected_result, msg='builtin functions should return the expected result')
		result_type = ast.DataType.from_value(result)
		self.assertTrue(ast.DataType.is_compatible(result_type, function_type.return_type))
		return result

	def test_engine_builtins(self):
		blts = builtins.Builtins.from_defaults({'test': {'one': 1.0, 'two': 2.0}})
		self.assertIsInstance(blts, builtins.Builtins)
		self.assertIsNone(blts.namespace)
		self.assertRegex(repr(blts), r'<Builtins namespace=None keys=\(\'\S+\'(, \'\S+\')*\)')

		self.assertIn('test', blts)
		test_builtins = blts['test']
		self.assertIsInstance(test_builtins, builtins.Builtins)
		self.assertEqual(test_builtins.namespace, 'test')

		self.assertIn('today', blts)
		today = blts['today']
		self.assertIsInstance(today, datetime.date)

		self.assertIn('now', blts)
		now = blts['now']
		self.assertIsInstance(now, datetime.datetime)

		# test that builtins have correct type hints
		blts = builtins.Builtins.from_defaults(
			{'name': 'Alice'},
			value_types={'name': ast.DataType.STRING}
		)
		self.assertEqual(blts.resolve_type('name'), ast.DataType.STRING)
		self.assertEqual(blts.resolve_type('missing'), ast.DataType.UNDEFINED)
		context = engine.Context()
		context.builtins = blts
		engine.Rule('$name =~ ""')
		with self.assertRaises(errors.EvaluationError):
			engine.Rule('$name + 1', context=context)

	def test_engine_builtins_function_any(self):
		self.assertBuiltinFunction('any', True, [0, 1, 2])
		self.assertBuiltinFunction('any', False, [None])
		self.assertBuiltinFunction('any', False, [])

	def test_engine_builtins_function_all(self):
		self.assertBuiltinFunction('all', True, [1, 2])
		self.assertBuiltinFunction('all', False, [0, 1, 2])
		self.assertBuiltinFunction('all', False, [None])
		self.assertBuiltinFunction('all', True, [])

	def test_engine_builtins_function_sum(self):
		self.assertBuiltinFunction('sum', 10, [1, 2, 3, 4])

	def test_engine_buitins_function_map(self):
		self.assertBuiltinFunction('map', (2, 4, 6), lambda i: i * 2, [1, 2, 3])
		self.assertBuiltinFunction('map', ('A', 'B'), lambda c: c.upper(), ['A', 'B'])

	def test_engine_buitins_function_filter(self):
		self.assertBuiltinFunction('filter', (1, 3), lambda i: i % 2, [1, 2, 3])
		self.assertBuiltinFunction('filter', ('A', 'B'), lambda c: len(c), ['', 'A', 'B'])

	def test_engine_builtins_function_parse_datetime(self):
		now = datetime.datetime.now()
		self.assertBuiltinFunction('parse_datetime', now.replace(tzinfo=dateutil.tz.tzlocal()), now.isoformat())
		with self.assertRaises(errors.DatetimeSyntaxError):
			self.assertBuiltinFunction('parse_datetime', now, '')

	def test_engine_builtins_function_parse_timedelta(self):
		self.assertBuiltinFunction('parse_timedelta', datetime.timedelta(days=1), 'P1D')
		with self.assertRaises(errors.TimedeltaSyntaxError):
			self.assertBuiltinFunction('parse_timedelta', datetime.timedelta(), '')

	def test_engine_builtins_re_groups(self):
		context = engine.Context()
		rule = engine.Rule('words =~ "(\\w+) (\\w+) (\\w+)" and $re_groups[0] == word0', context=context)
		self.assertIsNone(context._tls.regex_groups)
		words = (
			''.join(random.choice(string.ascii_letters) for _ in range(random.randint(4, 12))),
			''.join(random.choice(string.ascii_letters) for _ in range(random.randint(4, 12))),
			''.join(random.choice(string.ascii_letters) for _ in range(random.randint(4, 12)))
		)
		self.assertTrue(rule.matches({'words': ' '.join(words), 'word0': words[0]}))
		self.assertEqual(context._tls.regex_groups, words)

		self.assertFalse(rule.matches({'words': ''.join(words), 'word0': words[0]}))
		self.assertIsNone(context._tls.regex_groups)
