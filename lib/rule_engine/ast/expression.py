#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/expression.py
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
import datetime
import functools
import operator

from .. import builtins as _builtins
from .. import errors
from ..suggestions import suggest_symbol
from ..types import DataType, coerce_value, is_numeric
from ..types import _ObjectDataTypeDef

from .base import (
	Assignment,
	ExpressionBase,
	LiteralExpressionBase,
	_assert_is_integer_number,
	_is_reduced,
	_resolve_type,
)
from .literal import BooleanExpression, FloatExpression, NullExpression, TimedeltaExpression

################################################################################
# Miscellaneous Expressions
################################################################################
class ComprehensionExpression(ExpressionBase):
	result_type = DataType.ARRAY
	def __init__(self, context, result, variable, iterable, condition=None):
		self.context = context
		self.result = result
		self.variable = variable
		self.iterable = iterable
		self.condition = condition
		self.result_type = DataType.ARRAY(self.result.result_type)

	@classmethod
	def build(cls, context, result, variable, iterable, condition=None):
		iterable = iterable.build()
		if iterable.result_type is not DataType.UNDEFINED and not iterable.result_type.is_iterable:
			raise errors.EvaluationError('data type mismatch (comprehension requires an iterable)')
		resolved_iterable_type = _resolve_type(iterable.result_type, context)
		assignment = Assignment(variable, value_type=getattr(resolved_iterable_type, 'iterable_type', DataType.UNDEFINED))
		with context.assignments(assignment):
			if condition is not None:
				condition = condition.build()
			result = result.build()
		return cls(context, result, variable, iterable, condition=condition).reduce()

	def __repr__(self):
		return "<{0} iterable={1!r} result={2!r} condition={3!r} >".format(self.__class__.__name__, self.iterable, self.result, self.condition)

	def evaluate(self, thing):
		output_array = collections.deque()
		input_iterable = self.iterable.evaluate(thing)
		if not DataType.from_value(input_iterable).is_iterable:
			raise errors.EvaluationError('data type mismatch (comprehension requires an iterable)')
		for value in input_iterable:
			assignment = Assignment(self.variable, value=value)
			with self.context.assignments(assignment):
				if self.condition is None or self.condition.evaluate(thing):
					output_array.append(self.result.evaluate(thing))
		return tuple(output_array)

	def to_graphviz(self, digraph, *args, **kwargs):
		digraph.node(str(id(self)), "{}\nvariable={!r}".format(self.__class__.__name__, self.variable))
		self.result.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.result)), label='result')
		self.iterable.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.iterable)), label='iterable')
		if self.condition is not None:
			self.condition.to_graphviz(digraph, *args, **kwargs)
			digraph.edge(str(id(self)), str(id(self.condition)), label='condition')

class ContainsExpression(ExpressionBase):
	"""An expression used to test whether an item exists within a container."""
	__slots__ = ('container', 'member')
	result_type = DataType.BOOLEAN
	def __init__(self, context, container, member):
		if container.result_type == DataType.BYTES or container.result_type == DataType.STRING:
			if member.result_type != DataType.UNDEFINED and member.result_type != container.result_type:
				raise errors.EvaluationError('data type mismatch')
		elif isinstance(_resolve_type(container.result_type, context), _ObjectDataTypeDef):
			raise errors.EvaluationError('data type mismatch (containment check on OBJECT)')
		elif container.result_type != DataType.UNDEFINED and container.result_type.is_scalar:
			raise errors.EvaluationError('data type mismatch')
		self.context = context
		self.member = member
		self.container = container

	@classmethod
	def build(cls, context, container, member):
		return cls(context, container.build(), member.build()).reduce()

	def __repr__(self):
		return "<{0} container={1!r} member={2!r} >".format(self.__class__.__name__, self.container, self.member)

	def evaluate(self, thing):
		container_value = self.container.evaluate(thing)
		container_value_type = DataType.from_value(container_value)
		member_value = self.member.evaluate(thing)
		if container_value_type == DataType.BYTES or container_value_type == DataType.STRING:
			if DataType.from_value(member_value) != container_value_type:
				raise errors.EvaluationError('data type mismatch')
		return bool(member_value in container_value)

	def reduce(self):
		if not _is_reduced(self.container, self.member):
			return self
		return BooleanExpression(self.context, self.evaluate(None))

	def to_graphviz(self, digraph, *args, **kwargs):
		super(ContainsExpression, self).to_graphviz(digraph, *args, **kwargs)
		self.container.to_graphviz(digraph, *args, **kwargs)
		self.member.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.container)), label='container')
		digraph.edge(str(id(self)), str(id(self.member)), label='member')

