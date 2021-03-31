#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/suggestions.py
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

import functools
import itertools
import re

def _levenshtein(str1, str2):
	# calculate the levenshtein distance between two strings, 0 is a perfect match
	size_x = len(str1) + 1
	size_y = len(str2) + 1
	matrix = [[0] * size_y for _ in range(size_x)]
	for x in range(size_x):
		matrix[x][0] = x
	for y in range(size_y):
		matrix[0][y] = y

	for x, y in itertools.product(range(1, size_x), range(1, size_y)):
		if str1[x - 1] == str2[y - 1]:
			matrix[x][y] = min(
				matrix[x - 1][y] + 1,
				matrix[x - 1][y - 1],
				matrix[x][y - 1] + 1
			)
		else:
			matrix[x][y] = min(
				matrix[x - 1][y] + 1,
				matrix[x - 1][y - 1] + 1,
				matrix[x][y - 1] + 1
			)
	return (matrix[size_x - 1][size_y - 1])

def _suggest(word, options):
	if not len(options):
		return None
	return sorted(options, key=functools.partial(_levenshtein, word))[0]

def suggest_symbol(word, options):
	"""
	Select the best match for *word* from a list of value *options*. Values that are not suitable symbol names will be
	filtered out of *options*. If no match is found, this function will return None.

	:param str word: The original word to suggest an alternative for.
	:param tuple options: A list of strings to select the best match from.
	:return: The best replacement for *word*.
	:rtype: str
	"""
	from .parser import Parser  # avoid circular imports
	symbol_regex = '^' + Parser.get_token_regex('SYMBOL') + '$'
	return _suggest(word, [option for option in options if re.match(symbol_regex, option)])
