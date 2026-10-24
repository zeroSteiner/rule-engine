#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/engine.py
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
import copy
import dataclasses
import datetime
import decimal
import os
import pickle
import re
import sys
import unittest
from types import GeneratorType
import warnings

import rule_engine.ast as ast
import rule_engine.builtins as builtins
import rule_engine.engine as engine
import rule_engine.types as types
import rule_engine.errors as errors

import dateutil.tz

try:
    import graphviz
except ImportError:
    has_graphviz = False
else:
    has_graphviz = True

class ContextTests(unittest.TestCase):
    def test_context_default_timezone(self):
        context = engine.Context(default_timezone='Local')
        self.assertEqual(context.default_timezone, dateutil.tz.tzlocal())

        context = engine.Context(default_timezone='UTC')
        self.assertEqual(context.default_timezone, dateutil.tz.tzutc())

    def test_context_default_timezone_errors(self):
        with self.assertRaises(ValueError):
            engine.Context(default_timezone='doesnotexist')
        with self.assertRaises(TypeError):
            engine.Context(default_timezone=600)

    def test_context_type_resolver_mapping(self):
        context = engine.Context(type_resolver={'name': types.DataType.STRING})
        self.assertEqual(context.resolve_type('name'), types.DataType.STRING)

    def test_context_int_max_digits(self):
        self.assertIsNone(engine.Context().int_max_digits)
        for int_max_digits in (0, 1, 20, 4300):
            self.assertEqual(engine.Context(int_max_digits=int_max_digits).int_max_digits, int_max_digits)

    def test_context_int_max_digits_errors(self):
        for int_max_digits in ('20', 20.0, True):
            with self.subTest(int_max_digits=int_max_digits), self.assertRaises(TypeError):
                engine.Context(int_max_digits=int_max_digits)
        with self.assertRaises(ValueError):
            engine.Context(int_max_digits=-1)

    def test_context_mapping_attribute_lookup_default(self):
        context = engine.Context()
        self.assertTrue(context.mapping_attribute_lookup)

    def test_context_mapping_attribute_lookup_disabled(self):
        context = engine.Context(mapping_attribute_lookup=False)
        self.assertFalse(context.mapping_attribute_lookup)

    def test_context_mapping_attribute_lookup_parse_time_error(self):
        context = engine.Context(
                mapping_attribute_lookup=False,
                type_resolver={'facts': types.DataType.MAPPING(types.DataType.STRING, value_type=types.DataType.STRING)},
        )
        with self.assertRaisesRegex(errors.EvaluationError, r'attribute access on a MAPPING is disabled'):
            engine.Rule('facts.abc == "xyz"', context=context)

    def test_context_mapping_attribute_lookup_parse_time_error_mentions_migration(self):
        context = engine.Context(
                mapping_attribute_lookup=False,
                type_resolver={'facts': types.DataType.MAPPING(types.DataType.STRING, value_type=types.DataType.STRING)},
        )
        try:
            engine.Rule('facts.abc == "xyz"', context=context)
        except errors.EvaluationError as error:
            self.assertIn("mapping['abc']", error.message)
            self.assertIn('v6.0', error.message)
        else:
            self.fail('EvaluationError was not raised')

    def test_context_mapping_attribute_lookup_disabled_bracket_still_works(self):
        context = engine.Context(
                mapping_attribute_lookup=False,
                type_resolver={'facts': types.DataType.MAPPING(types.DataType.STRING, value_type=types.DataType.STRING)},
        )
        rule = engine.Rule('facts["abc"] == "xyz"', context=context)
        self.assertTrue(rule.matches({'facts': {'abc': 'xyz'}}))

    def test_context_mapping_attribute_lookup_disabled_runtime_mapping(self):
        # result_type is UNDEFINED at parse time, but the object is a mapping at runtime — the fallback is refused
        context = engine.Context(mapping_attribute_lookup=False)
        rule = engine.Rule('facts.abc', context=context)
        with self.assertRaises(errors.AttributeResolutionError):
            rule.evaluate({'facts': {'abc': 'xyz'}})

    def test_context_mapping_attribute_lookup_warning_fires_once(self):
        context = engine.Context()
        rule = engine.Rule('facts.abc == "xyz"', context=context)
        thing = {'facts': {'abc': 'xyz'}}
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always', category=errors.MappingAttributeLookupDeprecation)
            rule.matches(thing)
            rule.matches(thing)
            rule.matches(thing)
        dep = [w for w in captured if issubclass(w.category, errors.MappingAttributeLookupDeprecation)]
        self.assertEqual(len(dep), 1)

    def test_context_mapping_attribute_lookup_warning_is_per_context(self):
        thing = {'facts': {'abc': 'xyz'}}
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always', category=errors.MappingAttributeLookupDeprecation)
            rule_a = engine.Rule('facts.abc == "xyz"', context=engine.Context())
            rule_a.matches(thing)
            rule_b = engine.Rule('facts.abc == "xyz"', context=engine.Context())
            rule_b.matches(thing)
        dep = [w for w in captured if issubclass(w.category, errors.MappingAttributeLookupDeprecation)]
        self.assertEqual(len(dep), 2)

    def test_context_mapping_attribute_lookup_warning_message_content(self):
        context = engine.Context()
        rule = engine.Rule('facts.abc == "xyz"', context=context)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always', category=errors.MappingAttributeLookupDeprecation)
            rule.matches({'facts': {'abc': 'xyz'}})
        self.assertEqual(len(captured), 1)
        message = str(captured[0].message)
        self.assertIn("'abc'", message)
        self.assertIn("mapping['abc']", message)
        self.assertIn('v6.0', message)
        self.assertIn('MappingAttributeLookupDeprecation', message)

    def test_context_mapping_attribute_lookup_warning_concurrent(self):
        # spawn two threads both exercising the fallback against a shared Context; the warning should fire exactly once
        import threading
        context = engine.Context()
        rule = engine.Rule('facts.abc == "xyz"', context=context)
        thing = {'facts': {'abc': 'xyz'}}
        barrier = threading.Barrier(2)
        def worker():
            barrier.wait()
            rule.matches(thing)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always', category=errors.MappingAttributeLookupDeprecation)
            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
        dep = [w for w in captured if issubclass(w.category, errors.MappingAttributeLookupDeprecation)]
        self.assertEqual(len(dep), 1)

