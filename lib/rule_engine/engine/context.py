#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/engine/context.py
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
import threading
import warnings

from .. import ast
from .. import builtins
from .. import errors
from ..suggestions import suggest_symbol
from ..types import DataType

from ._attribute_resolver import _AttributeResolver

import dateutil.tz

def _tls_getter(thread_local, key, _builtins):
	# a function stub to be used with functools.partial for retrieving thread-local values
	return getattr(thread_local.storage, key)

def _default_type_resolver(_):
	return ast.DataType.UNDEFINED

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
			*,
			regex_flags=0,
			resolver=None,
			type_resolver=None,
			default_timezone='local',
			default_value=errors.UNDEFINED,
			decimal_context=None,
			mapping_attribute_lookup=True
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
		:param bool mapping_attribute_lookup: Whether or not to allow attribute-style access on :py:attr:`.MAPPING`
			values as a fallback to key-style lookup. When ``True`` (the default), accessing ``mapping.key`` falls
			back to ``mapping['key']`` and emits a :py:exc:`~rule_engine.errors.MappingAttributeLookupDeprecation`
			once per context. When ``False``, attribute access on a :py:attr:`.MAPPING` raises a parse-time error.
			This fallback is scheduled for removal in v6.0.

		.. versionchanged:: 2.0.0
			Added the *default_value* parameter.

		.. versionchanged:: 2.1.0
			If *type_resolver* is a dictionary, :py:func:`~.type_resolver_from_dict` will be called on it automatically
			and the result will be used as the callback.

		.. versionchanged:: 3.0.0
			Added the *decimal_context* parameter.

		.. versionchanged:: 5.0.0
			Added the *mapping_attribute_lookup* parameter.
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
		self.builtins = builtins.Builtins.from_defaults(
			values={'re_groups': builtins.BuiltinValueGenerator(functools.partial(_tls_getter, self._thread_local, 'regex_groups'))},
			value_types={'re_groups': ast.DataType.ARRAY(ast.DataType.STRING)},
			timezone=default_timezone
		)
		"""An instance of :py:class:`~rule_engine.builtins.Builtins` to provided a default set of builtin symbol values."""
		self.decimal_context = decimal_context or decimal.getcontext()
		"""The *decimal_context* parameter from :py:meth:`~__init__`"""
		if isinstance(type_resolver, collections.abc.Mapping):
			type_resolver = type_resolver_from_dict(type_resolver)
		self.__type_resolver = type_resolver or _default_type_resolver
		self.__resolver = resolver or resolve_item
		self.mapping_attribute_lookup = mapping_attribute_lookup
		"""The *mapping_attribute_lookup* parameter from :py:meth:`~__init__`."""
		self._mapping_fallback_lock = threading.Lock()
		self._mapping_fallback_warned = False

	def __getstate__(self):
		return {
			'regex_flags': self.regex_flags,
			'symbols': self.symbols,
			'default_timezone': self.default_timezone,
			'default_value': self.default_value,
			'decimal_context': self.decimal_context,
			'mapping_attribute_lookup': self.mapping_attribute_lookup,
			'_mapping_fallback_warned': self._mapping_fallback_warned,
			'_Context__type_resolver': self.__type_resolver,
			'_Context__resolver': self.__resolver,
		}

	def __setstate__(self, state):
		self.regex_flags = state['regex_flags']
		self.symbols = state['symbols']
		self.default_timezone = state['default_timezone']
		self.default_value = state['default_value']
		self.decimal_context = state['decimal_context']
		self.mapping_attribute_lookup = state['mapping_attribute_lookup']
		self._mapping_fallback_warned = state['_mapping_fallback_warned']
		self.__type_resolver = state['_Context__type_resolver']
		self.__resolver = state['_Context__resolver']
		# recreate transient objects that can not be pickled
		self._thread_local = threading.local()
		self._mapping_fallback_lock = threading.Lock()
		self.builtins = builtins.Builtins.from_defaults(
			values={'re_groups': builtins.BuiltinValueGenerator(functools.partial(_tls_getter, self._thread_local, 'regex_groups'))},
			value_types={'re_groups': ast.DataType.ARRAY(ast.DataType.STRING)},
			timezone=self.default_timezone
		)

	@contextlib.contextmanager
	def assignments(self, *assignments):
		"""
		Add the specified assignments to a thread-specific scope. This is used when an assignment originates from an
		expression.

		:param assignments: The one or more assignments to define.
		:type assignments: :py:class:`~rule_engine.ast.Assignment`
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
		if scope == builtins.Builtins.scope_name:
			thing = self.builtins
		if isinstance(thing, builtins.Builtins):
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

	def _warn_mapping_fallback(self, attribute_name):
		with self._mapping_fallback_lock:
			if self._mapping_fallback_warned:
				return
			self._mapping_fallback_warned = True
		message = (
			"accessing attribute {0!r} on a MAPPING value via dot syntax is deprecated; "
			"use mapping[{0!r}] instead. This fallback will be removed in v6.0. Set "
			"Context(mapping_attribute_lookup=False) to opt out now, or filter "
			"rule_engine.errors.MappingAttributeLookupDeprecation to silence this warning."
		).format(attribute_name)
		warnings.warn(errors.MappingAttributeLookupDeprecation(message), stacklevel=2)

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
		if scope == builtins.Builtins.scope_name:
			return self.builtins.resolve_type(name)
		for assignments in self._tls.assignment_scopes:
			if name in assignments:
				return assignments[name].value_type
		return self.__type_resolver(name)
