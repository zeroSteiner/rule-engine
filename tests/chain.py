#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/chain.py
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
import contextlib
import copy
import enum
import io
import pickle
import unittest

import rule_engine
import rule_engine.engine as engine
import rule_engine.errors as errors

__all__ = ('ChainEntryTests', 'ChainMutationTests', 'ChainSerializationTests', 'ChainTests')

class Action(enum.Enum):
    ACCEPT = 'accept'
    DROP = 'drop'

_Packet = collections.namedtuple('_Packet', ('port', 'source'))

class _Index(object):
    def __init__(self, value):
        self.value = value

    def __index__(self):
        return self.value

class ChainTests(unittest.TestCase):
    def test_chain_empty(self):
        chain = engine.Chain()
        self.assertEqual(len(chain), 0)
        self.assertFalse(chain)
        self.assertEqual(list(chain), [])
        self.assertIsNone(chain.find({}))
        with self.assertRaises(errors.ChainExhaustedError):
            chain.evaluate({})

    def test_chain_empty_with_default(self):
        chain = engine.Chain(default_value=Action.DROP)
        self.assertIs(chain.evaluate({}), Action.DROP)

    def test_chain_first_match_wins(self):
        chain = engine.Chain([
            ('port == 22', Action.ACCEPT),
            ('port > 0', Action.DROP),
        ])
        self.assertIs(chain.evaluate({'port': 22}), Action.ACCEPT)
        self.assertIs(chain.evaluate({'port': 80}), Action.DROP)

    def test_chain_skips_non_matching_rules(self):
        chain = engine.Chain([
            ('port == 22', 'ssh'),
            ('port == 80', 'http'),
            ('port == 443', 'https'),
        ])
        self.assertEqual(chain.evaluate({'port': 443}), 'https')

    def test_chain_returns_default_value(self):
        chain = engine.Chain([('port == 22', Action.ACCEPT)], default_value=Action.DROP)
        self.assertIs(chain.evaluate({'port': 80}), Action.DROP)

    def test_chain_returns_falsy_default_value(self):
        for default_value in (None, False, 0, ''):
            with self.subTest(default_value=default_value):
                chain = engine.Chain([('port == 22', Action.ACCEPT)], default_value=default_value)
                self.assertIs(chain.evaluate({'port': 80}), default_value)

    def test_chain_exhausted_raises(self):
        chain = engine.Chain([('port == 22', Action.ACCEPT)])
        thing = {'port': 80}
        with self.assertRaises(errors.ChainExhaustedError) as context:
            chain.evaluate(thing)
        self.assertIs(context.exception.thing, thing)
        self.assertEqual(context.exception.args, (context.exception.message,))

    def test_chain_default_value_can_be_changed(self):
        chain = engine.Chain([('port == 22', Action.ACCEPT)])
        chain.default_value = Action.DROP
        self.assertIs(chain.evaluate({'port': 80}), Action.DROP)
        chain.default_value = errors.UNDEFINED
        with self.assertRaises(errors.ChainExhaustedError):
            chain.evaluate({'port': 80})

    def test_chain_find_returns_entry(self):
        chain = engine.Chain([
            ('port == 22', Action.ACCEPT),
            ('port == 80', Action.DROP),
        ])
        self.assertIs(chain.find({'port': 22}), chain[0])
        self.assertIs(chain.find({'port': 80}), chain[1])

    def test_chain_find_ignores_default_value(self):
        chain = engine.Chain([('port == 22', Action.ACCEPT)], default_value=Action.DROP)
        self.assertIsNone(chain.find({'port': 80}))

    def test_chain_find_with_none_value(self):
        chain = engine.Chain([('port == 22', None)], default_value=Action.DROP)
        entry = chain.find({'port': 22})
        self.assertIsInstance(entry, engine.ChainEntry)
        self.assertIsNone(entry.value)
        self.assertIsNone(chain.evaluate({'port': 22}))

    def test_chain_index(self):
        chain = engine.Chain([
            ('port == 22', Action.ACCEPT),
            ('port == 80', Action.DROP),
            ('true', Action.DROP),
        ])
        self.assertEqual(chain.index(chain.find({'port': 80})), 1)
        self.assertEqual(chain.index(chain.find({'port': 443})), 2)
        for index, entry in enumerate(chain):
            self.assertEqual(chain.index(entry), index)

    def test_chain_index_compares_entries_as_tuples(self):
        rule = engine.Rule('port == 22')
        chain = engine.Chain([(rule, Action.ACCEPT), ('true', Action.DROP), (rule, Action.ACCEPT)])
        self.assertEqual(chain.index(engine.ChainEntry(rule, Action.ACCEPT)), 0)
        self.assertEqual(chain.index((rule, Action.ACCEPT)), 0)
        # an entry that is equal to an earlier one has the index of the earlier one, which is also the one find returns
        self.assertEqual(chain.index(chain[2]), 0)
        self.assertIs(chain.find({'port': 22}), chain[0])

    def test_chain_index_missing_entry(self):
        chain = engine.Chain([('port == 22', Action.ACCEPT)])
        # text rules are compiled into separate rules, which are not equal even though they have the same text
        other_chain = engine.Chain([('port == 22', Action.ACCEPT)])
        for entry in (other_chain[0], engine.ChainEntry(chain[0].rule, Action.DROP), (chain[0].rule,), None):
            with self.subTest(entry=entry):
                with self.assertRaisesRegex(ValueError, r'^entry is not in the chain$'):
                    chain.index(entry)
        with self.assertRaisesRegex(ValueError, r'^entry is not in the chain$'):
            engine.Chain().index(chain[0])

    def test_chain_index_propagates_comparison_errors(self):
        class Uncomparable(object):
            def __eq__(self, other):
                raise ValueError('can not compare')
            __hash__ = None
        rule = engine.Rule('true')
        chain = engine.Chain([(rule, Uncomparable()), (rule, Uncomparable())])
        self.assertEqual(chain.index(chain[0]), 0)
        # comparing the second entry to the first compares their values because their rules are the same
        with self.assertRaisesRegex(ValueError, r'^can not compare$'):
            chain.index(chain[1])

    def test_chain_truthy_result_matches(self):
        chain = engine.Chain([('name', 'named')], default_value='anonymous')
        self.assertEqual(chain.evaluate({'name': 'alice'}), 'named')
        self.assertEqual(chain.evaluate({'name': ''}), 'anonymous')

    def test_chain_text_rules_share_context(self):
        chain = engine.Chain([
            ('port == 22', Action.ACCEPT),
            ('source == "10.0.0.1"', Action.DROP),
        ])
        self.assertIsInstance(chain.context, engine.Context)
        for entry in chain:
            self.assertIs(entry.rule.context, chain.context)
        self.assertEqual(chain.context.symbols, {'port', 'source'})

    def test_chain_custom_context(self):
        context = engine.Context(resolver=engine.resolve_attribute)
        chain = engine.Chain([('port == 22', Action.ACCEPT)], default_value=Action.DROP, context=context)
        self.assertIs(chain.context, context)
        self.assertIs(chain[0].rule.context, context)
        self.assertIs(chain.evaluate(_Packet(port=22, source='10.0.0.1')), Action.ACCEPT)
        self.assertIs(chain.evaluate(_Packet(port=80, source='10.0.0.1')), Action.DROP)

    def test_chain_context_default_value_is_separate(self):
        # the context's default value applies to missing symbols, the chain's applies when no rule matches
        context = engine.Context(default_value=None)
        chain = engine.Chain([('port == 22', Action.ACCEPT)], default_value=Action.DROP, context=context)
        self.assertIs(chain.evaluate({}), Action.DROP)
        chain = engine.Chain([('port == 22', Action.ACCEPT)], context=context)
        with self.assertRaises(errors.ChainExhaustedError):
            chain.evaluate({})

    def test_chain_rule_objects_keep_their_context(self):
        context = engine.Context(resolver=engine.resolve_attribute)
        rule = engine.Rule('source == "10.0.0.1"', context=context)
        chain = engine.Chain([(rule, Action.ACCEPT), ('port == 80', Action.DROP)])
        self.assertIs(chain[0].rule, rule)
        self.assertIs(chain[0].rule.context, context)
        self.assertIsNot(chain[1].rule.context, context)
        self.assertIs(chain[1].rule.context, chain.context)
        self.assertEqual(context.symbols, {'source'})
        self.assertEqual(chain.context.symbols, {'port'})

    def test_chain_accepts_debug_rule(self):
        # the debug parser prints ply's debug output
        with contextlib.redirect_stderr(io.StringIO()):
            rule = engine.DebugRule('port == 22')
        chain = engine.Chain([(rule, Action.ACCEPT)])
        self.assertIs(chain[0].rule, rule)
        self.assertIs(chain.evaluate({'port': 22}), Action.ACCEPT)

    def test_chain_evaluation_errors_propagate(self):
        chain = engine.Chain([
            ('missing == 1', Action.DROP),
            ('true', Action.ACCEPT),
        ])
        with self.assertRaises(errors.SymbolResolutionError) as context:
            chain.evaluate({})
        self.assertNotIsInstance(context.exception, errors.ChainExhaustedError)
        with self.assertRaises(errors.SymbolResolutionError):
            chain.find({})

    def test_chain_evaluation_errors_after_match_are_not_reached(self):
        chain = engine.Chain([
            ('true', Action.ACCEPT),
            ('missing == 1', Action.DROP),
        ])
        self.assertIs(chain.evaluate({}), Action.ACCEPT)

    def test_chain_invalid_rule_type(self):
        for rule in (1, None, b'true', engine.Context()):
            with self.subTest(rule=rule):
                with self.assertRaisesRegex(TypeError, r'^chain entry #1 rule must be a str or Rule instance'):
                    engine.Chain([('true', Action.ACCEPT), (rule, Action.ACCEPT)])

    def test_chain_invalid_entry_does_not_compile_rules(self):
        context = engine.Context()
        for entries in ([('port == 22', 1), (42, 2)], [('port == 22', 1), 'port == 80'], [('port == 22', 1), ()]):
            with self.subTest(entries=entries):
                with self.assertRaises((TypeError, ValueError)):
                    engine.Chain(entries, context=context)
                self.assertEqual(context.symbols, set())

    def test_chain_invalid_entry_type(self):
        for entry in ('ab', b'ab', 1, None, {'rule': 'true', 'value': 1}, {'true', 'false'}):
            with self.subTest(entry=entry):
                with self.assertRaisesRegex(TypeError, r'^chain entry #1 must be a \(rule, value\) pair'):
                    engine.Chain([('true', Action.ACCEPT), entry])

    def test_chain_invalid_entry_length(self):
        for entry in ((), ('true',), ('true', Action.ACCEPT, Action.DROP)):
            with self.subTest(entry=entry):
                message = r'^chain entry #0 has length {0}; 2 is required$'.format(len(entry))
                with self.assertRaisesRegex(ValueError, message):
                    engine.Chain([entry])

    def test_chain_invalid_entries_type(self):
        with self.assertRaises(TypeError):
            engine.Chain({'true': Action.ACCEPT})
        with self.assertRaises(TypeError):
            engine.Chain(1)

    def test_chain_rule_syntax_error_propagates(self):
        with self.assertRaises(errors.RuleSyntaxError):
            engine.Chain([('port ==', Action.ACCEPT)])

    def test_chain_accepts_iterables(self):
        chain = engine.Chain(entry for entry in [('port == 22', Action.ACCEPT)])
        self.assertEqual(len(chain), 1)
        chain = engine.Chain([['port == 22', Action.ACCEPT]])
        self.assertEqual(len(chain), 1)
        chain = engine.Chain({'port == 22': Action.ACCEPT, 'port == 80': Action.DROP}.items())
        self.assertEqual([entry.value for entry in chain], [Action.ACCEPT, Action.DROP])

    def test_chain_from_chain(self):
        chain = engine.Chain([('port == 22', Action.ACCEPT)], default_value=Action.DROP)
        chain2 = engine.Chain(chain)
        self.assertEqual(len(chain2), 1)
        self.assertIs(chain2[0].rule, chain[0].rule)
        self.assertIs(chain2.default_value, errors.UNDEFINED)

    def test_chain_iteration_order(self):
        entries = [('port == 22', 'ssh'), ('port == 80', 'http'), ('port == 443', 'https')]
        chain = engine.Chain(entries)
        self.assertEqual(len(chain), 3)
        for (text, value), entry in zip(entries, chain):
            self.assertIsInstance(entry, engine.ChainEntry)
            self.assertEqual(entry.rule.text, text)
            self.assertEqual(entry.value, value)
        rule, value = chain[0]
        self.assertEqual(rule.text, 'port == 22')
        self.assertEqual(value, 'ssh')

    def test_chain_getitem(self):
        chain = engine.Chain([('port == 22', 'ssh'), ('port == 80', 'http')])
        self.assertEqual(chain[0].value, 'ssh')
        self.assertEqual(chain[-1].value, 'http')
        self.assertEqual(chain[True].value, 'http')
        self.assertEqual(chain[_Index(1)].value, 'http')
        for index in (2, -3):
            with self.subTest(index=index):
                with self.assertRaisesRegex(IndexError, r'^chain index out of range$'):
                    chain[index]
        with self.assertRaises(TypeError):
            chain['0']

    def test_chain_slice(self):
        context = engine.Context()
        default_value = object()
        chain = engine.Chain(
            [('port == 22', 'ssh'), ('port == 80', 'http'), ('port == 443', 'https')],
            default_value=default_value,
            context=context
        )
        slices = (
            slice(None),
            slice(1, None),
            slice(None, -1),
            slice(None, None, -1),
            slice(None, None, 2),
            slice(5, None),
            slice(_Index(1), _Index(2))
        )
        for index in slices:
            with self.subTest(index=index):
                chain2 = chain[index]
                self.assertIsInstance(chain2, engine.Chain)
                self.assertIsNot(chain2, chain)
                self.assertIs(chain2.default_value, default_value)
                self.assertIs(chain2.context, context)
                expected = list(chain)[index]
                self.assertEqual(len(chain2), len(expected))
                for entry, expected_entry in zip(chain2, expected):
                    self.assertIs(entry, expected_entry)
        with self.assertRaises(TypeError):
            chain['0':]

    def test_chain_slice_evaluate(self):
        chain = engine.Chain([('port == 22', Action.ACCEPT), ('port == 80', Action.DROP), ('true', Action.DROP)])
        chain2 = chain[:-1]
        self.assertIs(chain2.evaluate({'port': 22}), Action.ACCEPT)
        with self.assertRaises(errors.ChainExhaustedError):
            chain2.evaluate({'port': 443})
        self.assertIs(chain[1:].evaluate({'port': 22}), Action.DROP)
        self.assertEqual(chain[1:].index(chain[2]), 1)

    def test_chain_slice_subclass(self):
        class CustomChain(engine.Chain):
            pass
        chain = CustomChain([('true', Action.ACCEPT)])
        self.assertIsInstance(chain[:], CustomChain)

    def test_chain_repr(self):
        chain = engine.Chain([('port == 22', Action.ACCEPT)], default_value=Action.DROP)
        self.assertEqual(repr(chain), '<Chain entries=1 default_value=<Action.DROP: \'drop\'> >')
        self.assertEqual(repr(engine.Chain()), '<Chain entries=0 default_value=UNDEFINED >')

    def test_chain_exports(self):
        self.assertIs(rule_engine.Chain, engine.Chain)
        self.assertIs(rule_engine.ChainExhaustedError, errors.ChainExhaustedError)
        self.assertIn('Chain', rule_engine.__all__)
        self.assertIn('ChainExhaustedError', rule_engine.__all__)

