#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/engine.py
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
import collections.abc
import contextlib
import datetime
import decimal
import functools
import math
import re
import threading

from . import ast
from . import errors
from . import parser
from .suggestions import suggest_symbol

import dateutil.tz

def _now(builtins):
	return datetime.datetime.now(tz=builtins.timezone)

def _today(builtins):
	return _now(builtins).replace(hour=0, minute=0, second=0, microsecond=0)

def _tls_getter(thread_local, key, _builtins):
	# a function stub to be used with functools.partial for retrieving thread-local values
	return getattr(thread_local.storage, key)

def resolve_attribute(thing, name):
	"""
	A replacement resolver function for looking up symbols as members of *thing*. This is effectively the same as
	``thing.name``. The *thing* object can be a :py:func:`~collections.namedtuple`, a custom Python class or any other
	object. Each of the members of *thing* must be of a compatible data type.

	.. warning::
		This effectively exposes all members of *thing*. If any members are sensitive, then a custom resolver should be
		used that checks *name* against a whitelist of attributes that are allowed to be accessed.

	:param thing: The object on which the *name* attribute will be accessed.
	:param str name: The symbol name that is being resolved.
	:return: The value for the corresponding attribute *name*.
	"""
	if not hasattr(thing, name):
		raise errors.SymbolResolutionError(name, thing=thing, suggestion=suggest_symbol(name, dir(thing)))
	return getattr(thing, name)

def resolve_item(thing, name):
	"""
	A resolver function for looking up symbols as items from an object (*thing*) which supports the
	:py:class:`~collections.abc.Mapping` interface, such as a dictionary. This is effectively the same as
	``thing['name']``. Each of the values in *thing* must be of a compatible data type.

	:param thing: The object from which the *name* item will be accessed.
	:param str name: The symbol name that is being resolved.
	:return: The value for the corresponding attribute *name*.
	"""
	if not isinstance(thing, collections.abc.Mapping):
		raise errors.SymbolResolutionError(name, thing=thing)
	if name not in thing:
		raise errors.SymbolResolutionError(name, thing=thing, suggestion=suggest_symbol(name, thing.keys()))
	return thing[name]

def _type_resolver(type_map, name):
	if name not in type_map:
		raise errors.SymbolResolutionError(name, suggestion=suggest_symbol(name, type_map.keys()))
	return type_map[name]

def _float_op(value, op):
	if value.is_nan() or value.is_infinite():
		return value
	return op(value)

def type_resolver_from_dict(dictionary):
	"""
	Return a function suitable for use as the *type_resolver* for a :py:class:`.Context` instance from a dictionary. If
	any of the values within the dictionary are not of a compatible data type, a :py:exc:`TypeError` will be raised.
	Additionally, the resulting function will raise a :py:exc:`~rule_engine.errors.SymbolResolutionError` if the symbol
	name does not exist within the dictionary.

	:param dict dictionary: A dictionary (or any other object which supports the :py:class:`~collections.abc.Mapping`
		interface) from which to create the callback function.
	:return: The callback function.
	:rtype: function
	"""
	type_map = {key: value if ast.DataType.is_definition(value) else ast.DataType.from_value(value) for key, value in dictionary.items()}
	return functools.partial(_type_resolver, type_map)

