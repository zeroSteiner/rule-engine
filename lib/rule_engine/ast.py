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

import enum
import functools
import math
import operator
import re

from . import errors

def is_natural_number(value):
	"""
	Check whether *value* is a natural number (i.e. a whole, non-negative
	number). This can, for example, be used to check if a floating point number
	such as ``3.0`` can safely be converted to an integer without lose of
	information.

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is a natural number.
	:rtype: bool
	"""
	if not is_real_number(value):
		return False
	return math.floor(value) == value

def is_real_number(value):
	"""
	Check whether *value* is a real number (i.e. capable of being represented as
	a floating point value without lose of information). Despite being able to
	be represented as a float, ``NaN`` is not considered a real number for the
	purposes of this function.

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is a natural number.
	:rtype: bool
	"""
	if not isinstance(value, (int, float)):
		return False
	if isinstance(value, bool):
		return False
	if value == float('nan'):
		return False
	return True

def _assert_is_natural_number(value):
	if not is_natural_number(value):
		raise errors.EvaluationError('data type mismatch')

def _assert_is_real_number(value):
	if not is_real_number(value):
		raise errors.EvaluationError('data type mismatch')

class DataType(enum.Enum):
	"""
	A collection of constants representing the different supported data types.
	"""
	BOOLEAN = bool
	FLOAT = float
	STRING = str
	UNDEFINED = None
	"""
	Undefined values. This constant can be used to indicate that a particular
	symbol is valid, but it's data type is currently unknown.
	"""
	@classmethod
	def from_value(cls, value):
		"""
		Get the supported data type constant for the specified Python value. If
		the value can not be mapped to a supported data type, then a
		:py:exc:`TypeError` exception will be raised. This function will not
		return :py:attr:`.UNDEFINED`.

		:param value: The native Python type to retrieve the corresponding data
			type constant for.
		:return: One of the constants.
		"""
		if isinstance(value, bool):
			return cls.BOOLEAN
		elif isinstance(value, (float, int)):
			return cls.FLOAT
		elif isinstance(value, (str,)):
			return cls.STRING
		raise TypeError("can not map python type {0!r} to a compatible data type".format(type(value).__name__))

class ASTNodeBase(object):
	def to_graphviz(self, digraph):
		digraph.node(str(id(self)), self.__class__.__name__)

################################################################################
# Base Expression Classes
################################################################################
class ExpressionBase(ASTNodeBase):
	__slots__ = ('context',)
	result_type = DataType.UNDEFINED
	"""The data type of the result of successful evaluation."""
	def __repr__(self):
		return "<{0} >".format(self.__class__.__name__)

	def evaluate(self, thing):
		"""
		Evaluate this AST node and all applicable children nodes.

		:param thing: The object to use for symbol resolution.
		:return: The result of the evaluation as a native Python type.
		"""
		raise NotImplementedError()

	def reduce(self):
		"""
		Reduce this expression into a smaller subset of nodes. If the expression
		can not be reduced, then return an instance of itself, otherwise return
		a reduced :py:class:`.ExpressionBase` to replace it.

		:return: Either a reduced version of this node or itself.
		:rtype: :py:class:`.ExpressionBase`
		"""
		return self