@dataclasses.dataclass
class _TestPerson:
    name: str
    rank: str = 'Padawan'
    manager: 'typing.Any' = None


class ObjectTypeTests(unittest.TestCase):
    def _person_type(self, **kwargs):
        return types.DataType.OBJECT('Person', attributes={
                'name': types.DataType.STRING,
                'rank': types.DataType.STRING,
                'manager': types.DataType.OBJECT.reference('Person'),
        }, **kwargs)

    def _context(self, **extra_types):
        type_map = {'employee': self._person_type(), 'Person': self._person_type()}
        type_map.update(extra_types)
        return engine.Context(type_resolver=type_map)

    def test_object_rule_happy_path_dataclass(self):
        rule = engine.Rule('employee.name == "Luke"', context=self._context())
        self.assertTrue(rule.matches({'employee': _TestPerson(name='Luke')}))
        self.assertFalse(rule.matches({'employee': _TestPerson(name='Vader')}))

    def test_object_rule_chained_self_reference(self):
        luke = _TestPerson(name='Luke')
        yoda = _TestPerson(name='Yoda', manager=luke)
        obi = _TestPerson(name='Obi-Wan', manager=yoda)
        rule = engine.Rule('employee.manager.manager.name == "Luke"', context=self._context())
        self.assertTrue(rule.matches({'employee': obi}))

    def test_object_rule_unknown_attribute_parse_error(self):
        try:
            engine.Rule('employee.unknown_attr', context=self._context())
        except errors.ObjectAttributeError as error:
            self.assertEqual(error.attribute_name, 'unknown_attr')
            self.assertIn(error.suggestion, {'name', 'rank', 'manager'})
        else:
            self.fail('ObjectAttributeError was not raised')

    def test_object_rule_item_access_rejected(self):
        with self.assertRaisesRegex(errors.EvaluationError, 'item access on OBJECT'):
            engine.Rule('employee["name"]', context=self._context())

    def test_object_rule_containment_rejected(self):
        with self.assertRaisesRegex(errors.EvaluationError, 'containment check on OBJECT'):
            engine.Rule('"name" in employee', context=self._context())

    def test_object_rule_cross_type_mutual_reference(self):
        Person = types.DataType.OBJECT('Person', attributes={
                'name': types.DataType.STRING,
                'employer': types.DataType.OBJECT.reference('Company'),
        })
        Company = types.DataType.OBJECT('Company', attributes={
                'name': types.DataType.STRING,
                'ceo': types.DataType.OBJECT.reference('Person'),
        })
        context = engine.Context(type_resolver={'employee': Person, 'Person': Person, 'Company': Company})
        rule = engine.Rule('employee.employer.ceo.name == "Palpatine"', context=context)

        @dataclasses.dataclass
        class _Person:
            name: str
            employer: 'typing.Any' = None

        @dataclasses.dataclass
        class _Company:
            name: str
            ceo: 'typing.Any' = None

        sheev = _Person(name='Palpatine')
        empire = _Company(name='Empire', ceo=sheev)
        vader = _Person(name='Vader', employer=empire)
        self.assertTrue(rule.matches({'employee': vader}))

    def test_object_rule_unresolved_cross_reference(self):
        Person = types.DataType.OBJECT('Person', attributes={
                'employer': types.DataType.OBJECT.reference('Company'),
                'name': types.DataType.STRING,
        })
        context = engine.Context(type_resolver={'employee': Person, 'Person': Person})
        with self.assertRaisesRegex(errors.EvaluationError, "unresolved object reference: 'Company'"):
            engine.Rule('employee.employer.name', context=context)

    def test_object_rule_reference_resolves_to_non_object(self):
        Person = types.DataType.OBJECT('Person', attributes={
                'employer': types.DataType.OBJECT.reference('Company'),
        })
        context = engine.Context(type_resolver={
                'employee': Person,
                'Person': Person,
                'Company': types.DataType.STRING,
        })
        with self.assertRaisesRegex(errors.EvaluationError, "does not resolve to an OBJECT"):
            engine.Rule('employee.employer', context=context)

    def test_object_rule_reference_name_mismatch(self):
        Person = types.DataType.OBJECT('Person', attributes={
                'employer': types.DataType.OBJECT.reference('Company'),
        })
        Corporation = types.DataType.OBJECT('Corporation', attributes={'name': types.DataType.STRING})
        context = engine.Context(type_resolver={
                'employee': Person,
                'Person': Person,
                'Company': Corporation,
        })
        with self.assertRaisesRegex(errors.EvaluationError, "mismatched name"):
            engine.Rule('employee.employer', context=context)

    def test_object_rule_array_of_objects(self):
        Person = self._person_type()
        context = engine.Context(type_resolver={
                'crew': types.DataType.ARRAY(Person),
                'Person': Person,
        })
        rule = engine.Rule('crew[0].name == "Han"', context=context)
        self.assertTrue(rule.matches({'crew': [_TestPerson(name='Han'), _TestPerson(name='Chewie')]}))

    def test_object_rule_array_of_reference(self):
        Person = self._person_type()
        context = engine.Context(type_resolver={
                'crew': types.DataType.ARRAY(types.DataType.OBJECT.reference('Person')),
                'Person': Person,
        })
        rule = engine.Rule('crew[0].name == "Han"', context=context)
        self.assertTrue(rule.matches({'crew': [_TestPerson(name='Han'), _TestPerson(name='Chewie')]}))

    def test_object_rule_mapping_of_objects(self):
        Person = self._person_type()
        context = engine.Context(type_resolver={
                'roster': types.DataType.MAPPING(types.DataType.STRING, value_type=Person),
                'Person': Person,
        })
        rule = engine.Rule('roster["alice"].name == "Alice"', context=context)
        self.assertTrue(rule.matches({'roster': {'alice': _TestPerson(name='Alice')}}))

    def test_object_rule_mapping_of_reference(self):
        Person = self._person_type()
        context = engine.Context(type_resolver={
                'roster': types.DataType.MAPPING(types.DataType.STRING, value_type=types.DataType.OBJECT.reference('Person')),
                'Person': Person,
        })
        rule = engine.Rule('roster["alice"].name == "Alice"', context=context)
        self.assertTrue(rule.matches({'roster': {'alice': _TestPerson(name='Alice')}}))

    def test_object_rule_custom_accessor(self):
        Person = types.DataType.OBJECT(
                'Person',
                attributes={'name': types.DataType.STRING},
                accessor=lambda obj, name: obj[name]
        )
        context = engine.Context(type_resolver={'employee': Person, 'Person': Person})
        rule = engine.Rule('employee.name == "Leia"', context=context)
        self.assertTrue(rule.matches({'employee': {'name': 'Leia'}}))

    def test_object_rule_accessor_missing_uses_default_value(self):
        Person = types.DataType.OBJECT('Person', attributes={'name': types.DataType.STRING})
        context = engine.Context(
                type_resolver={'employee': Person, 'Person': Person},
                default_value=None,
        )
        rule = engine.Rule('employee.name', context=context)
        class _Blank:
            pass
        self.assertIsNone(rule.evaluate({'employee': _Blank()}))

    def test_object_rule_accessor_missing_raises(self):
        Person = types.DataType.OBJECT('Person', attributes={'name': types.DataType.STRING})
        context = engine.Context(type_resolver={'employee': Person, 'Person': Person})
        rule = engine.Rule('employee.name', context=context)
        class _Blank:
            pass
        with self.assertRaises(errors.ObjectAttributeError):
            rule.evaluate({'employee': _Blank()})

    def test_object_rule_accessor_propagates_other_errors(self):
        def angry_accessor(obj, name):
            raise RuntimeError('boom')
        Person = types.DataType.OBJECT('Person', attributes={'name': types.DataType.STRING}, accessor=angry_accessor)
        context = engine.Context(type_resolver={'employee': Person, 'Person': Person})
        rule = engine.Rule('employee.name', context=context)
        with self.assertRaises(RuntimeError):
            rule.evaluate({'employee': _TestPerson(name='Luke')})

    def test_object_rule_equality(self):
        rule = engine.Rule('employee == other', context=engine.Context(type_resolver={
                'employee': self._person_type(),
                'other': self._person_type(),
                'Person': self._person_type(),
        }))
        luke = _TestPerson(name='Luke')
        self.assertTrue(rule.evaluate({'employee': luke, 'other': luke}))
        self.assertFalse(rule.evaluate({'employee': luke, 'other': _TestPerson(name='Vader')}))

    def test_object_rule_equality_with_null(self):
        rule = engine.Rule('employee == null', context=self._context())
        # note: in Python, None compared to a dataclass instance uses type()-mismatch and returns False
        self.assertFalse(rule.matches({'employee': _TestPerson(name='Luke')}))

    def test_object_rule_cross_schema_comparison_returns_false(self):
        Hero = types.DataType.OBJECT('Hero', attributes={'name': types.DataType.STRING})
        context = engine.Context(type_resolver={
                'employee': self._person_type(),
                'villain': Hero,
                'Person': self._person_type(),
        })
        rule = engine.Rule('employee == villain', context=context)
        self.assertFalse(rule.evaluate({
                'employee': _TestPerson(name='Luke'),
                'villain': _TestPerson(name='Vader'),
        }))

    def test_object_rule_comprehension_over_array_of_reference(self):
        Person = self._person_type()
        context = engine.Context(type_resolver={
                'crew': types.DataType.ARRAY(types.DataType.OBJECT.reference('Person')),
                'Person': Person,
        })
        rule = engine.Rule('[m for m in crew if m.name == "Han"]', context=context)
        result = rule.evaluate({'crew': [_TestPerson(name='Han'), _TestPerson(name='Chewie')]})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'Han')

    def test_object_rule_symbols_tracked(self):
        context = self._context()
        engine.Rule('employee.name == "Luke"', context=context)
        self.assertIn('employee', context.symbols)


