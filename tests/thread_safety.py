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
import copy
import random
import sys
import threading
import unittest
import unittest.mock
import weakref

import rule_engine.ast as ast
import rule_engine.engine as engine
import rule_engine.errors as errors
import rule_engine.types as types

__all__ = ('ChainThreadSafetyTests', 'ThreadSafetyTests')

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
        rule = engine.Rule(r'words =~ "(\\w+) \\w+"', context=context)
        rule.evaluate({'words': 'MainThread Test'})
        self.assertEqual(context._tls.regex_groups, ('MainThread',))
        RuleThread(rule, {'words': 'AlternateThread Test'}).join()
        self.assertEqual(context._tls.regex_groups, ('MainThread',))

    def test_tls_for_regex2(self):
        lock = threading.RLock()
        context = engine.Context(resolver=functools.partial(testing_resolver, lock))
        rule = engine.Rule(r'words =~ "(\\w+) \\w+" and lock and $re_groups[0] == "MainThread"', context=context)
        self.assertTrue(rule.evaluate({'words': 'MainThread Test'}))
        lock.release()
        with lock:
            thread = RuleThread(rule, {'words': 'AlternateThread Test'})
            self.assertTrue(rule.evaluate({'words': 'MainThread Test'}))
            lock.release()
        self.assertFalse(thread.join())

    def test_null_member_deprecation_warns_once(self):
        context = engine.Context(type_resolver={'thing': types.DataType.ARRAY(types.DataType.STRING)})
        rule = engine.Rule('thing', context=context)
        barrier = threading.Barrier(8)
        def evaluate():
            barrier.wait()
            for _ in range(50):
                rule.evaluate({'thing': (None,)})
        with unittest.mock.patch('warnings.warn') as warn:
            threads = [threading.Thread(target=evaluate) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(warn.call_count, 1)

class _ResultThread(threading.Thread):
    def __init__(self, function, *function_args):
        super(_ResultThread, self).__init__(daemon=True)
        self.function = function
        self.function_args = function_args
        self.result = None
        self.exception = None

    def run(self):
        try:
            self.result = self.function(*self.function_args)
        except BaseException as error:
            self.exception = error

    def join_result(self, test_case, timeout=5):
        self.join(timeout)
        test_case.assertFalse(self.is_alive(), 'the thread did not finish')
        if self.exception is not None:
            raise self.exception
        return self.result

class _ReentrantIndex(object):
    def __init__(self, chain, value):
        self.chain = chain
        self.value = value

    def __index__(self):
        self.chain.append(engine.Rule('true'), 'from-index')
        return self.value

def _call_in_thread(test_case, function, *args):
    # call *function* in another thread so a deadlock fails the test instead of hanging it
    thread = _ResultThread(function, *args)
    thread.start()
    return thread.join_result(test_case)

class ChainThreadSafetyTests(unittest.TestCase):
    def test_chain_concurrent_modifications_are_not_lost(self):
        thread_count = 8
        entry_count = 250
        chain = engine.Chain()
        rule = engine.Rule('true')
        barrier = threading.Barrier(thread_count)
        def add_entries(thread_id):
            barrier.wait(timeout=5)
            for index in range(entry_count):
                if index % 2:
                    chain.append(rule, (thread_id, index))
                else:
                    chain.insert(0, rule, (thread_id, index))

        switch_interval = sys.getswitchinterval()
        # switch threads as often as possible to make a lost update likely if the chain is not locked correctly
        sys.setswitchinterval(1e-6)
        try:
            threads = [_ResultThread(add_entries, thread_id) for thread_id in range(thread_count)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join_result(self)
        finally:
            sys.setswitchinterval(switch_interval)
        self.assertEqual(len(chain), thread_count * entry_count)
        expected = set((thread_id, index) for thread_id in range(thread_count) for index in range(entry_count))
        self.assertEqual(set(entry.value for entry in chain), expected)

    def test_chain_concurrent_deletes_are_not_lost(self):
        thread_count = 8
        delete_count = 250
        rule = engine.Rule('true')
        chain = engine.Chain([(rule, index) for index in range(thread_count * delete_count + 1)])
        barrier = threading.Barrier(thread_count)
        def delete_entries():
            barrier.wait(timeout=5)
            return [chain.delete(0).value for _ in range(delete_count)]

        switch_interval = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        try:
            threads = [_ResultThread(delete_entries) for _ in range(thread_count)]
            for thread in threads:
                thread.start()
            deleted = [value for thread in threads for value in thread.join_result(self)]
        finally:
            sys.setswitchinterval(switch_interval)
        # each entry is deleted exactly once and the last one remains
        self.assertEqual(sorted(deleted), list(range(thread_count * delete_count)))
        self.assertEqual([entry.value for entry in chain], [thread_count * delete_count])

    def test_chain_concurrent_flush_is_not_lost(self):
        rule = engine.Rule('true')
        resurrected = 0
        switch_interval = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        try:
            for _ in range(100):
                chain = engine.Chain([(rule, ('old', index)) for index in range(20)])
                started = threading.Event()
                stop = threading.Event()
                def insert_entries():
                    index = 0
                    while not stop.is_set():
                        chain.insert(0, rule, ('new', index))
                        index += 1
                        started.set()

                thread = _ResultThread(insert_entries)
                thread.start()
                self.assertTrue(started.wait(timeout=5))
                chain.flush()
                stop.set()
                thread.join_result(self)
                if any(entry.value[0] == 'old' for entry in chain):
                    resurrected += 1
        finally:
            sys.setswitchinterval(switch_interval)
        self.assertEqual(resurrected, 0, 'entries present before flush() survived it')

    def test_chain_type_resolver_can_modify_chain(self):
        # the rule is compiled before the lock is acquired, so the type resolver can modify the chain
        def type_resolver(name):
            if name == 'trigger':
                chain.append(engine.Rule('true'), 'nested')
            return types.DataType.UNDEFINED

        chain = engine.Chain(context=engine.Context(type_resolver=type_resolver))
        _call_in_thread(self, chain.append, 'trigger', 'outer')
        _call_in_thread(self, chain.insert, 0, 'trigger', 'outer2')
        self.assertEqual([entry.value for entry in chain], ['outer2', 'nested', 'outer', 'nested'])

    def test_chain_index_can_modify_chain(self):
        chain = engine.Chain([('true', 'first')])
        _call_in_thread(self, chain.insert, _ReentrantIndex(chain, 0), 'true', 'inserted')
        self.assertEqual([entry.value for entry in chain], ['inserted', 'first', 'from-index'])
        entry = _call_in_thread(self, chain.delete, _ReentrantIndex(chain, 0))
        self.assertEqual(entry.value, 'inserted')
        self.assertEqual([entry.value for entry in chain], ['first', 'from-index', 'from-index'])

    def test_chain_flush_finalizer_can_modify_chain(self):
        class Target(object):
            pass

        chain = engine.Chain()
        target = Target()
        chain.append(engine.Rule('true'), target)
        weakref.finalize(target, chain.append, engine.Rule('true'), 'from-finalizer')
        del target
        _call_in_thread(self, chain.flush)
        self.assertEqual([entry.value for entry in chain], ['from-finalizer'])

    def test_chain_copy_has_its_own_lock(self):
        chain = engine.Chain([('true', 'first')])
        chain2 = copy.copy(chain)
        with chain._lock:
            _call_in_thread(self, chain2.append, 'true', 'second')
        self.assertEqual([entry.value for entry in chain2], ['first', 'second'])
        self.assertEqual([entry.value for entry in chain], ['first'])

    def test_chain_evaluate_isolated_from_concurrent_mutation(self):
        entered = threading.Event()
        release = threading.Event()
        released = []
        def resolver(thing, name):
            if name == 'gate':
                entered.set()
                released.append(release.wait(timeout=5))
                return False
            return engine.resolve_item(thing, name)

        chain = engine.Chain([('gate', 'first'), ('true', 'second')], context=engine.Context(resolver=resolver))
        thread = _ResultThread(chain.evaluate, {})
        thread.start()
        self.assertTrue(entered.wait(timeout=5))
        # the chain is modified while the thread is evaluating it, this must not block on the in-progress evaluation
        chain.flush()
        chain.append(engine.Rule('true'), 'replacement')
        release.set()
        self.assertEqual(thread.join_result(self), 'second')
        self.assertEqual(released, [True])
        self.assertEqual(chain.evaluate({}), 'replacement')
