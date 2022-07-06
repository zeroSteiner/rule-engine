#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  examples/database.py
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
import csv
import json

import rule_engine

def isiterable(thing):
	return isinstance(thing, collections.abc.Iterable)

class Database(object):
	def __init__(self, data):
		self.data = data
		self._rule_context = rule_engine.Context(default_value=None)

	@classmethod
	def from_csv(cls, file_path, headers=None, skip_first=False):
		file_h = open(file_path, 'r')
		reader = csv.DictReader(file_h, headers)
		if skip_first:
			next(reader)
		rows = tuple(reader)
		file_h.close()
		return cls(rows)

	@classmethod
	def from_json(cls, file_path):
		with open(file_path, 'r') as file_h:
			data = json.load(file_h)
		return cls(data)

	def select(self, *names, from_=None, where='true', limit=None):
		data = self.data
		if from_ is not None:
			data = rule_engine.Rule(from_, context=self._rule_context).evaluate(data)
		if isinstance(data, collections.abc.Mapping):
			data = data.values()
		if not isiterable(data):
			raise ValueError('data source is not iterable')
		rule = rule_engine.Rule(where, context=self._rule_context)
		count = 0
		for match in rule.filter(data):
			if count == limit:
				break
			yield tuple(rule_engine.Rule(name, context=self._rule_context).evaluate(match) for name in names)
			count += 1
