#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/binary/comparison.py
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
import operator
import re
from typing import Any, Callable

from ... import errors
from ...types import DataType, coerce_value
from ...types import _DataTypeDef

from ..base import _assert_not_nullable
from ..literal import StringExpression
from .base import BinaryExpressionBase

class LogicExpression(BinaryExpressionBase):
    """A class for representing logical expressions from the grammar text such as "and" and "or"."""
    def _op_and(self, thing: Any) -> bool:
        return bool(self.left.evaluate(thing) and self.right.evaluate(thing))

    def _op_or(self, thing: Any) -> bool:
        return bool(self.left.evaluate(thing) or self.right.evaluate(thing))

class ComparisonExpression(BinaryExpressionBase):
    """A class for representing comparison expressions from the grammar text such as equality checks."""
    compatible_types: tuple[_DataTypeDef, ...] = BinaryExpressionBase.compatible_types + (DataType.OBJECT,)
    def _op_eq(self, thing: Any) -> bool:
        left_value = self.left.evaluate(thing)
        right_value = self.right.evaluate(thing)
        if type(left_value) is not type(right_value):
            return False
        return operator.eq(left_value, right_value)

    def _op_ne(self, thing: Any) -> bool:
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
    compatible_types: tuple[_DataTypeDef, ...] = (DataType.ARRAY, DataType.BOOLEAN, DataType.DATETIME, DataType.TIMEDELTA, DataType.FLOAT, DataType.NULL, DataType.STRING)
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(ArithmeticComparisonExpression, self).__init__(*args, **kwargs)
        _assert_not_nullable(self.left.result_type, role='left ordered-comparison operand')
        _assert_not_nullable(self.right.result_type, role='right ordered-comparison operand')
        if self.left.result_type != DataType.UNDEFINED and self.right.result_type != DataType.UNDEFINED:
            if self.left.result_type != self.right.result_type:
                raise errors.EvaluationError('data type mismatch')

    def __op_arithmetic(self, op: Callable[[Any, Any], Any], thing: Any) -> Any:
        left_value = self.left.evaluate(thing)
        right_value = self.right.evaluate(thing)
        return self.__op_arithmetic_values(op, left_value, right_value)

    def __op_arithmetic_arrays(self, op: Callable[[Any, Any], Any], left_value: Any, right_value: Any) -> Any:
        for subleft_value, subright_value in zip(left_value, right_value):
            if self.__op_arithmetic_values(operator.ne, subleft_value, subright_value):
                return self.__op_arithmetic_values(op, subleft_value, subright_value)
        if len(left_value) != len(right_value):
            return self.__op_arithmetic_values(op, len(left_value), len(right_value))
        return op in (operator.ge, operator.le)

    def __op_arithmetic_values(self, op: Callable[[Any, Any], Any], left_value: Any, right_value: Any) -> Any:
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
    compatible_types: tuple[_DataTypeDef, ...] = (DataType.NULL, DataType.STRING)
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(FuzzyComparisonExpression, self).__init__(*args, **kwargs)
        _assert_not_nullable(self.left.result_type, role='left regex operand')
        _assert_not_nullable(self.right.result_type, role='right regex operand')
        if isinstance(self.right, StringExpression):
            self._right = self._compile_regex(self.right.evaluate(None))

    def _compile_regex(self, regex: str) -> re.Pattern[str]:
        try:
            result = re.compile(regex, flags=self.context.regex_flags)
        except re.error as error:
            raise errors.RegexSyntaxError('invalid regular expression', error=error, value=regex) from None
        return result

    def __op_regex(self, regex_function: str, modifier: Callable[[Any, Any], Any], thing: Any) -> Any:
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
