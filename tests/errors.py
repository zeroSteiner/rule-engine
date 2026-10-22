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
import copyreg
import pickle
import random
import re
import string
import traceback
import unittest

import rule_engine.errors as errors
import rule_engine.types as types

__all__ = ('ChainExhaustedErrorTests', 'ResolutionErrorTests', 'UndefinedSentinelTests')

# subclasses like other packages may define, at the module level so they can be pickled
class _SlotsEngineError(errors.EngineError):
    __slots__ = ('code',)
    def __init__(self, code):
        super(_SlotsEngineError, self).__init__('code ' + str(code))
        self.code = code

class _SlotsSymbolTypeError(errors.SymbolTypeError):
    __slots__ = ('code',)
    def __init__(self, symbol_name, *, code, **kwargs):
        super(_SlotsSymbolTypeError, self).__init__(symbol_name, **kwargs)
        self.code = code

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

    def _engine_errors(self):
        # an error of every class, created with the arguments the package raises it with, and the arguments it keeps
        DataType = types.DataType
        person = DataType.OBJECT('Person', attributes={'name': DataType.STRING})
        return (
            (errors.EngineError('message'), ('message',)),
            (errors.EngineError(message='message'), ()),
            (errors.EvaluationError('message'), ('message',)),
            (errors.SyntaxError('message'), ('message',)),
            (errors.BytesSyntaxError('message', 'value'), ('message', 'value')),
            (errors.StringSyntaxError('message', 'value'), ('message', 'value')),
            (errors.DatetimeSyntaxError('message', 'value'), ('message', 'value')),
            (errors.FloatSyntaxError('message', 'value'), ('message', 'value')),
            (errors.TimedeltaSyntaxError('message', 'value'), ('message', 'value')),
            (errors.RegexSyntaxError('message', error=re.error('missing )'), value='('), ('message',)),
            (errors.RuleSyntaxError('message', None), ('message', None)),
            (
                errors.AttributeResolutionError('name', {'object': 1}, thing={'thing': 1}, suggestion='nam'),
                ('name', {'object': 1})
            ),
            (errors.ObjectAttributeError('name', person, suggestion='nam'), ('name', person)),
            (
                errors.AttributeTypeError(
                    'name',
                    {'object': 1},
                    is_value=1,
                    is_type=DataType.FLOAT,
                    expected_type=DataType.STRING
                ),
                ('name', {'object': 1})
            ),
            (errors.LookupError({'container': 1}, 'item'), ({'container': 1}, 'item')),
            (
                errors.SymbolResolutionError('name', symbol_scope='scope', thing={'thing': 1}, suggestion='nam'),
                ('name',)
            ),
            (
                errors.SymbolTypeError('name', is_value=1, is_type=DataType.FLOAT, expected_type=DataType.STRING),
                ('name',)
            ),
            (errors.FunctionCallError('message', error=ValueError('error'), function_name='function'), ('message',)),
            (errors.ArithmeticError('message'), ('message',)),
            (errors.ChainExhaustedError({'thing': 1}), ('no rule in the chain matched and no default value is set',))
        )

    def _error_state(self, error):
        # exceptions in the arguments and attributes compare by identity, so compare the representations
        attributes = dict(vars(error))
        for name in copyreg._slotnames(type(error)):
            attributes[name] = getattr(error, name)
        attributes = sorted((key, repr(value)) for key, value in attributes.items())
        return (type(error), repr(error.args), str(error), attributes)

    def test_engine_error_str_is_the_message(self):
        def subclasses(cls):
            for subclass in cls.__subclasses__():
                yield subclass
                yield from subclasses(subclass)
        classes = set(cls for cls in subclasses(errors.EngineError) if cls.__module__ == errors.__name__)
        self.assertEqual(classes - set(type(error) for error, _ in self._engine_errors()), set())

        for error, args in self._engine_errors():
            with self.subTest(error=type(error).__name__, args=args):
                self.assertEqual(str(error), error.message)
                self.assertEqual(
                    traceback.format_exception_only(type(error), error),
                    ['rule_engine.errors.{}: {}\n'.format(type(error).__name__, error.message)]
                )
                self.assertEqual(error.args, args)

        class CustomError(errors.EngineError):
            def __init__(self, value):
                # doesn't call EngineError.__init__ so there is no message
                self.value = value
        self.assertEqual(str(CustomError('value')), 'value')

    def _subclass_errors(self):
        DataType = types.DataType
        return (
            _SlotsEngineError(1),
            _SlotsSymbolTypeError('name', code=1, is_value=1, is_type=DataType.FLOAT, expected_type=DataType.STRING)
        )

    def test_engine_error_reduce(self):
        # errors whose arguments fit __init__ are reduced the default way, which calls it to create them again
        DataType = types.DataType
        for error in (
                errors.RegexSyntaxError('message', re.error('missing )'), '('),
                errors.AttributeTypeError('name', 'object', 1, DataType.FLOAT, DataType.STRING),
                errors.SymbolTypeError('name', 1, DataType.FLOAT, DataType.STRING),
                _SlotsEngineError(1)
            ):
            with self.subTest(error=type(error).__name__):
                self.assertEqual(error.__reduce__(), BaseException.__reduce__(error))
        # the others are created without calling __init__
        for error in (
                errors.RegexSyntaxError('message', error=re.error('missing )'), value='('),
                errors.SymbolTypeError('name', is_value=1, is_type=DataType.FLOAT, expected_type=DataType.STRING),
                self._subclass_errors()[1]
            ):
            with self.subTest(error=type(error).__name__):
                self.assertIs(error.__reduce__()[0], copyreg.__newobj__)

    def test_engine_error_pickle(self):
        # protocols 0 and 1 can't pickle the data types in some of the attributes
        for error in [error for error, _ in self._engine_errors()] + list(self._subclass_errors()):
            for protocol in range(2, pickle.HIGHEST_PROTOCOL + 1):
                with self.subTest(error=type(error).__name__, protocol=protocol):
                    error2 = pickle.loads(pickle.dumps(error, protocol=protocol))
                    self.assertEqual(self._error_state(error2), self._error_state(error))

    def test_engine_error_copy(self):
        for error in [error for error, _ in self._engine_errors()] + list(self._subclass_errors()):
            for copier in (copy.copy, copy.deepcopy):
                with self.subTest(error=type(error).__name__, copier=copier.__name__):
                    self.assertEqual(self._error_state(copier(error)), self._error_state(error))

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