class EngineTests(unittest.TestCase):
    def test_engine_resolve_attribute(self):
        thing = collections.namedtuple('Person', ('name',))(name='alice')
        self.assertEqual(engine.resolve_attribute(thing, 'name'), thing.name)
        with self.assertRaises(errors.SymbolResolutionError):
            engine.resolve_attribute(thing, 'email')

    def test_engine_resolve_attribute_with_defaults(self):
        thing = collections.namedtuple('Person', ('name',))(name='alice')
        context = engine.Context(resolver=engine.resolve_attribute, default_value=None)
        self.assertEqual(engine.Rule('name', context=context).evaluate(thing), thing.name)
        self.assertIsNone(engine.Rule('name.first', context=context).evaluate(thing))
        self.assertIsNone(engine.Rule('address', context=context).evaluate(thing))
        self.assertIsNone(engine.Rule('address.city', context=context).evaluate(thing))

    def test_engine_resolve_item(self):
        thing = {'name': 'Alice'}
        self.assertEqual(engine.resolve_item(thing, 'name'), thing['name'])
        with self.assertRaises(errors.SymbolResolutionError):
            engine.resolve_item(thing, 'email')

    def test_engine_resolve_item_with_defaults(self):
        thing = {'name': 'Alice'}
        context = engine.Context(resolver=engine.resolve_item, default_value=None)
        self.assertEqual(engine.Rule('name', context=context).evaluate(thing), thing['name'])
        self.assertIsNone(engine.Rule('name.first', context=context).evaluate(thing))
        self.assertIsNone(engine.Rule('address', context=context).evaluate(thing))
        self.assertIsNone(engine.Rule('address.city', context=context).evaluate(thing))

    def test_engine_type_resolver_from_dict(self):
        type_resolver = engine.type_resolver_from_dict({
                'string': types.DataType.STRING,
                'float': types.DataType.FLOAT
        })
        self.assertTrue(callable(type_resolver))
        self.assertEqual(type_resolver('string'), types.DataType.STRING)
        self.assertEqual(type_resolver('float'), types.DataType.FLOAT)
        with self.assertRaises(errors.SymbolResolutionError):
            type_resolver('doesnotexist')

    def test_engine_type_resolver_from_dataclass(self):
        type_resolver = engine.type_resolver_from_dataclass(_ResolverFlatHero)
        self.assertTrue(callable(type_resolver))
        self.assertIs(type_resolver('name'), types.DataType.STRING)
        self.assertIs(type_resolver('age'), types.DataType.FLOAT)
        with self.assertRaises(errors.SymbolResolutionError):
            type_resolver('doesnotexist')

    def test_engine_type_resolver_from_dataclass_evaluates_rule(self):
        context = engine.Context(
                resolver=engine.resolve_attribute,
                type_resolver=engine.type_resolver_from_dataclass(_ResolverFlatHero)
        )
        hero = _ResolverFlatHero(name='Batman', age=85)
        self.assertTrue(engine.Rule('name == "Batman" and age > 50', context=context).matches(hero))
        self.assertFalse(engine.Rule('name == "Joker"', context=context).matches(hero))

    def test_engine_type_resolver_from_dataclass_mutual_recursion(self):
        type_resolver = engine.type_resolver_from_dataclass(_ResolverPerson)
        # both types must be reachable so the cross-reference inside Company resolves at parse time
        person = type_resolver('_ResolverPerson')
        company = type_resolver('_ResolverCompany')
        self.assertIsInstance(person, types._ObjectDataTypeDef)
        self.assertIsInstance(company, types._ObjectDataTypeDef)

        context = engine.Context(resolver=engine.resolve_attribute, type_resolver=type_resolver)
        rule = engine.Rule('employer.ceo.name == "Alice"', context=context)
        alice = _ResolverPerson(name='Alice', employer=None)
        acme = _ResolverCompany(name='ACME', ceo=alice)
        alice.employer = acme
        self.assertTrue(rule.matches(alice))

    def test_engine_type_resolver_from_dataclass_rejects_non_dataclass(self):
        class NotADataclass:
            name: str

        with self.assertRaisesRegex(TypeError, r'^type_resolver_from_dataclass argument 1 must be a dataclass'):
            engine.type_resolver_from_dataclass(NotADataclass)

    def test_engine_type_resolver_from_dataclass_non_strict(self):
        import uuid
        @dataclasses.dataclass
        class HeroWithId:
            name: str
            identifier: uuid.UUID

        type_resolver = engine.type_resolver_from_dataclass(HeroWithId, strict=False)
        self.assertIs(type_resolver('name'), types.DataType.STRING)
        self.assertIs(type_resolver('identifier'), types.DataType.UNDEFINED)

    def test_engine_type_resolver_from_dataclass_preserves_nullable(self):
        type_resolver = engine.type_resolver_from_dataclass(_ResolverNullableHero)
        self.assertEqual(type_resolver('name'), types.DataType.NULLABLE(types.DataType.STRING))
        self.assertIs(type_resolver('age'), types.DataType.FLOAT)

    def test_engine_type_resolver_from_dataclass_nullable_evaluates_rule(self):
        context = engine.Context(
                resolver=engine.resolve_attribute,
                type_resolver=engine.type_resolver_from_dataclass(_ResolverNullableHero)
        )
        rule = engine.Rule('name == "Batman"', context=context)
        self.assertTrue(rule.matches(_ResolverNullableHero(name='Batman', age=85)))
        self.assertFalse(rule.matches(_ResolverNullableHero(name=None, age=85)))

    def test_engine_type_resolver_from_dataclass_registers_nullable_nested_object(self):
        type_resolver = engine.type_resolver_from_dataclass(_ResolverNullableCompany)
        ceo = type_resolver('ceo')
        self.assertIsInstance(ceo, types._NullableDataTypeDef)
        self.assertIsInstance(ceo.inner_type, types._ObjectDataTypeDef)
        # the Person OBJECT nested behind the NULLABLE wrapper is registered so cross-references resolve
        self.assertIsInstance(type_resolver('_ResolverPerson'), types._ObjectDataTypeDef)

