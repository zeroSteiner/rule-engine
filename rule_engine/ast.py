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

import functools
import re
import operator

from . import errors

class Expression(object):
	def __repr__(self):
		return "<{0} >".format(self.__class__.__name__)

	def evaluate(self, context, thing):
		raise NotImplementedError()

class LogicExpression(Expression):
	__slots__ = ('_evaluator', 'type', 'left', 'right')
	def __init__(self, type_, left, right):
		self.type = type_
		self._evaluator = getattr(self, '_op_' + type_.lower())
		self.left = left
		self.right = right

	def evaluate(self, context, thing):
		return self._evaluator(context, thing)

	def _op_and(self, context, thing):
		return bool(self.left.evaluate(context, thing) and self.right.evaluate(context, thing))

	def _op_or(self, context, thing):
		return bool(self.left.evaluate(context, thing) or self.right.evaluate(context, thing))

	def __op_arithmetic(self, op, context, thing):
		left = self.left.evaluate(context, thing)
		if not isinstance(left, (int, float)):
			raise errors.EvaluationError('data type mismatch')
		right = self.right.evaluate(context, thing)
		if not isinstance(right, (int, float)):
			raise errors.EvaluationError('data type mismatch')
		return op(left, right)

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
		right_regex = self.right.evaluate(context, thing)
		match = regex_function(right_regex, left_string, flags=context.regex_flags)
		return modifier(match, None)

	_op_eq_rem = functools.partialmethod(__op_regex, re.match, operator.is_not)
	_op_eq_res = functools.partialmethod(__op_regex, re.search, operator.is_not)
	_op_ne_rem = functools.partialmethod(__op_regex, re.match, operator.is_)
	_op_ne_res = functools.partialmethod(__op_regex, re.search, operator.is_)

class TernaryExpression(Expression):
	__slots__ = ('condition', 'case_true', 'case_false')
	def __init__(self, condition, case_true, case_false):
		self.condition = condition
		self.case_true = case_true
		self.case_false = case_false

	def evaluate(self, context, thing):
		case = (self.case_true if self.condition.evaluate(context, thing) else self.case_false)
		return case.evaluate(context, thing)

class SymbolExpression(Expression):
	__slots__ = ('name',)
	def __init__(self, name):
		self.name = name

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

################################################################################
# Literal Expressions
################################################################################
class LiteralExpression(Expression):
	__slots__ = ('value',)
	def __init__(self, value):
		self.value = value

	def __repr__(self):
		return "<{0} value={1!r} >".format(self.__class__.__name__, self.value)

	def evaluate(self, context, thing):
		return self.value

class BooleanExpression(LiteralExpression):
	pass

class FloatExpression(LiteralExpression):
	pass

class IntegerExpression(LiteralExpression):
	pass

class StringExpression(LiteralExpression):
	pass
