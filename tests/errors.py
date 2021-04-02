#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/errors.py
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

import random
import string
import unittest

import rule_engine.errors as errors

class ResolutionErrorTests(unittest.TestCase):
	def test_attribute_error_repr(self):
		attribute_error = errors.AttributeResolutionError('doesnotexist', None)
		self.assertIn('suggestion', repr(attribute_error))

		suggestion = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		attribute_error = errors.AttributeResolutionError('doesnotexist', None, suggestion=suggestion)
		self.assertIn('suggestion', repr(attribute_error))
		self.assertIn(suggestion, repr(attribute_error))

	def test_symbol_error_repr(self):
		symbol_error = errors.SymbolResolutionError('doesnotexist')
		self.assertIn('suggestion', repr(symbol_error))

		suggestion = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		symbol_error = errors.SymbolResolutionError('doesnotexist', suggestion=suggestion)
		self.assertIn('suggestion', repr(symbol_error))
		self.assertIn(suggestion, repr(symbol_error))

class UndefinedSentinelTests(unittest.TestCase):
	def test_undefined_has_a_repr(self):
		self.assertEqual(repr(errors.UNDEFINED), 'UNDEFINED')

	def test_undefined_is_a_sentinel(self):
		self.assertIsNotNone(errors.UNDEFINED)
		self.assertIs(errors.UNDEFINED, errors.UNDEFINED)

	def test_undefined_is_falsy(self):
		self.assertFalse(errors.UNDEFINED)

if __name__ == '__main__':
	unittest.main()