_AttributeResolverFunction = collections.namedtuple('_AttributeResolverFunction', ('function', 'result_type'))
class _AttributeResolver(object):
	class attribute(object):
		__slots__ = ('types', 'name', 'result_type')
		type_map = collections.defaultdict(dict)
		def __init__(self, name, *data_types, result_type=ast.DataType.UNDEFINED):
			self.types = data_types
			self.name = name
			self.result_type = result_type

		def __call__(self, function):
			for type_ in self.types:
				self.type_map[type_][self.name] = _AttributeResolverFunction(function, self.result_type)
			return function

	def __call__(self, thing, object_, name):
		try:
			object_type = ast.DataType.from_value(object_)
		except TypeError:
			# if the object can't be mapped to a supported type, raise a resolution error
			raise errors.AttributeResolutionError(name, object_, thing=thing) from None
		resolver = self._get_resolver(object_type, name, thing=thing)
		value = resolver.function(self, object_)
		value = ast.coerce_value(value)
		if resolver.result_type == ast.DataType.UNDEFINED:
			return value
		value_type = ast.DataType.from_value(value)
		if ast.DataType.is_compatible(resolver.result_type, value_type):
			return value
		raise errors.AttributeTypeError(name, object_, is_value=value, is_type=value_type, expected_type=resolver.result_type)

	def _get_resolver(self, object_type, name, thing=errors.UNDEFINED):
		for data_type, attribute_resolvers in self.attribute.type_map.items():
			if ast.DataType.is_compatible(data_type, object_type):
				break
		else:
			raise errors.AttributeResolutionError(name, object_type, thing=thing)
		resolver = attribute_resolvers.get(name)
		if resolver is None:
			raise errors.AttributeResolutionError(name, object_type, thing=thing, suggestion=suggest_symbol(name, attribute_resolvers.keys()))
		return resolver

	def resolve_type(self, object_type, name):
		"""
		The method to use for resolving the data type of an attribute.

		:param object_type: The data type of the object that *name* is an attribute of.
		:param str name: The name of the attribute to retrieve the data type of.
		:return: The data type of the specified attribute.
		"""
		return self._get_resolver(object_type, name).result_type

	@attribute('date', ast.DataType.DATETIME, result_type=ast.DataType.DATETIME)
	def datetime_date(self, value):
		return value.replace(hour=0, minute=0, second=0, microsecond=0)

	@attribute('day', ast.DataType.DATETIME, result_type=ast.DataType.FLOAT)
	def datetime_day(self, value):
		return value.day

	@attribute('hour', ast.DataType.DATETIME, result_type=ast.DataType.FLOAT)
	def datetime_hour(self, value):
		return value.hour

	@attribute('microsecond', ast.DataType.DATETIME, result_type=ast.DataType.FLOAT)
	def datetime_microsecond(self, value):
		return value.microsecond

	@attribute('millisecond', ast.DataType.DATETIME, result_type=ast.DataType.FLOAT)
	def datetime_millisecond(self, value):
		return value.microsecond / 1000

	@attribute('minute', ast.DataType.DATETIME, result_type=ast.DataType.FLOAT)
	def datetime_minute(self, value):
		return value.minute

	@attribute('month', ast.DataType.DATETIME, result_type=ast.DataType.FLOAT)
	def datetime_month(self, value):
		return value.month

	@attribute('second', ast.DataType.DATETIME, result_type=ast.DataType.FLOAT)
	def datetime_second(self, value):
		return value.second

	@attribute('weekday', ast.DataType.DATETIME, result_type=ast.DataType.STRING)
	def datetime_weekday(self, value):
		# use strftime %A so the value is localized
		return value.strftime('%A')

	@attribute('year', ast.DataType.DATETIME, result_type=ast.DataType.FLOAT)
	def datetime_year(self, value):
		return value.year

	@attribute('zone_name', ast.DataType.DATETIME, result_type=ast.DataType.STRING)
	def datetime_zone_name(self, value):
		return value.tzname()

	@attribute('ceiling', ast.DataType.FLOAT, result_type=ast.DataType.FLOAT)
	def float_ceiling(self, value):
		return _float_op(value, math.ceil)

	@attribute('floor', ast.DataType.FLOAT, result_type=ast.DataType.FLOAT)
	def float_floor(self, value):
		return _float_op(value, math.floor)

	@attribute('to_str', ast.DataType.FLOAT, result_type=ast.DataType.STRING)
	def float_to_str(self, value):
		# keep the string representations consistent for nan, inf, -inf
		if value.is_nan():
			return 'nan'
		elif value.is_infinite():
			if value.is_signed():
				return '-inf'
			else:
				return 'inf'
		return str(value)

	@attribute('keys', ast.DataType.MAPPING, result_type=ast.DataType.ARRAY)
	def mapping_keys(self, value):
		return tuple(value.keys())

	@attribute('values', ast.DataType.MAPPING, result_type=ast.DataType.ARRAY)
	def mapping_values(self, value):
		return tuple(value.values())

	@attribute('to_ary', ast.DataType.SET, result_type=ast.DataType.ARRAY)
	def set_to_ary(self, value):
		return tuple(value)

	@attribute('as_lower', ast.DataType.STRING, result_type=ast.DataType.STRING)
	def string_as_lower(self, value):
		return value.lower()

	@attribute('as_upper', ast.DataType.STRING, result_type=ast.DataType.STRING)
	def string_as_upper(self, value):
		return value.upper()

	@attribute('to_ary', ast.DataType.STRING, result_type=ast.DataType.ARRAY(ast.DataType.STRING))
	def string_to_ary(self, value):
		return value.split()

	@attribute('to_flt', ast.DataType.STRING, result_type=ast.DataType.FLOAT)
	def string_to_flt(self, value):
		value = value.strip()
		if re.match(r'-?inf', value):
			return decimal.Decimal(value)
		match = re.match(r'^(' + parser.Parser.get_token_regex('FLOAT') + ')$', value)
		if match is None:
			return decimal.Decimal('nan')
		return parser.literal_eval(match.group(0))

	@attribute('to_int', ast.DataType.STRING, result_type=ast.DataType.FLOAT)
	def string_to_int(self, value):
		value = self.string_to_flt(value)
		if not ast.is_integer_number(value):
			raise errors.EvaluationError('data type mismatch (not an integer number)')
		return value

	@attribute('is_empty', ast.DataType.ARRAY, ast.DataType.STRING, ast.DataType.MAPPING, ast.DataType.SET, result_type=ast.DataType.BOOLEAN)
	def value_is_empty(self, value):
		return len(value) == 0

	@attribute('length', ast.DataType.ARRAY, ast.DataType.STRING, ast.DataType.MAPPING, ast.DataType.SET, result_type=ast.DataType.FLOAT)
	def value_length(self, value):
		return len(value)

	@attribute('to_set', ast.DataType.ARRAY, ast.DataType.STRING, result_type=ast.DataType.SET)
	def value_to_set(self, value):
		return set(value)