class LiteralExpressionBase(ExpressionBase):
	"""A base class for representing literal values from the grammar text."""
	__slots__ = ('value',)
	def __init__(self, context, value):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param value: The native Python value.
		"""
		self.context = context
		self.value = self.result_type.value(value)

	def __repr__(self):
		return "<{0} value={1!r} >".format(self.__class__.__name__, self.value)

	def evaluate(self, thing):
		return self.value

################################################################################
# Literal Expressions
################################################################################
class BooleanExpression(LiteralExpressionBase):
	"""Literal boolean expressions representing True or False."""
	result_type = DataType.BOOLEAN

class FloatExpression(LiteralExpressionBase):
	"""Literal float expressions representing numerical values."""
	result_type = DataType.FLOAT

class StringExpression(LiteralExpressionBase):
	"""Literal string expressions representing an array of characters."""
	result_type = DataType.STRING

################################################################################
# Left-Operator-Right Expressions
################################################################################
class LeftOperatorRightExpressionBase(ExpressionBase):
	"""
	A base class for representing complex expressions composed of a left side
	and a right side, separated by an operator.
	"""
	compatible_types = (DataType.BOOLEAN, DataType.FLOAT, DataType.STRING)
	"""
	A tuple containing the compatible data types that the left and right
	expressions must return. This can for example be used to indicate that
	arithmetic operations are compatible with :py:attr:`~.DataType.FLOAT` but
	not :py:attr:`~.DataType.STRING` values.
	"""
	result_expression = BooleanExpression
	result_type = DataType.BOOLEAN
	def __init__(self, context, type_, left, right):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param str type_: The grammar type of operator at the center of the
			expression. Subclasses must define operator methods to handle
			evaluation based on this value.
		:param left: The expression to the left of the operator.
		:type left: :py:class:`.ExpressionBase`
		:param right: The expression to the right of the operator.
		:type right: :py:class:`.ExpressionBase`
		"""
		self.context = context
		self.type = type_
		self._evaluator = getattr(self, '_op_' + type_.lower(), None)
		if self._evaluator is None:
			raise errors.EngineError('unsupported operator: ' + type_)
		self.left = left
		if self.left.result_type is not DataType.UNDEFINED:
			if self.left.result_type not in self.compatible_types:
				raise errors.EvaluationError('data type mismatch')
		self.right = right
		if self.right.result_type is not DataType.UNDEFINED:
			if self.right.result_type not in self.compatible_types:
				raise errors.EvaluationError('data type mismatch')

	def evaluate(self, thing):
		return self._evaluator(thing)

	def reduce(self):
		if not isinstance(self.left, LiteralExpressionBase):
			return self
		if not isinstance(self.right, LiteralExpressionBase):
			return self
		return self.result_expression(self.context, self.evaluate(None))

	def to_graphviz(self, digraph, *args, **kwargs):
		super(LeftOperatorRightExpressionBase, self).to_graphviz(digraph, *args, **kwargs)
		self.left.to_graphviz(digraph, *args, **kwargs)
		self.right.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.left)))
		digraph.edge(str(id(self)), str(id(self.right)))

class ArithmeticExpression(LeftOperatorRightExpressionBase):
	"""
	A class for representing arithmetic expressions from the grammar text such
	as addition and subtraction.
	"""
	compatible_types = (DataType.FLOAT,)
	result_expression = FloatExpression
	result_type = DataType.FLOAT
	def __op_arithmetic(self, op, thing):
		left = self.left.evaluate(thing)
		_assert_is_real_number(left)
		right = self.right.evaluate(thing)
		_assert_is_real_number(right)
		return float(op(left, right))

	_op_add  = functools.partialmethod(__op_arithmetic, operator.add)
	_op_sub  = functools.partialmethod(__op_arithmetic, operator.sub)
	_op_fdiv = functools.partialmethod(__op_arithmetic, operator.floordiv)
	_op_tdiv = functools.partialmethod(__op_arithmetic, operator.truediv)
	_op_mod  = functools.partialmethod(__op_arithmetic, operator.mod)
	_op_mul  = functools.partialmethod(__op_arithmetic, operator.mul)
	_op_pow  = functools.partialmethod(__op_arithmetic, math.pow)