@dataclasses.dataclass
class _ResolverFlatHero:
    name: str
    age: int

@dataclasses.dataclass
class _ResolverPerson:
    name: str
    employer: '_ResolverCompany'

@dataclasses.dataclass
class _ResolverCompany:
    name: str
    ceo: _ResolverPerson

@dataclasses.dataclass
class _ResolverNullableHero:
    name: str | None
    age: int

@dataclasses.dataclass
class _ResolverNullableCompany:
    name: str
    ceo: _ResolverPerson | None = None

class EngineRuleTests(unittest.TestCase):
    rule_text = 'first_name == "Luke" and email =~ ".*@rebels.org$"'
    true_item = {'first_name': 'Luke', 'last_name': 'Skywalker', 'email': 'luke@rebels.org'}
    false_item = {'first_name': 'Darth', 'last_name': 'Vader', 'email': 'dvader@empire.net'}
    def test_engine_rule_is_valid(self):
        self.assertTrue(engine.Rule.is_valid(self.rule_text))
        self.assertTrue(engine.Rule.is_valid('test == 1'))
        self.assertFalse(engine.Rule.is_valid('test =='))

    def test_engine_rule_raises(self):
        with self.assertRaises(errors.RuleSyntaxError):
            engine.Rule('test ==')

    @unittest.skipUnless(has_graphviz, 'graphviz is unavailable')
    def test_engine_rule_to_graphviz_1(self):
        rule = engine.Rule(self.rule_text)
        digraph = rule.to_graphviz()
        self.assertIsInstance(digraph, graphviz.Digraph)
        self.assertEqual(digraph.comment, self.rule_text)

    @unittest.skipUnless(has_graphviz, 'graphviz is unavailable')
    def test_engine_rule_to_graphviz_2(self):
        rule = engine.Rule('null in [foo.length % [2, 4, 6][s:e][boz] ? (bar > baz) : (bar < -baz)] # comment')
        digraph = rule.to_graphviz()
        self.assertIsInstance(digraph, graphviz.Digraph)

    @unittest.skipUnless(has_graphviz, 'graphviz is unavailable')
    def test_engine_rule_to_graphviz_3(self):
        rule = engine.Rule('[member for member in iterable if member]')
        digraph = rule.to_graphviz()
        self.assertIsInstance(digraph, graphviz.Digraph)

    def test_engine_rule_to_strings(self):
        rule = engine.Rule(self.rule_text)
        self.assertEqual(str(rule), self.rule_text)
        self.assertRegex(repr(rule), "<Rule text='{0}' >".format(re.escape(self.rule_text)))

    def test_engine_rule_matches(self, rule=None):
        rule = rule or engine.Rule(self.rule_text)
        result = rule.matches(self.true_item)
        self.assertIsInstance(result, bool)
        self.assertTrue(result)
        result = rule.matches(self.false_item)
        self.assertIsInstance(result, bool)
        self.assertFalse(result)

    def test_engine_rule_filter(self, rule=None):
        rule = rule or engine.Rule(self.rule_text)
        result = rule.filter([self.true_item, self.false_item])
        self.assertIsInstance(result, GeneratorType)
        result = tuple(result)
        self.assertIn(self.true_item, result)
        self.assertNotIn(self.false_item, result)

    def test_engine_rule_evaluate(self):
        rule = engine.Rule('"string"')
        self.assertEqual(rule.evaluate(None), 'string')

    def test_engine_rule_evaluate_attributes(self):
        # ensure that multiple levels can be evaluated as attributes
        rule = engine.Rule('a.b.c')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=errors.MappingAttributeLookupDeprecation)
            self.assertTrue(rule.evaluate({'a': {'b': {'c': True}}}))

            value = rule.evaluate({'a': {'b': {'c': 1}}})
            self.assertIsInstance(value, decimal.Decimal)
            self.assertEqual(value, 1.0)

            value = rule.evaluate({'a': {'b': {'c': {'d': None}}}})
            self.assertIsInstance(value, dict)
            self.assertIn('d', value)

            with self.assertRaises(errors.AttributeResolutionError):
                rule.evaluate({'a': {}})

    def test_engine_rule_evaluate_any_type_operators(self):
        # ==, !=, and, and or accept values of any type
        context = engine.Context(type_resolver=engine.type_resolver_from_dict({
            'data': types.DataType.BYTES,
            'function': types.DataType.FUNCTION,
            'thing': types.DataType.OBJECT
        }))
        thing = {'data': b'ab', 'function': abs, 'thing': object()}
        for text, value in (
                ('b"ab" == b"ab"', True),
                ('b"ab" != null', True),
                ('data == b"ab"', True),
                ('data != "ab"', True),
                ('data and thing', True),
                ('thing or false', True),
                ('function == $abs', True),
                ('$abs != $abs', False),
                # functions are compared by identity and accessing a method creates a new one
                ('data.decode == data.decode', False)
            ):
            self.assertEqual(engine.Rule(text, context=context).evaluate(thing), value, msg=text)
        # ordering is not supported for bytes
        with self.assertRaises(errors.EvaluationError):
            engine.Rule('b"a" < b"b"')

    def test_engine_rule_string_to_int_leading_zeros(self):
        rule = engine.Rule('zip.to_int >= 2100 and zip.to_int < 2200')
        self.assertTrue(rule.matches({'zip': '02134'}))
        self.assertFalse(rule.matches({'zip': '10001'}))
        self.assertEqual(engine.Rule('zip.to_int').evaluate({'zip': '02134'}), 2134)
        self.assertEqual(engine.Rule('zip.to_flt').evaluate({'zip': '02134'}), 2134)

    def test_engine_rule_parse_float_invalid_prefixed_no_warnings(self):
        rule = engine.Rule('$parse_float(value)')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            with self.assertRaises(errors.FunctionCallError) as raised:
                rule.evaluate({'value': "0x1, '\\.'"})
        self.assertIsInstance(raised.exception.error, errors.FloatSyntaxError)
        self.assertEqual(caught, [])

    def test_engine_rule_debug_parser(self):
        with open(os.devnull, 'w') as file_h:
            original_stderr = sys.stderr
            sys.stderr = file_h
            debug_rule = engine.DebugRule(self.rule_text)
            sys.stderr = original_stderr
        self.test_engine_rule_matches(rule=debug_rule)
        self.test_engine_rule_filter(rule=debug_rule)