class Builtins(collections.abc.Mapping):
	"""
	A class to define and provide variables to within the builtin context of rules. These can be accessed by specifying
	a symbol name with the ``$`` prefix.
	"""
	scope_name = 'built-in'
	"""The identity name of the scope for builtin symbols."""
	def __init__(self, values, namespace=None, timezone=None, value_types=None):
		"""
		:param dict values: A mapping of string keys to be used as symbol names with values of either Python literals or
			a function which will be called when the symbol is accessed. When using a function, it will be passed a
			single argument, which is the instance of :py:class:`Builtins`.
		:param str namespace: The namespace of the variables to resolve.
		:param timezone: A timezone to use when resolving timestamps.
		:type timezone: :py:class:`~datetime.tzinfo`
		:param dict value_types: A mapping of the values to their datatypes.

		.. versionchanged:: 2.3.0
			Added the *value_types* parameter.
		"""
		self.__values = values
		self.__value_types = value_types or {}
		self.namespace = namespace
		self.timezone = timezone or dateutil.tz.tzlocal()

	def resolve_type(self, name):
		"""
		The method to use for resolving the data type of a builtin symbol.

		:param str name: The name of the symbol to retrieve the data type of.
		:return: The data type of the symbol or :py:attr:`~rule_engine.ast.DataType.UNDEFINED`.
		"""
		return self.__value_types.get(name, ast.DataType.UNDEFINED)

	def __repr__(self):
		return "<{} namespace={!r} keys={!r} timezone={!r} >".format(self.__class__.__name__, self.namespace, tuple(self.keys()), self.timezone)

	def __getitem__(self, name):
		value = self.__values[name]
		if isinstance(value, collections.abc.Mapping):
			if self.namespace is None:
				namespace = name
			else:
				namespace = self.namespace + '.' + name
			return self.__class__(value, namespace=namespace, timezone=self.timezone)
		elif callable(value):
			value = value(self)
		return value

	def __iter__(self):
		return iter(self.__values)

	def __len__(self):
		return len(self.__values)

	@classmethod
	def from_defaults(cls, values=None, **kwargs):
		"""Initialize a :py:class:`Builtins` instance with a set of default values."""
		# there may be errors here if the decimal.Context precision exceeds what is provided by the math constants
		default_values = {
			'e': decimal.Decimal(repr(math.e)),
			'pi': decimal.Decimal(repr(math.pi)),
			'now': _now,
			'today': _today
		}
		default_values.update(values or {})
		default_value_types = {
			'e': ast.DataType.FLOAT,
			'pi': ast.DataType.FLOAT,
			'now': ast.DataType.DATETIME,
			'today': ast.DataType.DATETIME
		}
		default_value_types.update(kwargs.pop('value_types', {}))
		return cls(default_values, value_types=default_value_types, **kwargs)

