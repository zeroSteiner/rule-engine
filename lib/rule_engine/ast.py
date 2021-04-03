#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast.py
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
import re

from . import errors
from .suggestions import suggest_symbol
from .types import *

import dateutil.parser

def _assert_is_integer_number(*values):
	if not all(map(is_integer_number, values)):
		raise errors.EvaluationError('data type mismatch (not an integer number)')

def _assert_is_natural_number(*values):
	if not all(map(is_natural_number, values)):
		raise errors.EvaluationError('data type mismatch (not a natural number)')

def _assert_is_numeric(*values):
	if not all(map(is_numeric, values)):
		raise errors.EvaluationError('data type mismatch (not a numeric value)')

def _is_reduced(*values):
	"""
	Check if the ast expression *value* is a literal expression and if it is a compound datatype, that all of it's
	members are reduced literals. A value that causes this to evaluate to True for is able to be evaluated without a
	*thing*.
	"""
	return all((isinstance(value, LiteralExpressionBase) and value.is_reduced) for value in values)

def _iterable_member_value_type(value):
	value = (
		member.result_type if isinstance(member, ExpressionBase) else member for member in value
	)
	return iterable_member_value_type(value)

class Assignment(object):
	"""An internal assignment where by a symbol is populated with a value of the specified type."""
	__slots__ = ('name', 'value', 'value_type')
	def __init__(self, name, *, value=errors.UNDEFINED, value_type=None):
		"""
		:param str name: The symbol name that the assignment is defining.
		:param value: The value of the assignment.
		:param value_type: The data type of the assignment.
		:type value_type: :py:class:`~.DataType`
		"""
		self.name = name
		self.value = value
		if value is not errors.UNDEFINED and value_type is not None:
			value_type = DataType.from_value(value)
		self.value_type = value_type

	def __repr__(self):
		return "<{} name={!r} value={!r} value_type={!r} >".format(self.__class__.__name__, self.name, self.value, self.value_type)

class ASTNodeBase(object):
	def to_graphviz(self, digraph):
		digraph.node(str(id(self)), self.__class__.__name__)

	@classmethod
	def build(cls, *args, **kwargs):
		return cls(*args, **kwargs).reduce()

	def evaluate(self, thing):
		"""
		Evaluate this AST node and all applicable children nodes.

		:param thing: The object to use for symbol resolution.
		:return: The result of the evaluation as a native Python type.
		"""
		raise NotImplementedError()

	def reduce(self):
		"""
		Reduce this expression into a smaller subset of nodes. If the expression can not be reduced, then return an
		instance of itself, otherwise return a reduced :py:class:`.ExpressionBase` to replace it.

		:return: Either a reduced version of this node or itself.
		:rtype: :py:class:`.ExpressionBase`
		"""
		return self

################################################################################
# Base Expression Classes
################################################################################
class ExpressionBase(ASTNodeBase):
	__slots__ = ('context',)
	result_type = DataType.UNDEFINED
	"""The data type of the result of successful evaluation."""
	def __repr__(self):
		return "<{0} >".format(self.__class__.__name__)

