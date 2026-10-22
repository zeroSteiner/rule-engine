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

import copy
import pickle
import random
import string
import traceback
import unittest

import rule_engine.errors as errors
import rule_engine.types as types

__all__ = ('ChainExhaustedErrorTests', 'ResolutionErrorTests', 'UndefinedSentinelTests')

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

    def _type_spellings(self):
        DataType = types.DataType
        person = DataType.OBJECT('Person', attributes={
            'name': DataType.STRING,
            'parent': DataType.NULLABLE(DataType.OBJECT.self),
            'children': DataType.ARRAY(DataType.OBJECT.self)
        })
        big = DataType.OBJECT('Big', attributes={'attribute_' + str(index): DataType.STRING for index in range(500)})
        return (
            (DataType.STRING, 'STRING'),
            (DataType.NULL, 'NULL'),
            (DataType.UNDEFINED, 'UNDEFINED'),
            (DataType.ARRAY, 'ARRAY'),
            (DataType.ARRAY(DataType.STRING), 'ARRAY(STRING)'),
            (DataType.ARRAY(DataType.NULLABLE(DataType.STRING)), 'ARRAY(NULLABLE(STRING))'),
            (DataType.ARRAY(DataType.ARRAY(DataType.FLOAT)), 'ARRAY(ARRAY(FLOAT))'),
            (DataType.SET(DataType.FLOAT), 'SET(FLOAT)'),
            (DataType.MAPPING, 'MAPPING'),
            (DataType.MAPPING(DataType.STRING), 'MAPPING(STRING)'),
            (DataType.MAPPING(DataType.UNDEFINED, DataType.FLOAT), 'MAPPING(UNDEFINED, FLOAT)'),
            (DataType.MAPPING(DataType.STRING, DataType.FLOAT), 'MAPPING(STRING, FLOAT)'),
            (
                DataType.MAPPING(DataType.ARRAY(DataType.STRING), DataType.SET(DataType.FLOAT)),
                'MAPPING(ARRAY(STRING), SET(FLOAT))'
            ),
            (DataType.NULLABLE, 'NULLABLE'),
            (DataType.NULLABLE(DataType.ARRAY(DataType.STRING)), 'NULLABLE(ARRAY(STRING))'),
            (
                DataType.FUNCTION(
                    'split',
                    return_type=DataType.ARRAY(DataType.STRING),
                    argument_types=(DataType.STRING,)
                ),
                'FUNCTION'
            ),
            (DataType.OBJECT, 'OBJECT'),
            (person, 'Person'),
            (big, 'Big'),
            (DataType.ARRAY(person), 'ARRAY(Person)'),
            (DataType.MAPPING(DataType.STRING, DataType.NULLABLE(big)), 'MAPPING(STRING, NULLABLE(Big))')
        )

    def test_attribute_type_error_message(self):
        FLOAT = types.DataType.FLOAT
        message = "attribute 'name' resolved to incorrect datatype (is: {}, expected: {})"
        for data_type, spelling in self._type_spellings():
            with self.subTest(spelling=spelling):
                error = errors.AttributeTypeError('name', 'object', is_value=1, is_type=FLOAT, expected_type=data_type)
                self.assertEqual(error.message, message.format('FLOAT', spelling))
                self.assertIs(error.expected_type, data_type)
                error = errors.AttributeTypeError('name', 'object', is_value=1, is_type=data_type, expected_type=FLOAT)
                self.assertEqual(error.message, message.format(spelling, 'FLOAT'))
                self.assertIs(error.is_type, data_type)

    def test_symbol_type_error_message(self):
        FLOAT = types.DataType.FLOAT
        message = "symbol 'name' resolved to incorrect datatype (is: {}, expected: {})"
        for data_type, spelling in self._type_spellings():
            with self.subTest(spelling=spelling):
                error = errors.SymbolTypeError('name', is_value=1, is_type=FLOAT, expected_type=data_type)
                self.assertEqual(error.message, message.format('FLOAT', spelling))
                self.assertIs(error.expected_type, data_type)
                error = errors.SymbolTypeError('name', is_value=1, is_type=data_type, expected_type=FLOAT)
                self.assertEqual(error.message, message.format(spelling, 'FLOAT'))
                self.assertIs(error.is_type, data_type)

class ChainExhaustedErrorTests(unittest.TestCase):
    def test_chain_exhausted_error_attributes(self):
        thing = {'port': 80}
        error = errors.ChainExhaustedError(thing)
        self.assertIsInstance(error, errors.EvaluationError)
        self.assertIsInstance(error, errors.EngineError)
        self.assertIs(error.thing, thing)
        self.assertEqual(error.message, 'no rule in the chain matched and no default value is set')

    def test_chain_exhausted_error_default_thing(self):
        self.assertIs(errors.ChainExhaustedError().thing, errors.UNDEFINED)

    def test_chain_exhausted_error_does_not_leak_thing(self):
        secret = ''.join(random.choice(string.ascii_letters) for _ in range(20))
        error = errors.ChainExhaustedError({'password': secret})
        self.assertEqual(str(error), error.message)
        self.assertEqual(error.args, (error.message,))
        self.assertNotIn(secret, str(error))
        self.assertNotIn(secret, repr(error))
        self.assertNotIn(secret, ''.join(traceback.format_exception_only(type(error), error)))

    def test_chain_exhausted_error_repr(self):
        self.assertEqual(
            repr(errors.ChainExhaustedError({})),
            "<ChainExhaustedError message='no rule in the chain matched and no default value is set' >"
        )

    def test_chain_exhausted_error_pickle(self):
        for error in (errors.ChainExhaustedError({'port': 80}), errors.ChainExhaustedError(thing={'port': 80})):
            with self.subTest(error=error):
                error2 = pickle.loads(pickle.dumps(error))
                self.assertIsInstance(error2, errors.ChainExhaustedError)
                self.assertEqual(error2.thing, {'port': 80})
                self.assertEqual(error2.message, error.message)
                self.assertEqual(error2.args, (error.message,))
        error = pickle.loads(pickle.dumps(errors.ChainExhaustedError()))
        self.assertIs(error.thing, errors.UNDEFINED)

class UndefinedSentinelTests(unittest.TestCase):
    def test_undefined_has_a_repr(self):
        self.assertEqual(repr(errors.UNDEFINED), 'UNDEFINED')

    def test_undefined_is_a_sentinel(self):
        self.assertIsNotNone(errors.UNDEFINED)
        self.assertIs(errors.UNDEFINED, errors.UNDEFINED)

    def test_undefined_is_falsy(self):
        self.assertFalse(errors.UNDEFINED)

    def test_undefined_pickle_preserves_identity(self):
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.subTest(protocol=protocol):
                self.assertIs(pickle.loads(pickle.dumps(errors.UNDEFINED, protocol=protocol)), errors.UNDEFINED)

    def test_undefined_copy_preserves_identity(self):
        self.assertIs(copy.copy(errors.UNDEFINED), errors.UNDEFINED)
        self.assertIs(copy.deepcopy(errors.UNDEFINED), errors.UNDEFINED)
        self.assertIs(copy.deepcopy([errors.UNDEFINED])[0], errors.UNDEFINED)

    def test_undefined_pickle_in_exception(self):
        symbol_error = pickle.loads(pickle.dumps(errors.SymbolResolutionError('doesnotexist')))
        self.assertEqual(symbol_error.symbol_name, 'doesnotexist')
        self.assertIs(symbol_error.thing, errors.UNDEFINED)

if __name__ == '__main__':
    unittest.main()