class EngineDatetimeRuleTests(unittest.TestCase):
    def test_add_timedeltas(self):
        rule = engine.Rule("t'P4DT2H31S' + t'P1WT45M17S' == t'P1W4DT2H45M48S'")
        self.assertTrue(rule.evaluate({}))

    def test_add_empty_timedelta(self):
        rule = engine.Rule("t'P1DT3S' + t'PT' == t'P1DT3S'")
        self.assertTrue(rule.evaluate({}))

    def test_add_to_today(self):
        rule = engine.Rule("$today + t'PT' == $today")
        self.assertTrue(rule.evaluate({}))

    def test_add_datetime_to_timedelta(self):
        rule = engine.Rule("d'2022-05-23 08:23' + t'PT4H3M2S' == d'2022-05-23 12:26:02'")
        self.assertTrue(rule.evaluate({}))

        rule = engine.Rule("start + t'PT1H' == end")
        self.assertTrue(rule.evaluate({
                "start": datetime.datetime(year=2022, month=2, day=28, hour=23, minute=32, second=56),
                "end": datetime.datetime(year=2022, month=3, day=1, hour=0, minute=32, second=56),
        }))

    def test_subtract_timedeltas(self):
        rule = engine.Rule("t'P4DT2H31S' - t'P1DT45S' == t'P3DT1H59M46S'")
        self.assertTrue(rule.evaluate({}))

        rule = engine.Rule("t'P4DT2H31S' - t'P1WT45M17S' == -t'P2DT22H44M46S'")
        self.assertTrue(rule.evaluate({}))

    def test_subtract_empty_timedelta(self):
        rule = engine.Rule("t'P1DT3S' - t'PT' == t'P1DT3S'")
        self.assertTrue(rule.evaluate({}))

    def test_subtract_from_today(self):
        rule = engine.Rule("$today - t'PT' == $today")
        self.assertTrue(rule.evaluate({}))

    def test_subtract_datetime_from_datetime(self):
        rule = engine.Rule("d'2022-05-23 14:12' - d'2022-05-23 12:15' == t'PT1H57M'")
        self.assertTrue(rule.evaluate({}))

        rule = engine.Rule("end - t'PT1H' == start")
        self.assertTrue(rule.evaluate({
                "start": datetime.datetime(year=2022, month=2, day=28, hour=23, minute=32, second=56),
                "end": datetime.datetime(year=2022, month=3, day=1, hour=0, minute=32, second=56),
        }))

    def test_subtract_timedelta_from_datetime(self):
        rule = engine.Rule("d'2022-06-12' - t'P1D' == d'2022-06-11'")
        self.assertTrue(rule.evaluate({}))

