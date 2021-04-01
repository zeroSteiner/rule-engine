#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/suggestions.py
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

import rule_engine.suggestions as suggestions

# JARO_WINKLER_TEST_CASES taken from the original whitepaper: see page 13, table 4
# https://www.census.gov/srd/papers/pdf/rr91-9.pdf
# not all JARO_WINKLER_TEST_CASES are a perfect match, so the table is a selection of those that are
JARO_WINKLER_TEST_CASES = (
	('shackleford', 'shackelford', 0.9848),
	('cunningham', 'cunnigham', 0.9833),
	('galloway', 'calloway', 0.9167),
	('lampley', 'campley', 0.9048),
	('michele', 'michelle', 0.9792),
	('jonathon', 'jonathan', 0.9583),
)

class JaroWinklerTests(unittest.TestCase):
	def test_jaro_winkler_distance(self):
		for str1, str2, distance in JARO_WINKLER_TEST_CASES:
			self.assertEqual(
				round(suggestions.jaro_winkler_distance(str1, str2), 4),
				distance,
				msg="({}, {}) != {}".format(str1, str2, distance)
			)

	def test_jaro_winkler_distance_match(self):
		strx = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		self.assertEqual(
			suggestions.jaro_winkler_distance(strx, strx),
			1.0
		)

	def test_jaro_winkler_similarity(self):
		for str1, str2, distance in JARO_WINKLER_TEST_CASES:
			similarity = round(1 - distance, 4)
			self.assertEqual(
				round(suggestions.jaro_winkler_similarity(str1, str2), 4),
				similarity,
				msg="({}, {}) != {}".format(str1, str2, similarity)
			)

	def test_jaro_winkler_similarity_match(self):
		strx = ''.join(random.choice(string.ascii_letters) for _ in range(10))
		self.assertEqual(
			suggestions.jaro_winkler_similarity(strx, strx),
			0.0
		)