class BitwiseExpression(LeftOperatorRightExpressionBase):
	"""
	A class for representing bitwise arithmetic expressions from the grammar
	text such as XOR and shifting operations.
	"""
	compatible_types = (DataType.FLOAT,)
	result_expression = FloatExpression
	result_type = DataType.FLOAT
	def __init__(self, *args, **kwargs):
		super(BitwiseExpression, self).__init__(*args, **kwargs)
		if isinstance(self.left, LiteralExpressionBase):
			_assert_is_natural_number(self.left.evaluate(None))
		if isinstance(self.right, LiteralExpressionBase):
			_assert_is_natural_number(self.right.evaluate(None))

	def __op_bitwise(self, op, thing):
		left = self.left.evaluate(thing)
		_assert_is_natural_number(left)
		right = self.right.evaluate(thing)
		_assert_is_natural_number(right)
		return float(op(int(left), int(right)))

	_op_bwand = functools.partialmethod(__op_bitwise, operator.and_)
	_op_bwor  = functools.partialmethod(__op_bitwise, operator.or_)
	_op_bwxor = functools.partialmethod(__op_bitwise, operator.xor)
	_op_bwlsh = functools.partialmethod(__op_bitwise, operator.lshift)
	_op_bwrsh = functools.partialmethod(__op_bitwise, operator.rshift)

class LogicExpression(LeftOperatorRightExpressionBase):
	"""
	A class for representing logical expressions from the grammar text such as
	as "and" and "or".
	"""
	def _op_and(self, thing):
		return bool(self.left.evaluate(thing) and self.right.evaluate(thing))

	def _op_or(self, thing):
		return bool(self.left.evaluate(thing) or self.right.evaluate(thing))

################################################################################
# Left-Operator-Right Comparison Expressions
################################################################################
class ComparisonExpression(LeftOperatorRightExpressionBase):
	"""
	A class for representing comparison expressions from the grammar text such
	as equality checks.
	"""
	def __op_comparison(self, op, thing):
		return op(self.left.evaluate(thing), self.right.evaluate(thing))

	_op_eq = functools.partialmethod(__op_comparison, operator.eq)
	_op_ne = functools.partialmethod(__op_comparison, operator.ne)

class ArithmeticComparisonExpression(ComparisonExpression):
	"""
	A class for representing arithmetic comparison expressions from the grammar
	text such as less-than-or-equal-to and greater-than.
	"""
	compatible_types = (DataType.FLOAT,)
	def __op_arithmetic(self, op, thing):
		left = self.left.evaluate(thing)
		_assert_is_real_number(left)
		right = self.right.evaluate(thing)
		_assert_is_real_number(right)
		return op(int(left), int(right))

	_op_ge = functools.partialmethod(__op_arithmetic, operator.ge)
	_op_gt = functools.partialmethod(__op_arithmetic, operator.gt)
	_op_le = functools.partialmethod(__op_arithmetic, operator.le)
	_op_lt = functools.partialmethod(__op_arithmetic, operator.lt)

class RegexComparisonExpression(ComparisonExpression):
	"""
	A class for representing regular expression comparison expressions from the
	grammar text such as search and does not match.
	"""
	compatible_types = (DataType.STRING,)
	def __init__(self, *args, **kwargs):
		super(RegexComparisonExpression, self).__init__(*args, **kwargs)
		if isinstance(self.right, StringExpression):
			self._right = re.compile(self.right.evaluate(None), flags=self.context.regex_flags)

	def __op_regex(self, regex_function, modifier, thing):
		left_string = self.left.evaluate(thing)
		if not isinstance(left_string, str):
			raise errors.EvaluationError('data type mismatch')
		if isinstance(self.right, StringExpression):
			regex = self._right
		else:
			regex = self.right.evaluate(thing)
			if not isinstance(regex, str):
				raise errors.EvaluationError('data type mismatch')
			regex = re.compile(self.right, flags=self.context.regex_flags)
		match = getattr(regex, regex_function)(left_string)
		return modifier(match, None)

	_op_eq_rem = functools.partialmethod(__op_regex, 'match', operator.is_not)
	_op_eq_res = functools.partialmethod(__op_regex, 'search', operator.is_not)
	_op_ne_rem = functools.partialmethod(__op_regex, 'match', operator.is_)
	_op_ne_res = functools.partialmethod(__op_regex, 'search', operator.is_)