class GetAttributeExpression(ExpressionBase):
	"""A class representing an expression in which *name* is retrieved as an attribute of *object*."""
	__slots__ = ('name', 'object', 'safe', '_object_type')
	def __init__(self, context, object_, name, safe=False):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param object_: The parent object from which to retrieve the attribute.
		:param str name: The name of the attribute to retrieve.
		:param bool safe: Whether or not the safe version should be invoked.

		.. versionchanged:: 2.4.0
			Added the *safe* parameter.
		"""
		self.context = context
		self.object = object_
		self._object_type = None
		if self.object.result_type != DataType.UNDEFINED:
			if not (self.object.result_type == DataType.NULL and safe):
				resolved_object_type = _resolve_type(self.object.result_type, context)
				if isinstance(resolved_object_type, _ObjectDataTypeDef):
					if name not in resolved_object_type.attributes:
						raise errors.ObjectAttributeError(
							name,
							resolved_object_type,
							suggestion=suggest_symbol(name, resolved_object_type.attributes.keys())
						)
					self._object_type = resolved_object_type
					attribute_type = _resolve_type(resolved_object_type.attributes[name], context)
					self.result_type = attribute_type
				else:
					try:
						self.result_type = context.resolve_attribute_type(self.object.result_type, name)
					except errors.AttributeResolutionError as error:
						# this is necessary because MAPPING objects can have their keys accessed as attributes
						if not isinstance(self.object.result_type, DataType.MAPPING.__class__):
							raise error
						if not context.mapping_attribute_lookup:
							raise errors.EvaluationError(
								"attribute access on a MAPPING is disabled - use mapping[{0!r}] instead, "
								"or set mapping_attribute_lookup=True on the Context for v4-compatible "
								"behavior (deprecated, removal scheduled for v6.0)".format(name)
							)
						# leave the result type undefined because the name could be a mapping key or attribute
		self.name = name
		self.safe = safe

	@classmethod
	def build(cls, context, object_, name, safe=False):
		return cls(context, object_.build(), name, safe=safe).reduce()

	def __repr__(self):
		return "<{0} name={1!r} >".format(self.__class__.__name__, self.name)

	def evaluate(self, thing):
		resolved_obj = self.object.evaluate(thing)
		if resolved_obj is None and self.safe:
			return resolved_obj

		if self._object_type is not None:
			try:
				value = self._object_type.accessor(resolved_obj, self.name)
			except (AttributeError, KeyError):
				default_value = self.context.default_value
				if default_value is errors.UNDEFINED:
					raise errors.ObjectAttributeError(
						self.name,
						self._object_type,
						thing=thing,
						suggestion=suggest_symbol(self.name, self._object_type.attributes.keys())
					) from None
				value = default_value
			return self._new_value(value, verify_type=False)

		attribute_error = None
		try:
			value = self.context.resolve_attribute(thing, resolved_obj, self.name)
		except errors.AttributeResolutionError as error:
			attribute_error = error
		else:
			return self._new_value(value, verify_type=False)

		if isinstance(resolved_obj, collections.abc.Mapping) and not isinstance(resolved_obj, _builtins.Builtins):
			if not self.context.mapping_attribute_lookup:
				raise attribute_error
			self.context._warn_mapping_fallback(self.name)

		try:
			value = self.context.resolve(resolved_obj, self.name)
		except errors.SymbolResolutionError as symbol_error:
			default_value = self.context.default_value
			if default_value is errors.UNDEFINED:
				suggestion = attribute_error.suggestion or symbol_error.suggestion
				if attribute_error.suggestion and symbol_error.suggestion:
					# if there are two suggestions, select the best one
					suggestion = suggest_symbol(self.name, (attribute_error.suggestion, symbol_error.suggestion))
				attribute_error.suggestion = suggestion
				raise attribute_error from None
			value = default_value
		return self._new_value(value, verify_type=False)

	def reduce(self):
		if not _is_reduced(self.object):
			return self
		literal = LiteralExpressionBase.from_value(self.context, self.evaluate(None))
		if literal.result_type == DataType.FUNCTION and DataType.is_compatible(self.result_type, DataType.FUNCTION):
			literal.result_type = self.result_type
		return literal

	def to_graphviz(self, digraph, *args, **kwargs):
		digraph.node(str(id(self)), "{}\nname={!r}".format(self.__class__.__name__, self.name))
		self.object.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.object)))

class GetItemExpression(ExpressionBase):
	"""A class representing an expression in which an *item* is retrieved from a container *object*."""
	__slots__ = ('container', 'item', 'safe')
	def __init__(self, context, container, item, safe=False):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param container: The container object from which to retrieve the item.
		:param str item: The item to retrieve from the container.
		:param bool safe: Whether or not the safe version should be invoked.

		.. versionchanged:: 2.4.0
			Added the *safe* parameter.
		"""
		self.context = context
		self.container = container
		resolved_container_type = _resolve_type(container.result_type, context)
		if container.result_type == DataType.BYTES:
			if not DataType.is_compatible(item.result_type, DataType.FLOAT):
				raise errors.EvaluationError('data type mismatch (not an integer number)')
			self.result_type = DataType.FLOAT
		elif container.result_type == DataType.STRING:
			if not DataType.is_compatible(item.result_type, DataType.FLOAT):
				raise errors.EvaluationError('data type mismatch (not an integer number)')
			self.result_type = DataType.STRING
		# check against __class__ so the parent class is dynamic in case it changes in the future, what we're doing here
		# is explicitly checking if result_type is an array with out checking the value_type
		elif isinstance(resolved_container_type, DataType.ARRAY.__class__):
			if not DataType.is_compatible(item.result_type, DataType.FLOAT):
				raise errors.EvaluationError('data type mismatch (not an integer number)')
			self.result_type = _resolve_type(resolved_container_type.value_type, context)
		elif isinstance(resolved_container_type, DataType.MAPPING.__class__):
			if not (safe or DataType.is_compatible(item.result_type, resolved_container_type.key_type)):
				raise errors.LookupError(errors.UNDEFINED, errors.UNDEFINED)
			self.result_type = _resolve_type(resolved_container_type.value_type, context)
		elif isinstance(resolved_container_type, DataType.SET.__class__):
			raise errors.EvaluationError('data type mismatch (container is a set)')
		elif isinstance(resolved_container_type, _ObjectDataTypeDef):
			raise errors.EvaluationError(
				"data type mismatch (item access on OBJECT - use {0}.attribute instead)".format(resolved_container_type.name)
			)
		elif container.result_type != DataType.UNDEFINED:
			if not (container.result_type == DataType.NULL and safe):
				raise errors.EvaluationError('data type mismatch')
		self.item = item
		self.safe = safe

	@classmethod
	def build(cls, context, container, item, safe=False):
		return cls(context, container.build(), item.build(), safe=safe).reduce()

	def __repr__(self):
		return "<{0} container={1!r} item={2!r} >".format(self.__class__.__name__, self.container, self.item)

	def evaluate(self, thing):
		resolved_obj = self.container.evaluate(thing)
		if resolved_obj is None:
			if self.safe:
				return resolved_obj
			raise errors.EvaluationError('data type mismatch (container is null)')

		resolved_item = self.item.evaluate(thing)
		if isinstance(resolved_obj, (bytes, str, tuple)):
			_assert_is_integer_number(resolved_item)
			resolved_item = int(resolved_item)
		try:
			value = operator.getitem(resolved_obj, resolved_item)
		except (IndexError, KeyError):
			if self.safe:
				return None
			raise errors.LookupError(resolved_obj, resolved_item)
		return self._new_value(value, verify_type=False)

	def reduce(self):
		if isinstance(self.container.result_type, DataType.MAPPING.__class__):
			if self.safe and not DataType.is_compatible(self.item.result_type, self.container.result_type.key_type):
				return NullExpression(self.context)
		if _is_reduced(self.container, self.item):
			return LiteralExpressionBase.from_value(self.context, self.evaluate(None))
		return self

	def to_graphviz(self, digraph, *args, **kwargs):
		super(GetItemExpression, self).to_graphviz(digraph, *args, **kwargs)
		self.container.to_graphviz(digraph, *args, **kwargs)
		self.item.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.container)), label='container')
		digraph.edge(str(id(self)), str(id(self.item)), label='item')