class ChainEntryTests(unittest.TestCase):
    def test_chain_entry_fields(self):
        rule = engine.Rule('true')
        entry = engine.ChainEntry(rule, Action.ACCEPT)
        self.assertEqual(engine.ChainEntry._fields, ('rule', 'value'))
        self.assertIs(entry.rule, rule)
        self.assertIs(entry.value, Action.ACCEPT)
        self.assertEqual(entry, (rule, Action.ACCEPT))
        rule2, value = entry
        self.assertIs(rule2, rule)
        self.assertIs(value, Action.ACCEPT)

    def test_chain_entry_pickle(self):
        entry = pickle.loads(pickle.dumps(engine.ChainEntry(engine.Rule('port == 22'), Action.ACCEPT)))
        self.assertIsInstance(entry, engine.ChainEntry)
        self.assertTrue(entry.rule.matches({'port': 22}))
        self.assertIs(entry.value, Action.ACCEPT)

class ChainMutationTests(unittest.TestCase):
    def test_chain_append(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        entry = chain.append('port == 80', 'http')
        self.assertIsInstance(entry, engine.ChainEntry)
        self.assertIs(chain[-1], entry)
        self.assertEqual(len(chain), 2)
        self.assertIs(entry.rule.context, chain.context)
        self.assertEqual(chain.evaluate({'port': 80}), 'http')

    def test_chain_append_rule_object(self):
        rule = engine.Rule('port == 80')
        chain = engine.Chain()
        entry = chain.append(rule, 'http')
        self.assertIs(entry.rule, rule)
        self.assertIs(chain[0], entry)

    def test_chain_append_invalid_rule_leaves_chain_unchanged(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        entries = list(chain)
        with self.assertRaisesRegex(TypeError, r'^chain rule must be a str or Rule instance, not int$'):
            chain.append(1, 'invalid')
        with self.assertRaises(errors.RuleSyntaxError):
            chain.append('port ==', 'invalid')
        self.assertEqual(list(chain), entries)

    def test_chain_insert(self):
        chain = engine.Chain([('port == 22', 'ssh'), ('port == 80', 'http')])
        entry = chain.insert(0, 'port == 21', 'ftp')
        self.assertIs(chain[0], entry)
        self.assertIs(entry.rule.context, chain.context)
        chain.insert(2, 'port == 23', 'telnet')
        chain.insert(4, engine.Rule('port == 443'), 'https')
        self.assertEqual([entry.value for entry in chain], ['ftp', 'ssh', 'telnet', 'http', 'https'])

    def test_chain_insert_negative_index(self):
        chain = engine.Chain([('port == 22', 'ssh'), ('true', 'other')])
        entry = chain.insert(-1, 'port == 80', 'http')
        self.assertIs(chain[1], entry)
        self.assertEqual([entry.value for entry in chain], ['ssh', 'http', 'other'])

    def test_chain_insert_out_of_range_index(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        chain.insert(100, 'port == 80', 'http')
        chain.insert(-100, 'port == 21', 'ftp')
        self.assertEqual([entry.value for entry in chain], ['ftp', 'ssh', 'http'])

    def test_chain_insert_huge_index(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        chain.insert(2 ** 64, 'port == 80', 'http')
        chain.insert(-2 ** 64, 'port == 21', 'ftp')
        self.assertEqual([entry.value for entry in chain], ['ftp', 'ssh', 'http'])

    def test_chain_insert_invalid_index_does_not_compile_rule(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        entries = list(chain)
        with self.assertRaises(TypeError):
            chain.insert('0', 'unique_symbol == 1', 'invalid')
        self.assertEqual(list(chain), entries)
        self.assertNotIn('unique_symbol', chain.context.symbols)

    def test_chain_insert_invalid_rule_leaves_chain_unchanged(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        entries = list(chain)
        with self.assertRaises(TypeError):
            chain.insert(0, None, 'invalid')
        with self.assertRaises(errors.RuleSyntaxError):
            chain.insert(0, 'port ==', 'invalid')
        self.assertEqual(list(chain), entries)

    def test_chain_delete(self):
        chain = engine.Chain([('port == 22', 'ssh'), ('port == 80', 'http'), ('port == 443', 'https')])
        entry = chain[1]
        self.assertIs(chain.delete(1), entry)
        self.assertEqual([entry.value for entry in chain], ['ssh', 'https'])
        self.assertEqual(chain.delete(-1).value, 'https')
        self.assertEqual([entry.value for entry in chain], ['ssh'])
        self.assertEqual(chain.evaluate({'port': 22}), 'ssh')

    def test_chain_delete_invalid_index_leaves_chain_unchanged(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        entries = list(chain)
        for index in (1, -2):
            with self.subTest(index=index):
                with self.assertRaisesRegex(IndexError, r'^chain index out of range$'):
                    chain.delete(index)
        with self.assertRaises(TypeError):
            chain.delete('0')
        for index in (2 ** 64, -2 ** 64):
            with self.subTest(index=index):
                with self.assertRaisesRegex(IndexError, r'^chain index out of range$'):
                    chain.delete(index)
        self.assertEqual(list(chain), entries)
        with self.assertRaises(IndexError):
            engine.Chain().delete(0)

    def test_chain_flush(self):
        chain = engine.Chain([('port == 22', 'ssh')], default_value='other')
        self.assertIsNone(chain.flush())
        self.assertEqual(len(chain), 0)
        self.assertEqual(chain.default_value, 'other')
        self.assertEqual(chain.evaluate({'port': 22}), 'other')
        chain.flush()
        chain.append('port == 22', 'ssh')
        self.assertEqual(chain.evaluate({'port': 22}), 'ssh')

    def test_chain_flush_without_default_value(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        chain.flush()
        with self.assertRaises(errors.ChainExhaustedError):
            chain.evaluate({'port': 22})

    def test_chain_index_follows_modifications(self):
        chain = engine.Chain([('port == 22', 'ssh'), ('port == 80', 'http')])
        entry = chain.find({'port': 80})
        chain.insert(0, 'port == 21', 'ftp')
        self.assertEqual(chain.index(entry), 2)
        self.assertEqual(chain.index(chain.append('port == 443', 'https')), 3)
        self.assertIs(chain.delete(chain.index(entry)), entry)
        with self.assertRaises(ValueError):
            chain.index(entry)

    def test_chain_slice_modifications_are_independent(self):
        chain = engine.Chain([('port == 22', 'ssh'), ('port == 80', 'http')])
        chain2 = chain[:]
        self.assertIsNot(chain2._lock, chain._lock)
        entry = chain2.append('port == 443', 'https')
        self.assertIs(entry.rule.context, chain.context)
        chain.delete(0)
        chain2.default_value = 'other'
        self.assertEqual([entry.value for entry in chain], ['http'])
        self.assertIs(chain.default_value, errors.UNDEFINED)
        self.assertEqual([entry.value for entry in chain2], ['ssh', 'http', 'https'])

    def test_chain_iterator_is_a_snapshot(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        iterator = iter(chain)
        chain.append('port == 80', 'http')
        self.assertEqual([entry.value for entry in iterator], ['ssh'])
        # modifying the chain while iterating over it neither fails nor iterates over the new entries
        for entry in chain:
            chain.append(entry.rule, entry.value)
        self.assertEqual([entry.value for entry in chain], ['ssh', 'http', 'ssh', 'http'])

    def test_chain_mutation_during_evaluate_uses_snapshot(self):
        replacement = engine.Rule('true')
        def resolver(thing, name):
            if name == 'mutate':
                chain.flush()
                chain.append(replacement, 'new')
                return False
            return engine.resolve_item(thing, name)

        chain = engine.Chain([('mutate', 'old'), ('true', 'other')], context=engine.Context(resolver=resolver))
        self.assertEqual(chain.evaluate({}), 'other')
        self.assertEqual(chain.evaluate({}), 'new')

    def test_chain_index_uses_snapshot(self):
        class InsertOnCompare(object):
            def __init__(self):
                self.chain = None

            def __eq__(self, other):
                if self.chain is not None:
                    chain, self.chain = self.chain, None
                    chain.insert(0, 'false', 'inserted')
                return False

            __hash__ = None

        rule = engine.Rule('true')
        value = InsertOnCompare()
        chain = engine.Chain([(rule, value), (rule, 'target')])
        entry = chain[1]
        value.chain = chain
        # the comparison inserts an entry while the chain is being searched, which only affects the next search
        self.assertEqual(chain.index(entry), 1)
        self.assertEqual(chain.index(entry), 2)

    def test_chain_slice_uses_snapshot(self):
        class InsertingIndex(object):
            def __init__(self, chain):
                self.chain = chain

            def __index__(self):
                self.chain.insert(0, 'false', 'inserted')
                return 0

        chain = engine.Chain([('true', 'a'), ('true', 'b')])
        self.assertEqual([entry.value for entry in chain[InsertingIndex(chain):]], ['a', 'b'])
        self.assertEqual(len(chain), 3)

    def test_chain_copy_mutations_are_independent(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        chain2 = copy.copy(chain)
        self.assertIsNot(chain2._lock, chain._lock)
        chain2.append('port == 80', 'http')
        chain.delete(0)
        self.assertEqual(len(chain), 0)
        self.assertEqual([entry.value for entry in chain2], ['ssh', 'http'])

    def test_chain_mutable_after_pickle(self):
        chain = engine.Chain([('port == 22', 'ssh')])
        chain.insert(0, 'port == 21', 'ftp')
        chain.append('port == 80', 'http')
        chain.delete(1)
        for chain2 in (pickle.loads(pickle.dumps(chain)), copy.deepcopy(chain)):
            with self.subTest(chain=chain2):
                self.assertEqual([entry.value for entry in chain2], ['ftp', 'http'])
                entry = chain2.append('port == 443', 'https')
                self.assertIs(entry.rule.context, chain2.context)
                self.assertEqual(chain2.evaluate({'port': 443}), 'https')
                chain2.flush()
                self.assertEqual(len(chain2), 0)
        self.assertEqual(len(chain), 2)

class ChainSerializationTests(unittest.TestCase):
    def _make_chain(self, **kwargs):
        return engine.Chain([
            ('port == 22', Action.ACCEPT),
            ('source == "10.0.0.1"', Action.DROP),
        ], **kwargs)

    def test_chain_pickle(self):
        chain = self._make_chain(default_value=Action.DROP)
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.subTest(protocol=protocol):
                chain2 = pickle.loads(pickle.dumps(chain, protocol=protocol))
                self.assertIsInstance(chain2, engine.Chain)
                self.assertEqual(len(chain2), 2)
                self.assertEqual([entry.rule.text for entry in chain2], [entry.rule.text for entry in chain])
                for entry in chain2:
                    self.assertIsInstance(entry, engine.ChainEntry)
                self.assertIs(chain2.default_value, Action.DROP)
                self.assertIs(chain2.evaluate({'port': 22, 'source': '10.0.0.1'}), Action.ACCEPT)
                self.assertIs(chain2.evaluate({'port': 80, 'source': '10.0.0.1'}), Action.DROP)
                self.assertIs(chain2.evaluate({'port': 80, 'source': '10.0.0.2'}), Action.DROP)
                self.assertIs(chain2.find({'port': 80, 'source': '10.0.0.1'}), chain2[1])

    def test_chain_pickle_index(self):
        chain = self._make_chain()
        chain2 = pickle.loads(pickle.dumps(chain))
        self.assertEqual(chain2.index(chain2.find({'port': 80, 'source': '10.0.0.1'})), 1)
        # the rules are recreated when the chain is loaded, so the original entries are not in it
        with self.assertRaises(ValueError):
            chain2.index(chain[1])

    def test_chain_slice_pickle(self):
        chain = pickle.loads(pickle.dumps(self._make_chain(default_value=Action.ACCEPT)[1:]))
        self.assertEqual(len(chain), 1)
        self.assertIs(chain[0].rule.context, chain.context)
        self.assertIs(chain.evaluate({'port': 22, 'source': '10.0.0.1'}), Action.DROP)
        self.assertIs(chain.evaluate({'port': 22, 'source': '10.0.0.2'}), Action.ACCEPT)

    def test_chain_pickle_undefined_default_raises(self):
        chain = pickle.loads(pickle.dumps(self._make_chain()))
        self.assertIs(chain.default_value, errors.UNDEFINED)
        with self.assertRaises(errors.ChainExhaustedError):
            chain.evaluate({'port': 80, 'source': '10.0.0.2'})

    def test_chain_deepcopy_undefined_default_raises(self):
        chain = copy.deepcopy(self._make_chain())
        self.assertIs(chain.default_value, errors.UNDEFINED)
        with self.assertRaises(errors.ChainExhaustedError):
            chain.evaluate({'port': 80, 'source': '10.0.0.2'})

    def test_chain_pickle_preserves_shared_context(self):
        chain = pickle.loads(pickle.dumps(self._make_chain()))
        self.assertIs(chain[0].rule.context, chain.context)
        self.assertIs(chain[1].rule.context, chain.context)
        self.assertEqual(chain.context.symbols, {'port', 'source'})

    def test_chain_pickle_preserves_separate_context(self):
        context = engine.Context(resolver=engine.resolve_attribute)
        rule = engine.Rule('port == 22', context=context)
        chain = engine.Chain([(rule, Action.ACCEPT), (rule, Action.DROP), ('port == 80', Action.DROP)])
        chain2 = pickle.loads(pickle.dumps(chain))
        self.assertIs(chain2[0].rule, chain2[1].rule)
        self.assertIsNot(chain2[0].rule.context, chain2.context)
        self.assertIs(chain2[2].rule.context, chain2.context)
        self.assertIs(chain2.evaluate(_Packet(port=22, source='10.0.0.1')), Action.ACCEPT)

    def test_chain_copy(self):
        chain = self._make_chain(default_value=Action.DROP)
        for chain2 in (copy.copy(chain), copy.deepcopy(chain)):
            with self.subTest(chain=chain2):
                self.assertIsNot(chain2, chain)
                self.assertEqual(len(chain2), 2)
                self.assertIs(chain2.evaluate({'port': 22, 'source': '10.0.0.1'}), Action.ACCEPT)
                self.assertIs(chain2.evaluate({'port': 80, 'source': '10.0.0.2'}), Action.DROP)

    def test_chain_copy_context_sharing(self):
        chain = self._make_chain()
        chain2 = copy.copy(chain)
        self.assertIs(chain2.context, chain.context)
        self.assertIs(chain2[0], chain[0])
        chain2 = copy.deepcopy(chain)
        self.assertIsNot(chain2.context, chain.context)
        self.assertIs(chain2[0].rule.context, chain2.context)
        self.assertIs(chain2[1].rule.context, chain2.context)

    def test_chain_pickle_unpicklable_value_raises(self):
        chain = engine.Chain([('true', lambda: None)])
        with self.assertRaises((AttributeError, pickle.PicklingError)):
            pickle.dumps(chain)

if __name__ == '__main__':
    unittest.main()
