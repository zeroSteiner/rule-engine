#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/ast/value_is.py
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
import unittest

import rule_engine.ast as ast

__all__ = ('ValueIsTests',)

inf = float('inf')
nan = float('nan')

class ValueIsTests(unittest.TestCase):
	_Case = collections.namedtuple('_Case', ('value', 'numeric', 'real', 'integer', 'natural'))
	cases = (
		#     value   numeric  real    integer natural
		_Case(-inf,   True,    False,  False,  False),
		_Case(-1.5,   True,    True,   False,  False),
		_Case(-1.0,   True,    True,   True,   False),
		_Case(-1,     True,    True,   True,   False),
		_Case(0,      True,    True,   True,   True ),
		_Case(1,      True,    True,   True,   True ),
		_Case(1.0,    True,    True,   True,   True ),
		_Case(1.5,    True,    True,   False,  False),
		_Case(inf,    True,    False,  False,  False),
		_Case(nan,    True,    False,  False,  False),
		_Case(True,   False,   False,  False,  False),
		_Case(False,  False,   False,  False,  False),
		_Case('',     False,   False,  False,  False),
		_Case(None,   False,   False,  False,  False),
	)
	def test_value_is_integer_number(self):
		for case in self.cases:
			self.assertEqual(ast.is_integer_number(case.value), case.integer)

	def test_value_is_natural_number(self):
		for case in self.cases:
			self.assertEqual(ast.is_natural_number(case.value), case.natural)

	def test_value_is_numeric(self):
		for case in self.cases:
			self.assertEqual(ast.is_numeric(case.value), case.numeric)

	def test_value_is_real_number(self):
		for case in self.cases:
			self.assertEqual(ast.is_real_number(case.value), case.real)

if __name__ == '__main__':
	unittest.main()