class GetSliceExpression(ExpressionBase):
	"""A class representing an expression in which a range of items is retrieved from a container *object*."""
	__slots__ = ('container', 'start', 'stop', 'safe')
	def __init__(self, context, container, start=None, stop=None, safe=False):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param container: The container object from which to retrieve the item.
		:param start: The expression that represents the starting index of the slice.
		:param stop: The expression that represents the stopping index of the slice.
		:param bool safe: Whether or not the safe version should be invoked.

		.. versionchanged:: 2.4.0
			Added the *safe* parameter.
		"""
		self.context = context
		self.container = container
		if container.result_type == DataType.BYTES:
			self.result_type = DataType.BYTES
		elif container.result_type == DataType.STRING:
			self.result_type = DataType.STRING
		# check against __class__ so the parent class is dynamic in case it changes in the future, what we're doing here
		# is explicitly checking if result_type is an array with out checking the value_type
		elif isinstance(container.result_type, DataType.ARRAY.__class__):
			self.result_type = container.result_type
		elif isinstance(container.result_type, DataType.SET.__class__):
			raise errors.EvaluationError('data type mismatch (container is a set)')
		elif container.result_type != DataType.UNDEFINED:
			if not (container.result_type == DataType.NULL and safe):
				raise errors.EvaluationError('data type mismatch')
		self.start = start or LiteralExpressionBase.from_value(context, 0)
		self.stop = stop or LiteralExpressionBase.from_value(context, None)
		self.safe = safe

	@classmethod
	def build(cls, context, container, start=None, stop=None, safe=False):
		if start is not None:
			start = start.build()
		if stop is not None:
			stop = stop.build()
		return cls(context, container.build(), start=start, stop=stop, safe=safe).reduce()

	def __repr__(self):
		return "<{0} container={1!r} start={2!r} stop={3!r} >".format(self.__class__.__name__, self.container, self.start, self.stop)

	def evaluate(self, thing):
		resolved_obj = self.container.evaluate(thing)
		if resolved_obj is None:
			if self.safe:
				return resolved_obj
			raise errors.EvaluationError('data type mismatch')

		resolved_start = self.start.evaluate(thing)
		if resolved_start is not None:
			_assert_is_integer_number(resolved_start)
			resolved_start = int(resolved_start)
		resolved_stop = self.stop.evaluate(thing)
		if resolved_stop is not None:
			_assert_is_integer_number(resolved_stop)
			resolved_stop = int(resolved_stop)
		value = operator.getitem(resolved_obj, slice(resolved_start, resolved_stop))
		return coerce_value(value, verify_type=False)

	def reduce(self):
		if not _is_reduced(self.container, self.start, self.stop):
			return self
		return LiteralExpressionBase.from_value(self.context, self.evaluate(None))

	def to_graphviz(self, digraph, *args, **kwargs):
		super(GetSliceExpression, self).to_graphviz(digraph, *args, **kwargs)
		self.container.to_graphviz(digraph, *args, **kwargs)
		self.start.to_graphviz(digraph, *args, **kwargs)
		self.stop.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.container)), label='container')
		digraph.edge(str(id(self)), str(id(self.start)), label='start')
		digraph.edge(str(id(self)), str(id(self.stop)), label='stop')

class SymbolExpression(ExpressionBase):
	"""
	A class representing a symbol name to be resolved at evaluation time with the help of a
	:py:class:`~rule_engine.engine.Context` object.
	"""
	__slots__ = ('name', 'result_type', 'scope')
	def __init__(self, context, name, scope=None):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param str name: The name of the symbol. This will be resolved with a given context object on the specified
			*thing*.
		:param str scope: The optional scope to use while resolving the symbol.
		"""
		context.symbols.add(name)
		self.context = context
		self.name = name
		type_hint = context.resolve_type(name, scope=scope)
		if type_hint is not None:
			self.result_type = type_hint
		self.scope = scope

	def __repr__(self):
		return "<{0} name={1!r} >".format(self.__class__.__name__, self.name)

	def evaluate(self, thing):
		try:
			value = self.context.resolve(thing, self.name, scope=self.scope)
		except errors.SymbolResolutionError:
			default_value = self.context.default_value
			if default_value is errors.UNDEFINED:
				raise
			value = default_value
		value = self._new_value(value, verify_type=False)

		# if the expected result type is undefined, return the value
		if self.result_type == DataType.UNDEFINED:
			return value

		# OBJECT values are opaque to DataType.from_value; trust the schema annotation and delegate attribute-level
		# type checking to GetAttributeExpression
		if isinstance(self.result_type, _ObjectDataTypeDef):
			return value

		# use DataType.from_value to raise a TypeError if value is not of a
		# compatible data type
		value_type = DataType.from_value(value)

		# if the type is the expected result type, return the value
		if DataType.is_compatible(value_type, self.result_type):
			if self.result_type.is_scalar:
				return value
			if self.result_type.value_type == DataType.UNDEFINED:
				return value
			if value_type.value_type == DataType.UNDEFINED:
				return value
			if self.result_type.value_type != DataType.NULL and not self.result_type.value_type_nullable and any(v is None for v in value):
				raise errors.SymbolTypeError(self.name, is_value=value, is_type=value_type, expected_type=self.result_type)
			if self.result_type.value_type == value_type.value_type:
				return value

		# if the type is null, return the value (treat null as a special case)
		if value_type == DataType.NULL:
			return value

		raise errors.SymbolTypeError(self.name, is_value=value, is_type=value_type, expected_type=self.result_type)

	def to_graphviz(self, digraph, *args, **kwargs):
		digraph.node(str(id(self)), "{}\nname={!r}".format(self.__class__.__name__, self.name))

