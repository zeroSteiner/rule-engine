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

import re
import operator

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

	def _op_eq(self, context, thing):
		left = self.left.evaluate(context, thing)
		right = self.right.evaluate(context, thing)
		return operator.eq(left, right)

	def _op_ne(self, context, thing):
		left = self.left.evaluate(context, thing)
		right = self.right.evaluate(context, thing)
		return operator.ne(left, right)

	def _op_eq_rem(self, context, thing):
		left = self.left.evaluate(context, thing)
		right = self.right.evaluate(context, thing)
		return re.match(right, left, flags=context.regex_flags) is not None

	def _op_eq_res(self, context, thing):
		left = self.left.evaluate(context, thing)
		right = self.right.evaluate(context, thing)
		return re.search(right, left, flags=context.regex_flags) is not None

	def _op_ne_rem(self, context, thing):
		left = self.left.evaluate(context, thing)
		right = self.right.evaluate(context, thing)
		return re.match(right, left, flags=context.regex_flags) is None

	def _op_ne_res(self, context, thing):
		left = self.left.evaluate(context, thing)
		right = self.right.evaluate(context, thing)
		return re.search(right, left, flags=context.regex_flags) is None

	def _op_and(self, context, thing):
		return bool(self.left.evaluate(context, thing) and self.right.evaluate(context, thing))

	def _op_or(self, context, thing):
		return bool(self.left.evaluate(context, thing) or self.right.evaluate(context, thing))

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
