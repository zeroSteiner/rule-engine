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

import datetime
import enum
import functools
import math
import operator
import re

from . import errors

import dateutil.parser

NONE_TYPE = type(None)

def is_natural_number(value):
	"""
	Check whether *value* is a natural number (i.e. a whole, non-negative
	number). This can, for example, be used to check if a floating point number
	such as ``3.0`` can safely be converted to an integer without loss of
	information.

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is a natural number.
	:rtype: bool
	"""
	if not is_real_number(value):
		return False
	if math.floor(value) != value:
		return False
	if value < 0:
		return False
	return True

def is_real_number(value):
	"""
	Check whether *value* is a real number (i.e. capable of being represented as
	a floating point value without loss of information as well as being finite).
	Despite being able to be represented as a float, ``NaN`` is not considered a
	real number for the purposes of this function.

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is a natural number.
	:rtype: bool
	"""
	if not is_numeric(value):
		return False
	if not math.isfinite(value):
		return False
	return True

def is_numeric(value):
	"""
	Check whether *value* is a numeric value (i.e. capable of being represented
	as a floating point value without loss of information).

	:param value: The value to check. This value is a native Python type.
	:return: Whether or not the value is numeric.
	:rtype: bool
	"""
	if not isinstance(value, (int, float)):
		return False
	if isinstance(value, bool):
		return False
	return True

def _assert_is_natural_number(value):
	if not is_natural_number(value):
		raise errors.EvaluationError('data type mismatch (not a natural number)')

def _assert_is_numeric(value):
	if not is_numeric(value):
		raise errors.EvaluationError('data type mismatch (not a numeric value)')

class DataType(enum.Enum):
	"""
	A collection of constants representing the different supported data types.
	"""
	BOOLEAN = bool
	DATETIME = datetime.datetime
	FLOAT = float
	NULL = NONE_TYPE
	STRING = str
	UNDEFINED = None
	"""
	Undefined values. This constant can be used to indicate that a particular
	symbol is valid, but it's data type is currently unknown.
	"""
	@classmethod
	def from_type(cls, python_type):
		"""
		Get the supported data type constant for the specified Python type. If
		the type can not be mapped to a supported data type, then a
		:py:exc:`ValueError` exception will be raised. This function will not
		return :py:attr:`.UNDEFINED`.

		:param type python_type: The native Python type to retrieve the
			corresponding type constant for.
		:return: One of the constants.
		"""
		if not isinstance(python_type, type):
			raise TypeError('from_type argument 1 must be type, not ' + type(python_type).__name__)
		if python_type is bool:
			return cls.BOOLEAN
		elif python_type is datetime.date or python_type is datetime.datetime:
			return cls.DATETIME
		elif python_type is float or python_type is int:
			return cls.FLOAT
		elif python_type is NONE_TYPE:
			return cls.NULL
		elif python_type is str:
			return cls.STRING
		raise ValueError("can not map python type {0!r} to a compatible data type".format(python_type.__name__))

	@classmethod
	def from_value(cls, python_value):
		"""
		Get the supported data type constant for the specified Python value. If
		the value can not be mapped to a supported data type, then a
		:py:exc:`TypeError` exception will be raised. This function will not
		return :py:attr:`.UNDEFINED`.

		:param python_value: The native Python value to retrieve the
			corresponding data type constant for.
		:return: One of the constants.
		"""
		if isinstance(python_value, bool):
			return cls.BOOLEAN
		elif isinstance(python_value, (datetime.date, datetime.datetime)):
			return cls.DATETIME
		elif isinstance(python_value, (float, int)):
			return cls.FLOAT
		elif python_value is None:
			return cls.NULL
		elif isinstance(python_value, (str,)):
			return cls.STRING
		raise TypeError("can not map python type {0!r} to a compatible data type".format(type(python_value).__name__))

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
		if not isinstance(value, self.result_type.value):
			raise TypeError("__init__ argument 2 must be {}, not {}".format(self.result_type.value.__name__, type(value).__name__))
		self.value = value

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