class FunctionCallExpression(ExpressionBase):
	__slots__ = ('function', 'arguments',)
	def __init__(self, context, function, arguments):
		self.context = context
		self.function = function
		if self.function.result_type != DataType.UNDEFINED:
			function_type = self.function.result_type
			self._validate_function(function_type, arguments)
			self.result_type = function_type.return_type
		self.arguments = arguments

	@classmethod
	def build(cls, context, function, arguments):
		return cls(context, function.build(), tuple(argument.build() for argument in arguments)).reduce()

	def reduce(self):
		if not _is_reduced(self.function, *self.arguments):
			return self
		return LiteralExpressionBase.from_value(self.context, self.evaluate(None))

	def evaluate(self, thing):
		function = self.function.evaluate(thing)
		if not callable(function):
			raise errors.EvaluationError('data type mismatch (not a callable value)')
		arguments = tuple(argument.evaluate(thing) for argument in self.arguments)
		function_name = '<unknown>'
		if self.function.result_type != DataType.UNDEFINED:
			function_type = self.function.result_type
			function_name = function_type.value_name
			self._validate_function(function_type, arguments)
		elif hasattr(function, '__name__'):
			function_name = function.__name__ + '?'
		try:
			result = function(*arguments)
		except errors.FunctionCallError as error:
			error.function_name = function_name
			raise error
		except Exception as error:
			raise errors.FunctionCallError('function call failed', error=error, function_name=function_name) from None
		result = self._new_value(result)
		if not DataType.is_compatible(DataType.from_value(result), self.result_type):
			raise errors.FunctionCallError('function call failed (data type mismatch on returned value)', function_name=function_name)
		return result

	def _validate_function(self, function_type, arguments):
		if not isinstance(function_type, DataType.FUNCTION.__class__):
			raise errors.EvaluationError('data type mismatch (not a callable value)')
		if function_type.minimum_arguments is not DataType.UNDEFINED:
			if len(arguments) < function_type.minimum_arguments:
				raise errors.FunctionCallError(
					"expected at least {} positional arguments".format(function_type.minimum_arguments),
					function_name=function_type.value_name
				)
		if function_type.argument_types is not DataType.UNDEFINED:
			if len(arguments) > len(function_type.argument_types):
				raise errors.FunctionCallError(
					"expected at most {} positional arguments".format(len(function_type.argument_types)),
					function_name=function_type.value_name
				)
			for pos, (arg1, arg2_type) in enumerate(zip(arguments, function_type.argument_types), 1):
				if isinstance(arg1, ExpressionBase):
					arg1_type = arg1.result_type
				else:
					arg1_type = DataType.from_value(arg1)
				if not DataType.is_compatible(arg1_type, arg2_type):
					raise errors.FunctionCallError(
						"data type mismatch (argument #{})".format(pos),
						function_name=function_type.value_name
					)

	def to_graphviz(self, digraph, *args, **kwargs):
		super(FunctionCallExpression, self).to_graphviz(digraph, *args, **kwargs)
		self.function.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.function)), label='function')
		for idx, argument in enumerate(self.arguments, 1):
			argument.to_graphviz(digraph, *args, **kwargs)
			digraph.edge(str(id(self)), str(id(argument)), label="argument #{}".format(idx))