class LiteralExpressionBase(ExpressionBase):
	"""A base class for representing literal values from the grammar text."""
	__slots__ = ('value',)
	is_reduced = True
	def __init__(self, context, value):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param value: The native Python value.
		"""
		self.context = context
		if not isinstance(value, self.result_type.python_type) and self.result_type.is_scalar:
			raise TypeError("__init__ argument 2 must be {}, not {}".format(self.result_type.python_type.__name__, type(value).__name__))
		self.value = value

	def __repr__(self):
		return "<{0} value={1!r} >".format(self.__class__.__name__, self.value)

	@classmethod
	def from_value(cls, context, value):
		"""
		Create a Literal Expression instance to represent the specified *value*.

		.. versionadded:: 2.0.0

		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param value: The value to represent as a Literal Expression.
		:return: A subclass of :py:class:`~.LiteralExpressionBase` specific to the type of *value*.
		"""
		datatype = DataType.from_value(value)
		for subclass in cls.__subclasses__():
			if DataType.is_compatible(subclass.result_type, datatype):
				break
		else:
			raise errors.EngineError("can not create literal expression from python value: {!r}".format(value))
		if datatype.is_compound:
			if isinstance(datatype, DataType.ARRAY.__class__) or isinstance(datatype, DataType.SET.__class__):
				value = datatype.python_type(cls.from_value(context, v) for v in value)
			elif isinstance(datatype, DataType.MAPPING.__class__):
				value = tuple((cls.from_value(context, k), cls.from_value(context, v)) for k, v in value.items())
		else:
			value = coerce_value(value)
		return subclass(context, value)

	def evaluate(self, thing):
		return self.value

	def to_graphviz(self, digraph, *args, **kwargs):
		if self.result_type.is_compound:
			digraph.node(str(id(self)), self.__class__.__name__)
		else:
			digraph.node(str(id(self)), "{}\nvalue={!r}".format(self.__class__.__name__, self.value))

################################################################################
# Literal Expressions
################################################################################
class _CollectionMixin(object):
	def evaluate(self, thing):
		return self.result_type.python_type(member.evaluate(thing) for member in self.value)

	@property
	def is_reduced(self):
		return _is_reduced(*self.value)

	def to_graphviz(self, digraph, *args, **kwargs):
		super(_CollectionMixin, self).to_graphviz(digraph, *args, **kwargs)
		for member in self.value:
			member.to_graphviz(digraph, *args, **kwargs)
			digraph.edge(str(id(self)), str(id(member)))

class ArrayExpression(_CollectionMixin, LiteralExpressionBase):
	"""Literal array expressions containing 0 or more sub-expressions."""
	result_type = DataType.ARRAY
	def __init__(self, *args, **kwargs):
		super(ArrayExpression, self).__init__(*args, **kwargs)
		self.result_type = DataType.ARRAY(value_type=_iterable_member_value_type(self.value))

	@classmethod
	def build(cls, context, value):
		return cls(context, [member.build() for member in value])

class BooleanExpression(LiteralExpressionBase):
	"""Literal boolean expressions representing True or False."""
	result_type = DataType.BOOLEAN

class DatetimeExpression(LiteralExpressionBase):
	"""
	Literal datetime expressions representing a specific point in time. This expression type always evaluates to true.
	"""
	result_type = DataType.DATETIME
	@classmethod
	def from_string(cls, context, string):
		try:
			dt = dateutil.parser.isoparse(string)
		except ValueError:
			raise errors.DatetimeSyntaxError('invalid datetime', string)
		if dt.tzinfo is None:
			dt = dt.replace(tzinfo=context.default_timezone)
		return cls(context, dt)

class FloatExpression(LiteralExpressionBase):
	"""Literal float expressions representing numerical values."""
	result_type = DataType.FLOAT
	def __init__(self, context, value, **kwargs):
		value = coerce_value(value)
		super(FloatExpression, self).__init__(context, value, **kwargs)

class MappingExpression(LiteralExpressionBase):
	"""Literal mapping expression representing a set of associations between keys and values."""
	result_type = DataType.MAPPING
	def __init__(self, context, value, **kwargs):
		if isinstance(value, dict):
			value = tuple(value.items())
		super(MappingExpression, self).__init__(context, value, **kwargs)
		self.result_type = DataType.MAPPING(
			key_type=_iterable_member_value_type(key for key, _ in self.value),
			value_type=_iterable_member_value_type(value for _, value in self.value)
		)

	@classmethod
	def build(cls, context, value):
		value = collections.OrderedDict(value)
		value = collections.OrderedDict((k.build(), v.build()) for k, v in value.items())
		return cls(context, value)

	def evaluate(self, thing):
		mapping = collections.OrderedDict()
		for key, value in self.value:
			key = key.evaluate(thing)
			key_type = DataType.from_value(key)
			if key_type.is_compound and not isinstance(key_type, DataType.ARRAY.__class__):
				raise errors.EngineError("the {} data type may not be used for mapping keys".format(key_type.name))
			mapping[key] = value
		# defer value evaluation to avoid evaluating values of duplicate keys
		for key, value in mapping.items():
			mapping[key] = value.evaluate(thing)
		return mapping

	@property
	def is_reduced(self):
		return all(_is_reduced(key, value) for key, value in self.value)

class NullExpression(LiteralExpressionBase):
	"""Literal null expressions representing null values. This expression type always evaluates to false."""
	result_type = DataType.NULL
	def __init__(self, context, value=None):
		# all of the literal expressions take a value
		if value is not None:
			raise TypeError('value must be None')
		super(NullExpression, self).__init__(context, value=None)

class SetExpression(_CollectionMixin, LiteralExpressionBase):
	"""Literal set expressions containing 0 or more sub-expressions."""
	result_type = DataType.SET
	def __init__(self, *args, **kwargs):
		super(SetExpression, self).__init__(*args, **kwargs)
		self.result_type = DataType.SET(value_type=_iterable_member_value_type(self.value))

	@classmethod
	def build(cls, context, value):
		value = set(member.build() for member in value)
		return cls(context, value)

class StringExpression(LiteralExpressionBase):
	"""Literal string expressions representing an array of characters."""
	result_type = DataType.STRING

################################################################################
# Left-Operator-Right Expressions
################################################################################
class LeftOperatorRightExpressionBase(ExpressionBase):
	"""
	A base class for representing complex expressions composed of a left side and a right side, separated by an
	operator.
	"""
	compatible_types = (DataType.ARRAY, DataType.BOOLEAN, DataType.DATETIME, DataType.FLOAT, DataType.MAPPING, DataType.NULL, DataType.SET, DataType.STRING)
	"""
	A tuple containing the compatible data types that the left and right expressions must return. This can for example
	be used to indicate that arithmetic operations are compatible with :py:attr:`~.DataType.FLOAT` but not
	:py:attr:`~.DataType.STRING` values.
	"""
	result_type = DataType.BOOLEAN
	def __init__(self, context, type_, left, right):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param str type_: The grammar type of operator at the center of the expression. Subclasses must define operator
			methods to handle evaluation based on this value.
		:param left: The expression to the left of the operator.
		:type left: :py:class:`.ExpressionBase`
		:param right: The expression to the right of the operator.
		:type right: :py:class:`.ExpressionBase`
		"""
		self.context = context
		type_ = type_.lower()
		self.type = type_
		self._evaluator = getattr(self, '_op_' + type_, None)
		if self._evaluator is None:
			raise errors.EngineError('unsupported operator: ' + type_)
		self._assert_type_is_compatible(left)
		self.left = left
		self._assert_type_is_compatible(right)
		self.right = right

	@classmethod
	def build(cls, context, type_, left, right):
		return cls(context, type_, left.build(), right.build()).reduce()

	def _assert_type_is_compatible(self, value):
		if value.result_type == DataType.UNDEFINED:
			return
		if any(DataType.is_compatible(dt, value.result_type) for dt in self.compatible_types):
			return
		raise errors.EvaluationError('data type mismatch')

	def __repr__(self):
		return "<{} type={!r} >".format(self.__class__.__name__, self.type)

	def evaluate(self, thing):
		return self._evaluator(thing)

	def reduce(self):
		if not _is_reduced(self.left, self.right):
			return self
		return LiteralExpressionBase.from_value(self.context, self.evaluate(None))

	def to_graphviz(self, digraph, *args, **kwargs):
		digraph.node(str(id(self)), "{}\ntype={!r}".format(self.__class__.__name__, self.type))
		self.left.to_graphviz(digraph, *args, **kwargs)
		self.right.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.left)), label='left')
		digraph.edge(str(id(self)), str(id(self.right)), label='right')