class DatetimeExpression(LiteralExpressionBase):
	"""
	Literal datetime expressions representing a specific point in time. This
	expression type always evaluates to true.
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

class NullExpression(LiteralExpressionBase):
	"""
	Literal null expressions representing null values. This expression type
	always evaluates to false.
	"""
	result_type = DataType.NULL
	def __init__(self, context):
		super(NullExpression, self).__init__(context, value=None)

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
	compatible_types = (DataType.BOOLEAN, DataType.DATETIME, DataType.FLOAT, DataType.NULL, DataType.STRING)
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
		_assert_is_numeric(left)
		right = self.right.evaluate(thing)
		_assert_is_numeric(right)
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
	def _op_eq(self, thing):
		if self.left.result_type is not DataType.UNDEFINED and self.right.result_type is not DataType.UNDEFINED:
			if self.left.result_type is not self.right.result_type:
				return False
		left_value = self.left.evaluate(thing)
		right_value = self.right.evaluate(thing)
		if type(left_value) is not type(right_value):
			return False
		return operator.eq(left_value, right_value)

	def _op_ne(self, thing):
		if self.left.result_type is not DataType.UNDEFINED and self.right.result_type is not DataType.UNDEFINED:
			if self.left.result_type is not self.right.result_type:
				return True
		left_value = self.left.evaluate(thing)
		right_value = self.right.evaluate(thing)
		if type(left_value) is not type(right_value):
			return True
		return operator.ne(left_value, right_value)

class ArithmeticComparisonExpression(ComparisonExpression):
	"""
	A class for representing arithmetic comparison expressions from the grammar
	text such as less-than-or-equal-to and greater-than.
	"""
	compatible_types = (DataType.DATETIME, DataType.FLOAT)
	def __op_arithmetic(self, op, thing):
		left = self.left.evaluate(thing)
		if not isinstance(left, datetime.datetime):
			_assert_is_numeric(left)
		right = self.right.evaluate(thing)
		if not isinstance(right, datetime.datetime):
			_assert_is_numeric(right)
		if type(left) is not type(right):
			raise errors.EvaluationError('data type mismatch')
		return op(left, right)

	_op_ge = functools.partialmethod(__op_arithmetic, operator.ge)
	_op_gt = functools.partialmethod(__op_arithmetic, operator.gt)
	_op_le = functools.partialmethod(__op_arithmetic, operator.le)
	_op_lt = functools.partialmethod(__op_arithmetic, operator.lt)

class FuzzyComparisonExpression(ComparisonExpression):
	"""
	A class for representing regular expression comparison expressions from the
	grammar text such as search and does not match.
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
			raise errors.RegexSyntaxError('invalid regular expression', error=error) from None
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
		return modifier(match, None)

	_op_eq_fzm = functools.partialmethod(__op_regex, 'match', operator.is_not)
	_op_eq_fzs = functools.partialmethod(__op_regex, 'search', operator.is_not)
	_op_ne_fzm = functools.partialmethod(__op_regex, 'match', operator.is_)
	_op_ne_fzs = functools.partialmethod(__op_regex, 'search', operator.is_)

################################################################################
# Miscellaneous Expressions
################################################################################
class SymbolExpression(ExpressionBase):
	"""
	A class representing a symbol name to be resolved at evaluation time with
	the help of a :py:class:`~rule_engine.engine.Context` object.
	"""
	__slots__ = ('name', 'result_type', 'scope')
	def __init__(self, context, name, scope=None):
		"""
		:param context: The context to use for evaluating the expression.
		:type context: :py:class:`~rule_engine.engine.Context`
		:param str name: The name of the symbol. This will be resolved with a
			given context object on the specified *thing*.
		:param str scope: The optional scope to use while resolving the symbol.
		"""
		context.symbols.add(name)
		self.context = context
		self.name = name
		type_hint = context.resolve_type(name)
		if type_hint is not None:
			self.result_type = type_hint
		self.scope = scope

	def __repr__(self):
		return "<{0} name={1!r} >".format(self.__class__.__name__, self.name)

	def evaluate(self, thing):
		value = self.context.resolve(thing, self.name, scope=self.scope)

		# convert the value from one of the supported types if necessary
		if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
			value = datetime.datetime(value.year, value.month, value.day)
		elif isinstance(value, int) and not isinstance(value, bool):
			value = float(value)

		if isinstance(value, datetime.datetime) and value.tzinfo is None:
			value = value.replace(tzinfo=self.context.default_timezone)

		# use DataType.from_value to raise a TypeError if value is not of a
		# compatible data type
		value_type = DataType.from_value(value)

		# if the expected result type is undefined, return the value
		if self.result_type is DataType.UNDEFINED:
			return value

		# if the type is the expected result type, return the value
		if value_type is self.result_type:
			return value

		# if the type is null, return the value (treat null as a special case)
		if value_type is DataType.NULL:
			return value

		raise errors.SymbolTypeError(self.name, is_value=value, is_type=value_type, expected_type=self.result_type)

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
		_assert_is_numeric(right)
		return op(right)

	_op_uminus = functools.partialmethod(__op_arithmetic, operator.neg)

	def reduce(self):
		type_ = self.type.lower()
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