class TernaryExpression(ExpressionBase):
	"""
	A class for representing ternary expressions from the grammar text. These involve evaluating :py:attr:`.condition`
	before evaluating either :py:attr:`.case_true` or :py:attr:`.case_false` based on the results.
	"""
	def __init__(self, context, condition, case_true, case_false):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param condition: The condition expression whose evaluation determines whether the *case_true* or *case_false*
			expression is evaluated.
		:param case_true: The expression that's evaluated when *condition* is True.
		:param case_false:The expression that's evaluated when *condition* is False.
		"""
		self.context = context
		self.condition = condition
		self.case_true = case_true
		self.case_false = case_false
		if self.case_true.result_type == self.case_false.result_type:
			self.result_type = self.case_true.result_type
		elif isinstance(self.case_true.result_type, DataType.ARRAY.__class__) and isinstance(self.case_false.result_type, DataType.ARRAY.__class__):
			self.result_type = DataType.ARRAY
		# todo: the other compound types should be checked here as well.

	@classmethod
	def build(cls, context, condition, case_true, case_false):
		return cls(context, condition.build(), case_true.build(), case_false.build()).reduce()

	def evaluate(self, thing):
		case = (self.case_true if self.condition.evaluate(thing) else self.case_false)
		return case.evaluate(thing)

	def reduce(self):
		if not _is_reduced(self.condition):
			return self
		reduced_condition = bool(self.condition.value)
		return self.case_true.reduce() if reduced_condition else self.case_false.reduce()

	def to_graphviz(self, digraph, *args, **kwargs):
		super(TernaryExpression, self).to_graphviz(digraph, *args, **kwargs)
		self.condition.to_graphviz(digraph, *args, **kwargs)
		self.case_true.to_graphviz(digraph, *args, **kwargs)
		self.case_false.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.condition)), label='condition')
		digraph.edge(str(id(self)), str(id(self.case_true)), label='true case')
		digraph.edge(str(id(self)), str(id(self.case_false)), label='false case')

class UnaryExpression(ExpressionBase):
	"""
	A class for representing unary expressions from the grammar text. These involve a single operator on the left side.
	"""
	def __init__(self, context, type_, right):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param str type_: The grammar type of operator to the left of the expression.
		:param right: The expression to the right of the operator.
		:type right: :py:class:`~.ExpressionBase`
		"""
		self.context = context
		type_ = type_.lower()
		self.type = type_
		if type_ == 'not':
			self.result_type = DataType.BOOLEAN
		elif type_ == 'uminus':
			self.result_type = right.result_type
		else:
			raise ValueError('unknown unary expression type')
		self._evaluator = getattr(self, '_op_' + type_)
		self.right = right

	@classmethod
	def build(cls, context, type_, right):
		return cls(context, type_, right.build()).reduce()

	def __repr__(self):
		return "<{} type={!r} >".format(self.__class__.__name__, self.type)

	def evaluate(self, thing):
		return self._evaluator(thing)

	def __op(self, op, thing):
		return op(self.right.evaluate(thing))

	_op_not = functools.partialmethod(__op, operator.not_)

	def __op_arithmetic(self, op, thing):
		right = self.right.evaluate(thing)
		if not is_numeric(right) and not isinstance(right, datetime.timedelta):
			raise errors.EvaluationError('data type mismatch (not a numeric or timedelta value)')
		return op(right)

	_op_uminus = functools.partialmethod(__op_arithmetic, operator.neg)

	def reduce(self):
		type_ = self.type.lower()
		if not _is_reduced(self.right):
			return self
		if type_ == 'not':
			return BooleanExpression(self.context, self.evaluate(None))
		elif type_ == 'uminus':
			if isinstance(self.right, FloatExpression):
				return FloatExpression(self.context, self.evaluate(None))
			elif isinstance(self.right, TimedeltaExpression):
				return TimedeltaExpression(self.context, self.evaluate(None))
			raise errors.EvaluationError('data type mismatch (not a float or timedelta expression)')

	def to_graphviz(self, digraph, *args, **kwargs):
		digraph.node(str(id(self)), "{}\ntype={!r}".format(self.__class__.__name__, self.type.lower()))
		self.right.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.right)))