class ContextSerializationTests(unittest.TestCase):
    def test_context_pickle_default(self):
        context = engine.Context()
        context2 = pickle.loads(pickle.dumps(context))
        self.assertEqual(context2.regex_flags, 0)
        self.assertIs(context2.default_value, errors.UNDEFINED)
        self.assertTrue(context2.mapping_attribute_lookup)

    def test_context_pickle_default_raises_symbol_resolution_error(self):
        context = pickle.loads(pickle.dumps(engine.Context()))
        rule = engine.Rule('missing', context=context)
        with self.assertRaises(errors.SymbolResolutionError):
            rule.evaluate({})

    def test_context_pickle_custom_params(self):
        context = engine.Context(
                regex_flags=re.IGNORECASE,
                default_timezone='utc',
                default_value=None,
                mapping_attribute_lookup=False
        )
        context2 = pickle.loads(pickle.dumps(context))
        self.assertEqual(context2.regex_flags, re.IGNORECASE)
        self.assertEqual(context2.default_timezone, dateutil.tz.tzutc())
        self.assertIsNone(context2.default_value)
        self.assertFalse(context2.mapping_attribute_lookup)

    def test_context_pickle_with_type_resolver_dict(self):
        context = engine.Context(type_resolver={'name': types.DataType.STRING})
        context2 = pickle.loads(pickle.dumps(context))
        self.assertEqual(context2.resolve_type('name'), types.DataType.STRING)

    def test_context_pickle_with_named_resolver(self):
        context = engine.Context(resolver=engine.resolve_attribute)
        context2 = pickle.loads(pickle.dumps(context))
        thing = collections.namedtuple('Thing', ('name',))('test')
        self.assertEqual(context2.resolve(thing, 'name'), 'test')

    def test_context_pickle_preserves_symbols(self):
        context = engine.Context()
        engine.Rule('name == "test"', context=context)
        self.assertIn('name', context.symbols)
        context2 = pickle.loads(pickle.dumps(context))
        self.assertEqual(context2.symbols, context.symbols)

    def test_context_pickle_warned_state(self):
        context = engine.Context()
        context._mapping_fallback_warned = True
        context2 = pickle.loads(pickle.dumps(context))
        self.assertTrue(context2._mapping_fallback_warned)

    def test_context_pickle_null_member_warned_state(self):
        context = engine.Context()
        context._null_member_warned.add((None, 'thing'))
        context2 = pickle.loads(pickle.dumps(context))
        self.assertEqual(context2._null_member_warned, {(None, 'thing')})
        # contexts pickled before the state was added warn again
        state = context.__getstate__()
        del state['_null_member_warned']
        context3 = engine.Context.__new__(engine.Context)
        context3.__setstate__(state)
        self.assertEqual(context3._null_member_warned, set())

    def test_context_pickle_builtins_functional(self):
        context = engine.Context()
        context2 = pickle.loads(pickle.dumps(context))
        rule = engine.Rule('$now != null', context=context2)
        self.assertTrue(rule.matches({}))
        result = engine.Rule('$now', context=context2).evaluate({})
        self.assertIsInstance(result, datetime.datetime)

    def test_rule_pickle(self):
        rule = engine.Rule('name == "test"')
        rule2 = pickle.loads(pickle.dumps(rule))
        self.assertTrue(rule2.matches({'name': 'test'}))
        self.assertFalse(rule2.matches({'name': 'other'}))

    def test_rule_pickle_with_type_resolver(self):
        context = engine.Context(type_resolver={'name': types.DataType.STRING})
        rule = engine.Rule('name == "test"', context=context)
        rule2 = pickle.loads(pickle.dumps(rule))
        self.assertTrue(rule2.matches({'name': 'test'}))
        self.assertFalse(rule2.matches({'name': 'other'}))

    def test_rule_pickle_missing_symbol_raises(self):
        rule = pickle.loads(pickle.dumps(engine.Rule('missing')))
        with self.assertRaises(errors.SymbolResolutionError):
            rule.evaluate({})
        context = engine.Context(resolver=engine.resolve_attribute)
        rule = pickle.loads(pickle.dumps(engine.Rule('thing.missing', context=context)))
        outer = collections.namedtuple('Outer', ('thing',))
        inner = collections.namedtuple('Inner', ('name',))
        with self.assertRaises(errors.AttributeResolutionError):
            rule.evaluate(outer(inner('test')))

    def test_rule_pickle_text_preserved(self):
        rule = engine.Rule('name == "test"')
        rule2 = pickle.loads(pickle.dumps(rule))
        self.assertEqual(rule2.text, rule.text)

    def test_context_pickle_int_max_digits(self):
        context = pickle.loads(pickle.dumps(engine.Context(int_max_digits=20)))
        self.assertEqual(context.int_max_digits, 20)
        rule = engine.Rule('value > 0', context=context)
        self.assertTrue(rule.matches({'value': 10 ** 20 - 1}))
        with self.assertRaises(errors.ArithmeticError):
            rule.matches({'value': 10 ** 20})
        with self.assertRaises(errors.ArithmeticError):
            engine.Rule('$parse_float(value) > 0', context=context).matches({'value': hex(10 ** 20)})

    def test_context_unpickle_without_int_max_digits(self):
        # pickles created before 5.1.1 don't include int_max_digits
        state = engine.Context().__getstate__()
        del state['int_max_digits']
        context = engine.Context.__new__(engine.Context)
        context.__setstate__(state)
        self.assertIsNone(context.int_max_digits)
        rule = engine.Rule('value << 2 == 4 and $parse_float("0x10") == 16', context=context)
        self.assertTrue(rule.matches({'value': 1}))

    def test_context_pickle_lambda_resolver_raises(self):
        context = engine.Context(resolver=lambda thing, name: thing[name])
        with self.assertRaises((AttributeError, pickle.PicklingError)):
            pickle.dumps(context)

    def test_context_copy(self):
        context = engine.Context(default_timezone='utc')
        context2 = copy.deepcopy(context)
        self.assertEqual(context2.default_timezone, dateutil.tz.tzutc())
        rule = engine.Rule('name == "test"', context=context2)
        self.assertTrue(rule.matches({'name': 'test'}))

    def test_context_pickle_object_missing_attribute_raises(self):
        person = types.DataType.OBJECT('Person', attributes={'name': types.DataType.STRING})
        context = engine.Context(type_resolver={'person': person})
        for context2 in (pickle.loads(pickle.dumps(context)), copy.deepcopy(context)):
            rule = engine.Rule('person.name == "alice"', context=context2)
            with self.assertRaises(errors.ObjectAttributeError):
                rule.evaluate({'person': object()})

    def test_context_unpickle_normalizes_undefined_copies(self):
        # pickles made before UNDEFINED preserved its identity contain a separate instance of the sentinel class
        stray_undefined = pickle.loads(b'\x80\x02crule_engine.errors\n_UNDEFINED\nq\x00)\x81q\x01.')
        self.assertIsInstance(stray_undefined, type(errors.UNDEFINED))
        self.assertIsNot(stray_undefined, errors.UNDEFINED)
        state = engine.Context().__getstate__()
        state['default_value'] = stray_undefined
        context = engine.Context.__new__(engine.Context)
        context.__setstate__(state)
        self.assertIs(context.default_value, errors.UNDEFINED)
        with self.assertRaises(errors.SymbolResolutionError):
            engine.Rule('missing', context=context).evaluate({})

    def test_context_deepcopy_missing_symbol_raises(self):
        context = copy.deepcopy(engine.Context())
        self.assertIs(context.default_value, errors.UNDEFINED)
        rule = engine.Rule('missing', context=context)
        with self.assertRaises(errors.SymbolResolutionError):
            rule.evaluate({})

