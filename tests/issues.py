#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/issues.py
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
import unittest

import rule_engine.engine as engine
import rule_engine.errors as errors
import rule_engine.types as types

import dateutil.tz

class GitHubIssueTests(unittest.TestCase):
	def test_number_10(self):
		value = random.randint(1, 10000)
		thing = {
			'c': {
				'c1': value,
			}
		}
		rule_text = 'c.c1 == ' + str(value)
		rule1 = engine.Rule(rule_text, context=engine.Context())
		rule2 = engine.Rule(rule_text, context=engine.Context(default_value=None))
		self.assertEqual(rule1.evaluate(thing), rule2.evaluate(thing))

	def test_number_14(self):
		context = engine.Context(
			type_resolver=engine.type_resolver_from_dict({
				'TEST_FLOAT': types.DataType.FLOAT,
			})
		)
		rule = engine.Rule(
			'(TEST_FLOAT == null ? 0 : TEST_FLOAT) < 42',
			context=context
		)
		rule.matches({'TEST_FLOAT': None})

	def test_number_19(self):
		context = engine.Context(
			type_resolver=engine.type_resolver_from_dict({
				'facts': types.DataType.MAPPING(
					key_type=types.DataType.STRING,
					value_type=types.DataType.STRING
				)
			})
		)
		rule = engine.Rule('facts.abc == "def"', context=context)
		self.assertTrue(rule.matches({'facts': {'abc': 'def'}}))

	def test_number_20(self):
		rule = engine.Rule('a / b ** 2')
		self.assertEqual(rule.evaluate({'a': 8, 'b': 4}), 0.5)

	def test_number_22(self):
		rules = ('object["timestamp"] > $now', 'object.timestamp > $now')
		for rule in rules:
			rule = engine.Rule(rule)
			self.assertFalse(rule.evaluate({
				'object': {'timestamp': datetime.datetime(2021, 8, 19)}
			}))

	def test_number_54(self):
		rules = (
			'count == 01',
			"test=='NOTTEST' and count==01 and other=='other'"
		)
		for rule in rules:
			with self.assertRaises(errors.FloatSyntaxError):
				engine.Rule(rule)

	def test_number_66(self):
		rule = engine.Rule('$parse_datetime("2020-01-01")')
		try:
			result = rule.evaluate({})
		except Exception:
			self.fail('evaluation raised an exception')
		self.assertEqual(result, datetime.datetime(2020, 1, 1, tzinfo=dateutil.tz.tzlocal()))

	def test_number_68(self):
		rule = engine.Rule('$min(items)')
		try:
			result = rule.evaluate({'items': [1, 2, 3, 4, 5, 6, 7, 8, 9]})
		except Exception:
			self.fail('evaluation raised an exception')
		self.assertEqual(result, 1)