################################################################################
# Miscellaneous Expressions
################################################################################
class SymbolExpression(ExpressionBase):
	"""
	A class representing a symbol name to be resolved at evaluation time with
	the help of a :py:class:`~rule_engine.engine.Context` object.
	"""
	__slots__ = ('name', 'result_type')
	def __init__(self, context, name):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param str name: The name of the symbol. This will be resolved with a
			given context object on the specified *thing*.
		"""
		self.context = context
		self.name = name
		type_hint = context.resolve_type(name)
		if type_hint is not None:
			self.result_type = type_hint

	def __repr__(self):
		return "<{0} name={1!r} >".format(self.__class__.__name__, self.name)

	def evaluate(self, thing):
		value = self.context.resolve(thing, self.name)
		# use DataType.from_value to raise a TypeError if value is not of a
		# compatible data type
		DataType.from_value(value)
		return value

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

	def evaluate(self, thing):
		return self.expression.evaluate(thing)

	def to_graphviz(self, digraph, *args, **kwargs):
		super(Statement, self).to_graphviz(digraph, *args, **kwargs)
		self.expression.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.expression)))

class TernaryExpression(ExpressionBase):
	"""
	A class for representing ternary expressions from the grammar text. These
	involve evaluating :py:attr:`.condition` before evaluating either
	:py:attr:`.case_true` or :py:attr:`.case_false` based on the results.
	"""
	def __init__(self, context, condition, case_true, case_false):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param condition: The condition expression whose evaluation determines
			whether the *case_true* or *case_false* expression is evaluated.
		:param case_true: The expression that's evaluated when *condition* is
			True.
		:param case_false:The expression that's evaluated when *condition* is
			False.
		"""
		self.context = context
		self.condition = condition
		self.case_true = case_true
		self.case_false = case_false

	def evaluate(self, thing):
		case = (self.case_true if self.condition.evaluate(thing) else self.case_false)
		return case.evaluate(thing)

	def reduce(self):
		if isinstance(self.condition, LiteralExpressionBase):
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
		digraph.edge(str(id(self)), str(id(self.condition)))
		digraph.edge(str(id(self)), str(id(self.case_true)))
		digraph.edge(str(id(self)), str(id(self.case_false)))

class UnaryExpression(ExpressionBase):
	def __init__(self, context, type_, right):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param str type_: The grammar type of operator to the left of the
			expression.
		:param right: The expression to the right of the operator.
		:type right: :py:class:`~.ExpressionBase`
		"""
		self.context = context
		self.type = type_
		self._evaluator = getattr(self, '_op_' + type_.lower())
		self.right = right

	def evaluate(self, thing):
		return self._evaluator(thing)

	def __op(self, op, thing):
		return op(self.right.evaluate(thing))

	_op_not = functools.partialmethod(__op, operator.not_)

	def __op_arithmetic(self, op, thing):
		right = self.right.evaluate(thing)
		_assert_is_real_number(right)
		return op(right)

	_op_uminus = functools.partialmethod(__op_arithmetic, operator.neg)

	def reduce(self):
		type_ = self.type.lower()
		if type_ not in ('not', 'uminus'):
			raise NotImplementedError()
		if not isinstance(self.right, LiteralExpressionBase):
			return self
		if type_ == 'not':
			return BooleanExpression(self.context, self.evaluate(None))
		elif type_ == 'uminus':
			if not isinstance(self.right, (FloatExpression,)):
				raise errors.EvaluationError('data type mismatch')
			return FloatExpression(self.context, self.evaluate(None))

	def to_graphviz(self, digraph, *args, **kwargs):
		super(UnaryExpression, self).to_graphviz(digraph, *args, **kwargs)
		self.right.to_graphviz(digraph, *args, **kwargs)
		digraph.edge(str(id(self)), str(id(self.right)))