class ArithmeticExpression(LeftOperatorRightExpressionBase):
	"""A class for representing arithmetic expressions from the grammar text such as addition and subtraction."""
	compatible_types = (DataType.FLOAT,)
	result_type = DataType.FLOAT
	def __op_arithmetic(self, op, thing):
		left_value = self.left.evaluate(thing)
		_assert_is_numeric(left_value)
		right_value = self.right.evaluate(thing)
		_assert_is_numeric(right_value)
		return op(left_value, right_value)

	_op_add  = functools.partialmethod(__op_arithmetic, operator.add)
	_op_sub  = functools.partialmethod(__op_arithmetic, operator.sub)
	_op_fdiv = functools.partialmethod(__op_arithmetic, operator.floordiv)
	_op_tdiv = functools.partialmethod(__op_arithmetic, operator.truediv)
	_op_mod  = functools.partialmethod(__op_arithmetic, operator.mod)
	_op_mul  = functools.partialmethod(__op_arithmetic, operator.mul)
	_op_pow  = functools.partialmethod(__op_arithmetic, operator.pow)

class BitwiseExpression(LeftOperatorRightExpressionBase):
	"""
	A class for representing bitwise arithmetic expressions from the grammar text such as XOR and shifting operations.
	"""
	compatible_types = (DataType.FLOAT, DataType.SET)
	result_type = DataType.UNDEFINED
	def __init__(self, *args, **kwargs):
		super(BitwiseExpression, self).__init__(*args, **kwargs)
		# don't use DataType.is_compatible, because for sets the member type isn't important
		if self.left.result_type != DataType.UNDEFINED and self.right.result_type != DataType.UNDEFINED:
			if self.left.result_type.__class__ != self.right.result_type.__class__:
				raise errors.EvaluationError('data type mismatch')
		if self.left.result_type == DataType.FLOAT:
			if _is_reduced(self.left):
				_assert_is_natural_number(self.left.evaluate(None))
			self.result_type = DataType.FLOAT
		if self.right.result_type == DataType.FLOAT:
			if _is_reduced(self.right):
				_assert_is_natural_number(self.right.evaluate(None))
			self.result_type = DataType.FLOAT
		if isinstance(self.left.result_type, DataType.SET.__class__) or isinstance(self.right.result_type, DataType.SET.__class__):
			self.result_type = DataType.SET  # this discards the member type info

	def _op_bitwise(self, op, thing):
		left = self.left.evaluate(thing)
		if DataType.from_value(left) == DataType.FLOAT:
			return self._op_bitwise_float(op, thing, left)
		elif isinstance(DataType.from_value(left), DataType.SET.__class__):
			return self._op_bitwise_set(op, thing, left)
		raise errors.EvaluationError('data type mismatch')

	def _op_bitwise_float(self, op, thing, left):
		_assert_is_natural_number(left)
		right = self.right.evaluate(thing)
		_assert_is_natural_number(right)
		return coerce_value(op(int(left), int(right)))

	def _op_bitwise_set(self, op, thing, left):
		right = self.right.evaluate(thing)
		if not DataType.is_compatible(DataType.from_value(right), DataType.SET):
			raise errors.EvaluationError('data type mismatch')
		return op(left, right)

	_op_bwand = functools.partialmethod(_op_bitwise, operator.and_)
	_op_bwor  = functools.partialmethod(_op_bitwise, operator.or_)
	_op_bwxor = functools.partialmethod(_op_bitwise, operator.xor)

