#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/thread_safety.py
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
import queue
import random
import threading
import unittest

import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors

__all__ = ('ThreadSafetyTests',)

def testing_resolver(lock, thing, name):
	if name == 'lock':
		lock.acquire()
		return True
	return engine.resolve_item(thing, name)

class RuleThread(threading.Thread):
	def __init__(self, rule, thing):
		self.rule = rule
		self.thing = thing
		self.queue = queue.Queue()
		super(RuleThread, self).__init__()
		self.start()

	def run(self):
		self.queue.put(self.rule.evaluate(self.thing))

	def join(self, *args, **kwargs):
		super(RuleThread, self).join(*args, **kwargs)
		return self.queue.get()

class ThreadSafetyTests(unittest.TestCase):
	def test_tls_for_comprehension(self):
		context = engine.Context()
		rule = engine.Rule('[word for word in words][0]', context=context)
		rule.evaluate({'words': ('MainThread', 'Test')})
		# this isn't exactly a thread test since the assignment scope should be cleared after the comprehension is
		# complete
		self.assertEqual(len(context._tls.assignment_scopes), 0)

	def test_tls_for_regex1(self):
		context = engine.Context()
		rule = engine.Rule('words =~ "(\w+) \w+"', context=context)
		rule.evaluate({'words': 'MainThread Test'})
		self.assertEqual(context._tls.regex_groups, ('MainThread',))
		RuleThread(rule, {'words': 'AlternateThread Test'}).join()
		self.assertEqual(context._tls.regex_groups, ('MainThread',))

	def test_tls_for_regex2(self):
		lock = threading.RLock()
		context = engine.Context(resolver=functools.partial(testing_resolver, lock))
		rule = engine.Rule('words =~ "(\w+) \w+" and lock and $re_groups[0] == "MainThread"', context=context)
		self.assertTrue(rule.evaluate({'words': 'MainThread Test'}))
		lock.release()
		with lock:
			thread = RuleThread(rule, {'words': 'AlternateThread Test'})
			self.assertTrue(rule.evaluate({'words': 'MainThread Test'}))
			lock.release()
		self.assertFalse(thread.join())