class EngineIntMaxDigitsTests(unittest.TestCase):
    def _set_int_max_str_digits(self, int_max_digits):
        if not hasattr(sys, 'set_int_max_str_digits'):
            self.skipTest('sys.set_int_max_str_digits is not available')
        self.addCleanup(sys.set_int_max_str_digits, sys.get_int_max_str_digits())
        sys.set_int_max_str_digits(int_max_digits)

    def test_engine_left_shift_overflow(self):
        # before the fix these raised an OverflowError or a MemoryError instead of an engine error
        for rule_text in ('1 << 1e15 == 0', '1 << 1e308 == 0'):
            with self.subTest(rule_text=rule_text):
                with self.assertRaises(errors.ArithmeticError):
                    engine.Rule(rule_text)
                self.assertFalse(engine.Rule.is_valid(rule_text))

    def test_engine_int_max_digits_large_limit(self):
        # a large limit must not make every left shift slow
        context = engine.Context(int_max_digits=10 ** 6)
        self.assertTrue(engine.Rule('value << 1 == 2', context=context).matches({'value': 1}))
        with self.assertRaises(errors.ArithmeticError):
            engine.Rule('1 << 1e15 == 0', context=context)

    def test_engine_int_max_digits_left_shift(self):
        context = engine.Context(int_max_digits=20)
        # constant expressions are evaluated while the rule is parsed
        with self.assertRaises(errors.ArithmeticError):
            engine.Rule('1 << 67 == 0', context=context)
        rule = engine.Rule('value << 67 == 0', context=context)
        with self.assertRaises(errors.ArithmeticError):
            rule.matches({'value': 1})
        self.assertTrue(engine.Rule('value << 66 > 0', context=context).matches({'value': 1}))

    def test_engine_int_max_digits_symbol(self):
        rule = engine.Rule('value > 0', context=engine.Context(int_max_digits=20))
        self.assertTrue(rule.matches({'value': 10 ** 20 - 1}))
        with self.assertRaisesRegex(errors.ArithmeticError, r'\(20 digits\)'):
            rule.matches({'value': 10 ** 20})

    def test_engine_int_max_digits_function_result(self):
        rule = engine.Rule('function() > 0', context=engine.Context(int_max_digits=20))
        self.assertTrue(rule.matches({'function': lambda: 10 ** 20 - 1}))
        with self.assertRaises(errors.ArithmeticError):
            rule.matches({'function': lambda: 10 ** 20})

    def test_engine_int_max_digits_base_literal(self):
        context = engine.Context(int_max_digits=20)
        with self.assertRaises(errors.ArithmeticError):
            engine.Rule(hex(10 ** 20) + ' > 0', context=context)
        self.assertTrue(engine.Rule(hex(10 ** 20 - 1) + ' > 0', context=context).matches({}))

    def test_engine_int_max_digits_floor(self):
        context = engine.Context(int_max_digits=20)
        with self.assertRaises(errors.ArithmeticError):
            engine.Rule('(1e20).floor > 0', context=context).matches({})
        self.assertTrue(engine.Rule('(1e19).floor > 0', context=context).matches({}))
        # the context's limit is used before converting, not only the interpreter's
        context = engine.Context(int_max_digits=0)
        for attribute in ('ceiling', 'floor'):
            self.assertTrue(engine.Rule('(1e5000).{0} > 0'.format(attribute), context=context).matches({}))

    def test_engine_int_max_digits_set(self):
        # SET members aren't converted but comparing a large integer to a FLOAT value converts it
        rule = engine.Rule('1 in value', context=engine.Context(int_max_digits=20))
        self.assertTrue(rule.matches({'value': {1, 10 ** 20 - 1}}))
        for value in ({10 ** 20}, {(1, (10 ** 20,))}, {frozenset([10 ** 20])}):
            with self.subTest(value=value), self.assertRaises(errors.ArithmeticError):
                rule.matches({'value': value})

    def test_engine_int_max_digits_string_to_flt(self):
        rule = engine.Rule('value.to_flt > 0', context=engine.Context(int_max_digits=20))
        self.assertTrue(rule.matches({'value': hex(10 ** 20 - 1)}))
        with self.assertRaises(errors.ArithmeticError):
            rule.matches({'value': hex(10 ** 20)})

    def test_engine_int_max_digits_parse_float(self):
        context = engine.Context(int_max_digits=20)
        rule = engine.Rule('$parse_float(value) > 0', context=context)
        self.assertTrue(rule.matches({'value': hex(10 ** 20 - 1)}))
        with self.assertRaises(errors.ArithmeticError):
            rule.matches({'value': hex(10 ** 20)})
        # the limit is read from the context each time the function is called
        context.int_max_digits = 21
        self.assertTrue(rule.matches({'value': hex(10 ** 20)}))
        with self.assertRaises(errors.FunctionCallError):
            rule.matches({'value': '0x1+1j'})

    def test_engine_int_max_digits_parse_float_custom_builtins(self):
        # replacing the builtins like the getting started guide shows must keep using the context's limit
        context = engine.Context(int_max_digits=20)
        context.builtins = builtins.Builtins.from_defaults({'version': '5.1.1'}, timezone=context.default_timezone)
        rule = engine.Rule('$parse_float(value) > 0', context=context)
        with self.assertRaises(errors.ArithmeticError):
            rule.matches({'value': hex(10 ** 20)})
        context.int_max_digits = 0
        self.assertTrue(rule.matches({'value': hex(10 ** 4300)}))

    def test_engine_int_max_digits_default_follows_interpreter(self):
        self._set_int_max_str_digits(640)
        rule = engine.Rule('value > 0')
        with self.assertRaisesRegex(errors.ArithmeticError, r'\(640 digits\)'):
            rule.matches({'value': 10 ** 640})
        sys.set_int_max_str_digits(4300)
        self.assertTrue(rule.matches({'value': 10 ** 640}))

if __name__ == '__main__':
    unittest.main()