class BitwiseShiftExpression(BitwiseExpression):
	compatible_types = (DataType.FLOAT,)
	result_type = DataType.FLOAT
	def _op_bitwise_shift(self, *args, **kwargs):
		return self._op_bitwise(*args, **kwargs)
	_op_bwlsh = functools.partialmethod(_op_bitwise_shift, operator.lshift)
	_op_bwrsh = functools.partialmethod(_op_bitwise_shift, operator.rshift)

class LogicExpression(LeftOperatorRightExpressionBase):
	"""A class for representing logical expressions from the grammar text such as "and" and "or"."""
	def _op_and(self, thing):
		return bool(self.left.evaluate(thing) and self.right.evaluate(thing))

	def _op_or(self, thing):
		return bool(self.left.evaluate(thing) or self.right.evaluate(thing))

################################################################################
# Left-Operator-Right Comparison Expressions
################################################################################
class ComparisonExpression(LeftOperatorRightExpressionBase):
	"""A class for representing comparison expressions from the grammar text such as equality checks."""
	def _op_eq(self, thing):
		left_value = self.left.evaluate(thing)
		right_value = self.right.evaluate(thing)
		if type(left_value) is not type(right_value):
			return False
		return operator.eq(left_value, right_value)

	def _op_ne(self, thing):
		left_value = self.left.evaluate(thing)
		right_value = self.right.evaluate(thing)
		if type(left_value) is not type(right_value):
			return True
		return operator.ne(left_value, right_value)