class _ThreadLocalStorage(object):
	"""
	An object whose attributes are required to be tracked separately among multiple threads. This is to guarantee that
	if a context is used by one or more rules that are being evaluated simultaneously in multiple threads, that the
	states are kept isolated.
	"""
	__slots__ = ('assignment_scopes', 'regex_groups')
	def __init__(self):
		self.assignment_scopes = collections.deque()
		self.regex_groups = None

	def reset(self):
		self.assignment_scopes.clear()
		self.regex_groups = None

class Context(object):
	"""
	An object defining the context for a rule's evaluation. This can be used to change the behavior of certain aspects
	of the rule such as how symbols are resolved and what regex flags should be used.
	"""
	def __init__(
			self,
			regex_flags=0,
			resolver=None,
			type_resolver=None,
			default_timezone='local',
			default_value=errors.UNDEFINED,
			decimal_context=None
	):
		"""
		:param int regex_flags: The flags to provide to functions in the :py:mod:`re` module when calling either the
			:py:func:`~re.match` or :py:func:`~re.search` functions for comparison expressions.
		:param resolver: An optional callback function to use in place of :py:meth:`.resolve`.
		:param type_resolver: An optional callback function to use in place of :py:meth:`.resolve_type`.
		:type type_resolver: function, dict
		:param default_timezone: The default timezone to apply to :py:class:`~datetime.datetime` instances which do not
			have one specified. This is necessary for comparison operations. The value should either be a
			:py:class:`~datetime.tzinfo` instance, or a string. If *default_timzezone* is a string it must be one of the
			specially supported (case-insensitive) values of "local" or "utc".
		:type default_timezone: str, :py:class:`~datetime.tzinfo`
		:param default_value: The default value to return when resolving either a missing symbol or attribute.
		:param decimal_context: A specific :py:class:`decimal.Context` object to use for evaluation of ``FLOAT`` values.
			The default value will be taken from the current thread and will be used by all evaluations using this
			:py:class:`~rule_engine.engine.Context` regardless of the decimal context of the thread which evaluates the
			rule. This causes the rule evaluation to be consistent regardless of the calling thread.

		.. versionchanged:: 2.0.0
			Added the *default_value* parameter.

		.. versionchanged:: 2.1.0
			If *type_resolver* is a dictionary, :py:func:`~.type_resolver_from_dict` will be called on it automatically
			and the result will be used as the callback.

		.. versionchanged:: 3.0.0
			Added the *decimal_context* parameter.
		"""
		self.regex_flags = regex_flags
		"""The *regex_flags* parameter from :py:meth:`~__init__`"""
		self.symbols = set()
		"""
		The symbols that are referred to by the rule. Some or all of these will need to be resolved at evaluation time.
		This attribute can be used after a rule is generated to ensure that all symbols are valid before it is
		evaluated.
		"""
		if isinstance(default_timezone, str):
			default_timezone = default_timezone.lower()
			if default_timezone == 'local':
				default_timezone = dateutil.tz.tzlocal()
			elif default_timezone == 'utc':
				default_timezone = dateutil.tz.tzutc()
			else:
				raise ValueError('unsupported timezone: ' + default_timezone)
		elif not isinstance(default_timezone, datetime.tzinfo):
			raise TypeError('invalid default_timezone type')
		self._thread_local = threading.local()
		self.default_timezone = default_timezone
		"""The *default_timezone* parameter from :py:meth:`~__init__`"""
		self.default_value = default_value
		"""The *default_value* parameter from :py:meth:`~__init__`"""
		self.builtins = Builtins.from_defaults(
			values={'re_groups': functools.partial(_tls_getter, self._thread_local, 'regex_groups')},
			value_types={'re_groups': ast.DataType.ARRAY(ast.DataType.STRING)},
			timezone=default_timezone
		)
		"""An instance of :py:class:`Builtins` to provided a default set of builtin symbol values."""
		self.decimal_context = decimal_context or decimal.getcontext()
		"""The *decimal_context* parameter from :py:meth:`~__init__`"""
		if isinstance(type_resolver, collections.abc.Mapping):
			type_resolver = type_resolver_from_dict(type_resolver)
		self.__type_resolver = type_resolver or (lambda _: ast.DataType.UNDEFINED)
		self.__resolver = resolver or resolve_item

	@contextlib.contextmanager
	def assignments(self, *assignments):
		"""
		Add the specified assignments to a thread-specific scope. This is used when an assignment originates from an
		expression.

		:param assignment: The one or more assignments to define.
		:type assignment: :py:class:`~rule_engine.ast.Assignment`
		"""
		self._tls.assignment_scopes.append({assign.name: assign for assign in assignments})
		try:
			yield
		finally:
			self._tls.assignment_scopes.pop()

	@property
	def _tls(self):
		if not hasattr(self._thread_local, 'storage'):
			self._thread_local.storage = _ThreadLocalStorage()
		return self._thread_local.storage

	def resolve(self, thing, name, scope=None):
		"""
		The method to use for resolving symbols names to values. This function must return a compatible value for the
		specified symbol name. When a *scope* is defined, this function handles the resolution itself, however when the
		*scope* is ``None`` the resolver specified in :py:meth:`~.Context.__init__` is used which defaults to
		:py:func:`resolve_item`.

		If *name* fails to resolve, this method will raise :py:exc:`~rule_engine.errors.SymbolResolutionError`. It is
		then up to the caller to determine whether or not it is appropriate to use :py:attr:`.default_value`.

		:param thing: The object from which the *name* item will be accessed.
		:param str name: The symbol name that is being resolved.
		:return: The value for the corresponding symbol *name*.
		"""
		if scope == Builtins.scope_name:
			thing = self.builtins
		if isinstance(thing, Builtins):
			return resolve_item(thing, name)
		if scope is None:
			for assignments in self._tls.assignment_scopes:
				if name in assignments:
					return assignments[name].value
			return self.__resolver(thing, name)
		raise errors.SymbolResolutionError(name, symbol_scope=scope, thing=thing)

	__resolve_attribute = _AttributeResolver()
	def resolve_attribute(self, thing, object_, name):
		"""
		The method to use for resolving attributes from values. This function must return a compatible value for the
		specified attribute name.

		If *name* fails to resolve, this method will raise :py:exc:`~rule_engine.errors.AttributeResolutionError`. It is
		then up to the caller to determine whether or not it is appropriate to use :py:attr:`.default_value`.

		:param thing: The object from which the *object_* was retrieved.
		:param object_: The object from which the *name* attribute will be accessed.
		:param str name: The attribute name that is being resolved.
		:return: The value for the corresponding attribute *name*.
		"""
		return self.__resolve_attribute(thing, object_, name)
	resolve_attribute_type = __resolve_attribute.resolve_type

	def resolve_type(self, name, scope=None):
		"""
		A method for providing type hints while the rule is being generated. This can be used to ensure that all symbol
		names are valid and that the types are appropriate for the operations being performed. It must then return one
		of the compatible data type constants if the symbol is valid or raise an exception. The default behavior is to
		return :py:data:`~rule_engine.ast.DataType.UNDEFINED` for all symbols.

		:param str name: The symbol name to provide a type hint for.
		:param str scope: An optional scope name that identifies from where to resolve the name.
		:return: The type of the specified symbol.
		"""
		if scope == Builtins.scope_name:
			return self.builtins.resolve_type(name)
		for assignments in self._tls.assignment_scopes:
			if name in assignments:
				return assignments[name].value_type
		return self.__type_resolver(name)

