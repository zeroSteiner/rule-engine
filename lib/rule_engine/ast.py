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
	a floating point value with lose of information.

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is a natural number.
	:rtype: bool
	"""
	if not isinstance(value, (int, float)):
		return False
	if isinstance(value, bool):
		return False
	return True

def _assert_is_natural_number(value):
	if not is_natural_number(value):
		raise errors.EvaluationError('data type mismatch')

def _assert_is_real_number(value):
	if not is_real_number(value):
		raise errors.EvaluationError('data type mismatch')

class DataType(enum.Enum):
	BOOLEAN = bool
	FLOAT = float
	STRING = str
	UNDEFINED = None
	@classmethod
	def from_value(cls, value):
		if isinstance(value, bool):
			return cls.BOOLEAN
		elif isinstance(value, (float, int)):
			return cls.FLOAT
		elif isinstance(value, (str,)):
			return cls.STRING
		raise TypeError("can not map python type {0!r} to a compatible data type".format(type(value).__name__))

################################################################################
# Base Expression Classes
################################################################################
class ExpressionBase(object):
	result_type = DataType.UNDEFINED
	def __repr__(self):
		return "<{0} >".format(self.__class__.__name__)

	def evaluate(self, context, thing):
		raise NotImplementedError()

	def reduce(self):
		return self

class LeftOperatorRightExpressionBase(ExpressionBase):
	__slots__ = ('_evaluator', 'type', 'left', 'right')
	compatible_types = (DataType.BOOLEAN, DataType.FLOAT, DataType.STRING)
	result_type = DataType.BOOLEAN
	_reduce_literals = ()
	def __init__(self, type_, left, right):
		self.type = type_
		self._evaluator = getattr(self, '_op_' + type_.lower())
		self.left = left
		if self.left.result_type is not DataType.UNDEFINED:
			if self.left.result_type not in self.compatible_types:
				raise errors.EvaluationError('data type mismatch')
		self.right = right
		if self.right.result_type is not DataType.UNDEFINED:
			if self.right.result_type not in self.compatible_types:
				raise errors.EvaluationError('data type mismatch')

	def evaluate(self, context, thing):
		return self._evaluator(context, thing)

	def reduce(self):
		if not isinstance(self.left, LiteralExpression):
			return self
		if not isinstance(self.left, self._reduce_literals):
			raise errors.EvaluationError('data type mismatch')
		if not isinstance(self.right, LiteralExpression):
			return self
		if not isinstance(self.right, self._reduce_literals):
			raise errors.EvaluationError('data type mismatch')
		primary_literal = self._reduce_literals[0]
		return primary_literal(self.evaluate(None, None))

################################################################################
# Literal Expressions
################################################################################
class LiteralExpression(ExpressionBase):
	__slots__ = ('value',)
	def __init__(self, value):
		self.value = self.result_type.value(value)

	def __repr__(self):
		return "<{0} value={1!r} >".format(self.__class__.__name__, self.value)

	def evaluate(self, context, thing):
		return self.value

class BooleanExpression(LiteralExpression):
	result_type = DataType.BOOLEAN

class FloatExpression(LiteralExpression):
	result_type = DataType.FLOAT

class StringExpression(LiteralExpression):
	result_type = DataType.STRING

################################################################################
# Left-Operator-Right Expressions
################################################################################
class ArithmeticExpression(LeftOperatorRightExpressionBase):
	compatible_types = (DataType.FLOAT,)
	result_type = DataType.FLOAT
	_reduce_literals = (FloatExpression,)
	def __op_arithmetic(self, op, context, thing):
		left = self.left.evaluate(context, thing)
		_assert_is_real_number(left)
		right = self.right.evaluate(context, thing)
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
	compatible_types = (DataType.FLOAT,)
	result_type = DataType.FLOAT
	_reduce_literals = (FloatExpression,)
	def __op_bitwise(self, op, context, thing):
		left = self.left.evaluate(context, thing)
		_assert_is_natural_number(left)
		right = self.right.evaluate(context, thing)
		_assert_is_natural_number(right)
		return float(op(int(left), int(right)))

	_op_bwand = functools.partialmethod(__op_bitwise, operator.and_)
	_op_bwor  = functools.partialmethod(__op_bitwise, operator.or_)
	_op_bwxor = functools.partialmethod(__op_bitwise, operator.xor)
	_op_bwlsh = functools.partialmethod(__op_bitwise, operator.lshift)
	_op_bwrsh = functools.partialmethod(__op_bitwise, operator.rshift)

class ComparisonExpression(LeftOperatorRightExpressionBase):
	_reduce_literals = (BooleanExpression, FloatExpression, StringExpression)
	def __op_arithmetic(self, op, context, thing):
		left = self.left.evaluate(context, thing)
		_assert_is_real_number(left)
		right = self.right.evaluate(context, thing)
		_assert_is_real_number(right)
		return op(int(left), int(right))

	_op_ge = functools.partialmethod(__op_arithmetic, operator.ge)
	_op_gt = functools.partialmethod(__op_arithmetic, operator.gt)
	_op_le = functools.partialmethod(__op_arithmetic, operator.le)
	_op_lt = functools.partialmethod(__op_arithmetic, operator.lt)

	def __op_comparison(self, op, context, thing):
		left = self.left.evaluate(context, thing)
		right = self.right.evaluate(context, thing)
		return op(left, right)

	_op_eq = functools.partialmethod(__op_comparison, operator.eq)
	_op_ne = functools.partialmethod(__op_comparison, operator.ne)

	def __op_regex(self, regex_function, modifier, context, thing):
		left_string = self.left.evaluate(context, thing)
		if not isinstance(left_string, str):
			raise errors.EvaluationError('data type mismatch')
		right_regex = self.right.evaluate(context, thing)
		if not isinstance(right_regex, str):
			raise errors.EvaluationError('data type mismatch')
		match = regex_function(right_regex, left_string, flags=context.regex_flags)
		return modifier(match, None)

	_op_eq_rem = functools.partialmethod(__op_regex, re.match, operator.is_not)
	_op_eq_res = functools.partialmethod(__op_regex, re.search, operator.is_not)
	_op_ne_rem = functools.partialmethod(__op_regex, re.match, operator.is_)
	_op_ne_res = functools.partialmethod(__op_regex, re.search, operator.is_)

class LogicExpression(LeftOperatorRightExpressionBase):
	_reduce_literals = (BooleanExpression, FloatExpression, StringExpression)
	def _op_and(self, context, thing):
		return bool(self.left.evaluate(context, thing) and self.right.evaluate(context, thing))

	def _op_or(self, context, thing):
		return bool(self.left.evaluate(context, thing) or self.right.evaluate(context, thing))

################################################################################
# Miscellaneous Expressions
################################################################################
class TernaryExpression(ExpressionBase):
	__slots__ = ('condition', 'case_true', 'case_false')
	def __init__(self, condition, case_true, case_false):
		self.condition = condition
		self.case_true = case_true
		self.case_false = case_false

	def evaluate(self, context, thing):
		case = (self.case_true if self.condition.evaluate(context, thing) else self.case_false)
		return case.evaluate(context, thing)

	def reduce(self):
		if isinstance(self.condition, LiteralExpression):
			reduced_condition = bool(self.condition.value)
		else:
			reduced_condition = self.condition.reduce()
			if reduced_condition is self.condition:
				return self
		return self.case_true.reduce() if reduced_condition else self.case_false.reduce()

class UnaryExpression(ExpressionBase):
	__slots__ = ('_evaluator', 'type', 'right')
	def __init__(self, type_, right):
		self.type = type_
		self._evaluator = getattr(self, '_op_' + type_.lower())
		self.right = right

	def evaluate(self, context, thing):
		return self._evaluator(context, thing)

	def __op(self, op, context, thing):
		right = self.right.evaluate(context, thing)
		_assert_is_real_number(right)
		return op(right)

	_op_uminus = functools.partialmethod(__op, operator.neg)

	def reduce(self):
		if not self.type.lower() == 'uminus':
			raise NotImplementedError()
		if not isinstance(self.right, LiteralExpression):
			return self
		if not isinstance(self.right, (FloatExpression,)):
			raise errors.EvaluationError('data type mismatch')
		return FloatExpression(self.evaluate(None, None))

class SymbolExpression(ExpressionBase):
	__slots__ = ('name',)
	def __init__(self, name, type_hint=None):
		self.name = name
		if type_hint is not None:
			self.result_type = type_hint

	def __repr__(self):
		return "<{0} name={1!r} >".format(self.__class__.__name__, self.name)

	def evaluate(self, context, thing):
		return context.resolve(thing, self.name)

class Statement(object):
	__slots__ = ('expression',)
	def __init__(self, expression):
		self.expression = expression

	def evaluate(self, context, thing):
		return self.expression.evaluate(context, thing)