class ArithmeticComparisonExpression(ComparisonExpression):
	"""
	A class for representing arithmetic comparison expressions from the grammar text such as less-than-or-equal-to and
	greater-than.
	"""
	compatible_types = (DataType.ARRAY, DataType.BOOLEAN, DataType.DATETIME, DataType.FLOAT, DataType.NULL, DataType.STRING)
	def __init__(self, *args, **kwargs):
		super(ArithmeticComparisonExpression, self).__init__(*args, **kwargs)
		if self.left.result_type != DataType.UNDEFINED and self.right.result_type != DataType.UNDEFINED:
			if self.left.result_type != self.right.result_type:
				raise errors.EvaluationError('data type mismatch')

	def __op_arithmetic(self, op, thing):
		left_value = self.left.evaluate(thing)
		right_value = self.right.evaluate(thing)
		return self.__op_arithmetic_values(op, left_value, right_value)

	def __op_arithmetic_arrays(self, op, left_value, right_value):
		for subleft_value, subright_value in zip(left_value, right_value):
			if self.__op_arithmetic_values(operator.ne, subleft_value, subright_value):
				return self.__op_arithmetic_values(op, subleft_value, subright_value)
		if len(left_value) != len(right_value):
			return self.__op_arithmetic_values(op, len(left_value), len(right_value))
		return op in (operator.ge, operator.le)

	def __op_arithmetic_values(self, op, left_value, right_value):
		if left_value is None and right_value is None:
			return op in (operator.ge, operator.le)
		elif isinstance(left_value, tuple) and isinstance(right_value, tuple):
			return self.__op_arithmetic_arrays(op, left_value, right_value)
		elif type(left_value) is not type(right_value):
			raise errors.EvaluationError('data type mismatch')
		return op(left_value, right_value)

	_op_ge = functools.partialmethod(__op_arithmetic, operator.ge)
	_op_gt = functools.partialmethod(__op_arithmetic, operator.gt)
	_op_le = functools.partialmethod(__op_arithmetic, operator.le)
	_op_lt = functools.partialmethod(__op_arithmetic, operator.lt)

class FuzzyComparisonExpression(ComparisonExpression):
	"""
	A class for representing regular expression comparison expressions from the grammar text such as search and does not
	match.
	"""
	compatible_types = (DataType.NULL, DataType.STRING)
	def __init__(self, *args, **kwargs):
		super(FuzzyComparisonExpression, self).__init__(*args, **kwargs)
		if isinstance(self.right, StringExpression):
			self._right = self._compile_regex(self.right.evaluate(None))

	def _compile_regex(self, regex):
		try:
			result = re.compile(regex, flags=self.context.regex_flags)
		except re.error as error:
			raise errors.RegexSyntaxError('invalid regular expression', error=error, value=regex) from None
		return result

	def __op_regex(self, regex_function, modifier, thing):
		left = self.left.evaluate(thing)
		if not isinstance(left, str) and left is not None:
			raise errors.EvaluationError('data type mismatch')
		if isinstance(self.right, StringExpression):
			regex = self._right
		else:
			regex = self.right.evaluate(thing)
			if isinstance(regex, str):
				regex = self._compile_regex(regex)
			elif regex is not None:
				raise errors.EvaluationError('data type mismatch')
		if left is None or regex is None:
			return not modifier(left, regex)
		match = getattr(regex, regex_function)(left)
		if match is not None:
			self.context._tls.regex_groups = coerce_value(match.groups())
		return modifier(match, None)

	_op_eq_fzm = functools.partialmethod(__op_regex, 'match', operator.is_not)
	_op_eq_fzs = functools.partialmethod(__op_regex, 'search', operator.is_not)
	_op_ne_fzm = functools.partialmethod(__op_regex, 'match', operator.is_)
	_op_ne_fzs = functools.partialmethod(__op_regex, 'search', operator.is_)

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
		assignment = Assignment(variable, value_type=getattr(iterable.result_type, 'iterable_type', DataType.UNDEFINED))
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
		if container.result_type == DataType.STRING:
			if member.result_type != DataType.UNDEFINED and member.result_type != DataType.STRING:
				raise errors.EvaluationError('data type mismatch')
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
		member_value = self.member.evaluate(thing)
		if DataType.from_value(container_value) == DataType.STRING:
			if DataType.from_value(member_value) != DataType.STRING:
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
	__slots__ = ('name', 'object', 'safe')
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
		if self.object.result_type != DataType.UNDEFINED:
			if not (self.object.result_type == DataType.NULL and safe):
				try:
					self.result_type = context.resolve_attribute_type(self.object.result_type, name)
				except errors.AttributeResolutionError as error:
					# this is necessary because MAPPING objects can have their keys accessed as attributes
					if not isinstance(self.object.result_type, DataType.MAPPING.__class__):
						raise error
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

		attribute_error = None
		try:
			value = self.context.resolve_attribute(thing, resolved_obj, self.name)
		except errors.AttributeResolutionError as error:
			attribute_error = error
		else:
			return coerce_value(value, verify_type=False)

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
		return coerce_value(value, verify_type=False)

	def reduce(self):
		if not _is_reduced(self.object):
			return self
		return LiteralExpressionBase.from_value(self.context, self.evaluate(None))

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
		if container.result_type == DataType.STRING:
			if not DataType.is_compatible(item.result_type, DataType.FLOAT):
				raise errors.EvaluationError('data type mismatch (not an integer number)')
			self.result_type = DataType.STRING
		# check against __class__ so the parent class is dynamic in case it changes in the future, what we're doing here
		# is explicitly checking if result_type is an array with out checking the value_type
		elif isinstance(container.result_type, DataType.ARRAY.__class__):
			if not DataType.is_compatible(item.result_type, DataType.FLOAT):
				raise errors.EvaluationError('data type mismatch (not an integer number)')
			self.result_type = container.result_type.value_type
		elif isinstance(container.result_type, DataType.MAPPING.__class__):
			if not (safe or DataType.is_compatible(item.result_type, container.result_type.key_type)):
				raise errors.LookupError(errors.UNDEFINED, errors.UNDEFINED)
			self.result_type = container.result_type.value_type
		elif isinstance(container.result_type, DataType.SET.__class__):
			raise errors.EvaluationError('data type mismatch (container is a set)')
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
		if isinstance(resolved_obj, (str, tuple)):
			_assert_is_integer_number(resolved_item)
			resolved_item = int(resolved_item)
		try:
			value = operator.getitem(resolved_obj, resolved_item)
		except (IndexError, KeyError):
			if self.safe:
				return None
			raise errors.LookupError(resolved_obj, resolved_item)
		return coerce_value(value, verify_type=False)

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
		if container.result_type == DataType.STRING:
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
		value = coerce_value(value, verify_type=False)
		if isinstance(value, datetime.datetime) and value.tzinfo is None:
			value = value.replace(tzinfo=self.context.default_timezone)

		# if the expected result type is undefined, return the value
		if self.result_type == DataType.UNDEFINED:
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

