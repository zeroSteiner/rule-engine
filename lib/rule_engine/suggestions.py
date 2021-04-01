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
import re

def jaro_distance(str1, str2):
	if str1 == str2:
		return 1.0

	str1_len = len(str1)
	str2_len = len(str2)
	max_len = max(str1_len, str2_len)
	match_distance = (max_len // 2) - 1
	str1_matches = [False] * max_len
	str2_matches = [False] * max_len
	matches = 0.0

	for i in range(str1_len):
		start = max(0, i - match_distance)
		end = min(i + match_distance, str2_len - 1) + 1
		for j in range(start, end):
			if not str2_matches[j] and str1[i] == str2[j]:
				str1_matches[i] = True
				str2_matches[j] = True
				matches += 1
				break

	if matches == 0.0:
		return 0.0

	k = 0
	transpositions = 0.0
	for i in range(str1_len):
		if not str1_matches[i]:
			continue
		while not str2_matches[k]:
			k += 1
		if str1[i] != str2[k]:
			transpositions += 1.0
		k += 1
	return ((matches / str1_len) + (matches / str2_len) + ((matches - transpositions / 2.0) / matches)) / 3.0

def jaro_winkler_distance(str1, str2, scale=0.1):
	jaro_dist = jaro_distance(str1, str2)
	if jaro_dist > 0.7:
		prefix = 0
		while prefix < min(len(str1), len(str2), 5) and str1[prefix] == str2[prefix]:
			prefix += 1
		jaro_dist += scale * prefix * (1 - jaro_dist)
	return jaro_dist

def jaro_winkler_similarity(*args, **kwargs):
	return 1 - jaro_winkler_distance(*args, **kwargs)

def _suggest(word, options):
	if not len(options):
		return None
	return sorted(options, key=functools.partial(jaro_winkler_similarity, word))[0]

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
