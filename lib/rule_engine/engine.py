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

import datetime
import functools
import math

from . import ast
from . import errors
from . import parser

import dateutil.tz

def resolve_attribute(thing, name):
	"""
	A replacement resolver function for looking up symbols as members of
	*thing*. This is effectively the same as ``thing.name``. The *thing* object
	can be a :py:class:`~collections.namedtuple`, a custom Python class or any
	other object. Each of the members of *thing* must be of a compatible data
	type.

	.. warning::
		This effectively exposes all members of *thing*. If any members are
		sensitive, then a custom resolver should be used that checks *name*
		against a whitelist of attributes that are allowed to be accessed.

	:param thing: The object on which the *name* attribute will be accessed.
	:param str name: The symbol name that is being resolved.
	:return: The value for the corresponding attribute *name*.
	"""
	for name_part in name.split('.'):
		if not hasattr(thing, name_part):
			raise errors.SymbolResolutionError(name_part)
		thing = getattr(thing, name_part)
	return thing

def resolve_item(thing, name):
	"""
	A resolver function for looking up symbols as items from an object (*thing*)
	which supports the :py:class:`~collections.abc.Mapping` interface, such as a
	dictionary. This is effectively the same as ``thing['name']``. Each of the
	values in *thing* must be of a compatible data type.

	:param thing: The object from which the *name* item will be accessed.
	:param str name: The symbol name that is being resolved.
	:return: The value for the corresponding attribute *name*.
	"""
	if name not in thing:
		raise errors.SymbolResolutionError(name)
	return thing[name]

def _type_resolver(type_map, name):
	if name not in type_map:
		raise errors.SymbolResolutionError(name)
	return type_map[name]

def type_resolver_from_dict(dictionary):
	"""
	Return a function suitable for use as the *type_resolver* for a
	:py:class:`.Context` instance from a dictionary. If any of the values within
	the dictionary are not of a compatible data type, a :py:exc:`TypeError` will
	be raised. Additionally, the resulting function will raise a
	:py:exc:`~rule_engine.errors.SymbolResolutionError` if the symbol name does
	not exist within the dictionary.

	:param dict dictionary: A dictionary (or any other object which supports the
		:py:class:`~collections.abc.Mapping` interface) from which to create the
		callback function.
	:return: The callback function.
	:rtype: function
	"""
	type_map = {key: value if isinstance(value, ast.DataType) else ast.DataType.from_value(value) for key, value in dictionary.items()}
	return functools.partial(_type_resolver, type_map)

class Context(object):
	"""
	An object defining the context for a rule's evaluation. This can be used to
	change the behavior of certain aspects of the rule such as how symbols are
	resolved and what regex flags should be used.
	"""
	def __init__(self, regex_flags=0, resolver=None, type_resolver=None, default_timezone='local'):
		"""
		:param int regex_flags: The flags to provide to functions in the
			:py:mod:`re` module.
		:param resolver: An optional callback function to use in place of
			:py:meth:`.resolve`.
		:param type_resolver: An optional callback function to use in place of
			:py:meth:`.resolve_type`.
		:param default_timezone: The default timezone to apply to
			:py:class:`~datetime.datetime` instances which do not have one
			specified. This is necessary for comparison operations. The value
			should either be a :py:class:`~datetime.tzinfo` instance, or a
			string. If *default_timzezone* is a string it must be one of the
			specially supported (case-insensitive) values of "local" or "utc".
		:type default_timezone: str, :py:class:`~datetime.tzinfo`
		"""
		self.regex_flags = regex_flags
		"""
		The flags to provide to the :py:func:`~re.match` and
		:py:func:`~re.search` functions when matching or searching for patterns.
		"""
		self.symbols = set()
		"""
		The symbols that are referred to by the rule. Some or all of these will
		need to be resolved at evaluation time. This attribute can be used after
		a rule is generated to ensure that all symbols are valid before it is
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
		self.default_timezone = default_timezone
		self.__type_resolver = type_resolver or (lambda _: ast.DataType.UNDEFINED)
		self.__resolver = resolver or resolve_item

	def resolve(self, thing, name, scope=None):
		"""
		The method to use for resolving symbols names to values. This function
		must return a compatible value for the specified symbol name. When a
		*scope* is defined, this function handles the resolution itself, however
		when the *scope* is ``None`` the resolver specified in
		:py:meth:`~.Context.__init__` is used which defaults to
		:py:func:`resolve_item`. This function must return a compatible value
		for the specified symbol name.

		:param thing: The object from which the *name* item will be accessed.
		:param str name: The symbol name that is being resolved.
		:return: The value for the corresponding attribute *name*.
		"""
		if scope is None:
			return self.__resolver(thing, name)
		if scope == 'built-in':
			if name == 'f.e':
				return math.e
			elif name == 'f.pi':
				return math.pi
			elif name == 'd.now':
				return datetime.datetime.now()
			elif name == 'd.today':
				return datetime.date.today()
		raise errors.SymbolResolutionError(name, symbol_scope=scope)

	def resolve_type(self, name):
		"""
		A method for providing type hints while the rule is being generated.
		This can be used to ensure that all symbol names are valid and that the
		types are appropriate for the operations being performed. It must then
		return one of the compatible data type constants if the symbol is valid
		or raise an exception. The default behavior is to return
		:py:data:`~rule_engine.ast.DataType.UNDEFINED` for all symbols.

		:param str name: The symbol name to provide a type hint for.
		:return: The type of the specified symbol
		"""
		return self.__type_resolver(name)

class Rule(object):
	"""
	A rule which parses a string with a logical expression and can then evaluate
	an arbitrary object for whether or not it matches based on the constraints
	of the expression.
	"""
	parser = parser.Parser()
	"""
	The :py:class:`~rule_engine.parser.Parser` instance that will be used for
	parsing the rule text into a compatible abstract syntax tree (AST) for
	evaluation.
	"""
	def __init__(self, text, context=None):
		"""
		:param str text: The text of the logical expression.
		:param context: The context to use for evaluating the expression on
			arbitrary objects. This can be used to change the default behavior.
			The default context is :py:class:`.Context` but any object providing
			the same interface (such as a subclass) can be used.
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
		A convenience function for iterating over *things* and yielding each
		member that :py:meth:`.matches` return True for.

		:param things: The collection of objects to iterate over.
		"""
		yield from (thing for thing in things if self.matches(thing))

	@classmethod
	def is_valid(cls, text, context=None):
		"""
		Test whether or not the rule is syntactically correct. This verifies the
		grammar is well structured and that there are no type compatibility
		issues regarding literals or symbols with known types (see
		:py:meth:`~.Context.resolve_type` for specifying symbol type
		information).

		:param str text: The text of the logical expression.
		:param context: The context as would be passed to the
			:py:meth:`.__init__` method. This can be used for specifying symbol
			type information.
		:return: Whether or not the expression is well formed and appears valid.
		:rtype: bool
		"""
		try:
			cls.parser.parse(text, (context or Context()))
		except errors.EngineError:
			return False
		return True

	def matches(self, thing):
		"""
		Evaluate the rule against the specified *thing*. This will either return
		whether *thing* matches, or an exception will be raised.

		:param thing: The object on which to apply the rule.
		:return: Whether or not the rule matches.
		:rtype: bool
		"""
		return bool(self.statement.evaluate(thing))

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

	def matches(self, thing):
		return self.statement.evaluate(thing)