class Statement(ASTNodeBase):
	"""A class representing the top level statement of the grammar text."""
	__slots__ = ('context', 'expression')
	def __init__(self, context, expression):
		"""
		:param context: The context to use for evaluating the statement.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param expression: The top level expression of the statement.
		:type expression: :py:class:`~.ExpressionBase`
		"""
		self.context = context
		self.expression = expression

	@classmethod
	def build(cls, context, expression):
		return cls(context, expression.build()).reduce()

	def evaluate(self, thing):
		return self.expression.evaluate(thing)

	def to_graphviz(self, digraph, *args, **kwargs):
		super(Statement, self).to_graphviz(digraph, *args, **kwargs)
		self.expression.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.expression)))

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

	@classmethod
	def build(cls, context, condition, case_true, case_false):
		return cls(context, condition.build(), case_true.build(), case_false.build()).reduce()

	def evaluate(self, thing):
		case = (self.case_true if self.condition.evaluate(thing) else self.case_false)
		return case.evaluate(thing)

	def reduce(self):
		if _is_reduced(self.condition):
			reduced_condition = bool(self.condition.value)
		else:
			reduced_condition = self.condition.reduce()
			if reduced_condition is self.condition:
				return self
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
		self._evaluator = getattr(self, '_op_' + type_)
		self.result_type = {
			'not':    DataType.BOOLEAN,
			'uminus': DataType.FLOAT
		}[type_]
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
		_assert_is_numeric(right)
		return op(right)

	_op_uminus = functools.partialmethod(__op_arithmetic, operator.neg)

	def reduce(self):
		type_ = self.type.lower()
		if not _is_reduced(self.right):
			return self
		if type_ == 'not':
			return BooleanExpression(self.context, self.evaluate(None))
		elif type_ == 'uminus':
			if not isinstance(self.right, (FloatExpression,)):
				raise errors.EvaluationError('data type mismatch (not a float expression)')
			return FloatExpression(self.context, self.evaluate(None))

	def to_graphviz(self, digraph, *args, **kwargs):
		digraph.node(str(id(self)), "{}\ntype={!r}".format(self.__class__.__name__, self.type.lower()))
		self.right.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.right)))