class Rule(object):
	"""
	A rule which parses a string with a logical expression and can then evaluate an arbitrary object for whether or not
	it matches based on the constraints of the expression.
	"""
	parser = parser.Parser()
	"""
	The :py:class:`~rule_engine.parser.Parser` instance that will be used for parsing the rule text into a compatible
	abstract syntax tree (AST) for evaluation.
	"""
	def __init__(self, text, context=None):
		"""
		:param str text: The text of the logical expression.
		:param context: The context to use for evaluating the expression on arbitrary objects. This can be used to
			change the default behavior. The default context is :py:class:`.Context` but any object providing the same
			interface (such as a subclass) can be used.
		:type context: :py:class:`.Context`
		"""
		context = context or Context()
		self.text = text
		self.context = context
		self.statement = self.parser.parse(text, context)

	def __repr__(self):
		return "<{0} text={1!r} >".format(self.__class__.__name__, self.text)

	def __str__(self):
		return self.text

	def filter(self, things):
		"""
		A convenience function for iterating over *things* and yielding each member that :py:meth:`.matches` return True
		for.

		:param things: The collection of objects to iterate over.
		"""
		yield from (thing for thing in things if self.matches(thing))

	@classmethod
	def is_valid(cls, text, context=None):
		"""
		Test whether or not the rule is syntactically correct. This verifies the grammar is well structured and that
		there are no type compatibility issues regarding literals or symbols with known types (see
		:py:meth:`~.Context.resolve_type` for specifying symbol type information).

		:param str text: The text of the logical expression.
		:param context: The context as would be passed to the :py:meth:`.__init__` method. This can be used for
			specifying symbol type information.
		:return: Whether or not the expression is well formed and appears valid.
		:rtype: bool
		"""
		try:
			cls.parser.parse(text, (context or Context()))
		except errors.EngineError:
			return False
		return True

	def evaluate(self, thing):
		"""
		Evaluate the rule against the specified *thing* and return the value. This can be used to, for example, apply
		the symbol resolver.

		:param thing: The object on which to apply the rule.
		:return: The value the rule evaluates to. Unlike the :py:meth:`.matches` method, this is not necessarily a
			boolean.
		"""
		self.context._tls.reset()
		with decimal.localcontext(self.context.decimal_context):
			return self.statement.evaluate(thing)

	def matches(self, thing):
		"""
		Evaluate the rule against the specified *thing*. This will either return whether *thing* matches, or an
		exception will be raised.

		:param thing: The object on which to apply the rule.
		:return: Whether or not the rule matches.
		:rtype: bool
		"""
		return bool(self.evaluate(thing))

	def to_graphviz(self):
		"""
		Generate a diagram of the parsed rule's AST using GraphViz.

		:return: The rule diagram.
		:rtype: :py:class:`graphviz.Digraph`
		"""
		import graphviz
		digraph = graphviz.Digraph(comment=self.text)
		self.statement.to_graphviz(digraph)
		return digraph

class DebugRule(Rule):
	parser = None
	def __init__(self, *args, **kwargs):
		self.parser = parser.Parser(debug=True)
		super(DebugRule, self).__init__(*args, **kwargs)
