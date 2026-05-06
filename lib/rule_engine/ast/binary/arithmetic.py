#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/binary/arithmetic.py
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
import operator
from typing import Any, Callable

from ... import errors
from ...types import DataType, coerce_value
from ...types import _DataTypeDef

from ..base import _assert_is_bytes, _assert_is_natural_number, _assert_is_numeric, _assert_is_string, _assert_not_nullable, _is_reduced
from .base import BinaryExpressionBase

class AddExpression(BinaryExpressionBase):
    """A class for representing addition expressions from the grammar text."""
    compatible_types: tuple[_DataTypeDef, ...] = (DataType.BYTES, DataType.FLOAT, DataType.STRING, DataType.DATETIME, DataType.TIMEDELTA)
    result_type: _DataTypeDef = DataType.UNDEFINED

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(AddExpression, self).__init__(*args, **kwargs)
        _assert_not_nullable(self.left.result_type, role="left operand of '+'")
        _assert_not_nullable(self.right.result_type, role="right operand of '+'")
        if self.left.result_type != DataType.UNDEFINED and self.right.result_type != DataType.UNDEFINED:
            if self.left.result_type == DataType.DATETIME:
                if self.right.result_type != DataType.TIMEDELTA:
                    raise errors.EvaluationError('data type mismatch')
                self.result_type = self.left.result_type
            elif self.left.result_type == DataType.TIMEDELTA:
                if self.right.result_type not in (DataType.DATETIME, DataType.TIMEDELTA):
                    raise errors.EvaluationError('data type mismatch')
                self.result_type = self.right.result_type
            elif self.left.result_type != self.right.result_type:
                raise errors.EvaluationError('data type mismatch')
            else:
                self.result_type = self.left.result_type

    def _op_add(self, thing: Any) -> Any:
        left_value = self.left.evaluate(thing)
        right_value = self.right.evaluate(thing)
        if isinstance(left_value, datetime.datetime):
            if not isinstance(right_value, datetime.timedelta):
                raise errors.EvaluationError('data type mismatch (not a timedelta value)')
        elif isinstance(left_value, datetime.timedelta):
            if not isinstance(right_value, (datetime.timedelta, datetime.datetime)):
                raise errors.EvaluationError('data type mismatch (not a datetime or timedelta value)')
        elif isinstance(left_value, bytes) or isinstance(right_value, bytes):
            _assert_is_bytes(left_value, right_value)
        elif isinstance(left_value, str) or isinstance(right_value, str):
            _assert_is_string(left_value, right_value)
        else:
            _assert_is_numeric(left_value, right_value)
        return operator.add(left_value, right_value)

class SubtractExpression(BinaryExpressionBase):
    """
    A class for representing subtraction expressions from the grammar text.

    .. versionadded:: 3.5.0
    """
    compatible_types: tuple[_DataTypeDef, ...] = (DataType.FLOAT, DataType.DATETIME, DataType.TIMEDELTA)
    result_type: _DataTypeDef = DataType.UNDEFINED

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(SubtractExpression, self).__init__(*args, **kwargs)
        _assert_not_nullable(self.left.result_type, role="left operand of '-'")
        _assert_not_nullable(self.right.result_type, role="right operand of '-'")
        if self.left.result_type != DataType.UNDEFINED and self.right.result_type != DataType.UNDEFINED:
            if self.left.result_type == DataType.DATETIME:
                if self.right.result_type == DataType.DATETIME:
                    self.result_type = DataType.TIMEDELTA
                elif self.right.result_type == DataType.TIMEDELTA:
                    self.result_type = DataType.DATETIME
                else:
                    raise errors.EvaluationError('data type mismatch')
            elif self.left.result_type == DataType.TIMEDELTA:
                if self.right.result_type != DataType.TIMEDELTA:
                    raise errors.EvaluationError('data type mismatch')
                self.result_type = self.left.result_type
            elif self.left.result_type != self.right.result_type:
                raise errors.EvaluationError('data type mismatch')
            else:
                self.result_type = self.left.result_type

    def _op_sub(self, thing: Any) -> Any:
        left_value = self.left.evaluate(thing)
        right_value = self.right.evaluate(thing)
        if isinstance(left_value, datetime.datetime):
            if not isinstance(right_value, (datetime.datetime, datetime.timedelta)):
                raise errors.EvaluationError('data type mismatch (not a datetime or timedelta value)')
        elif isinstance(left_value, datetime.timedelta):
            if not isinstance(right_value, datetime.timedelta):
                raise errors.EvaluationError('data type mismatch (not a timedelta value)')
        else:
            _assert_is_numeric(left_value, right_value)
        return operator.sub(left_value, right_value)

class ArithmeticExpression(BinaryExpressionBase):
    """A class for representing arithmetic expressions from the grammar text such as multiplication and division."""
    compatible_types: tuple[_DataTypeDef, ...] = (DataType.FLOAT,)
    result_type: _DataTypeDef = DataType.FLOAT
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(ArithmeticExpression, self).__init__(*args, **kwargs)
        _assert_not_nullable(self.left.result_type, role='left arithmetic operand')
        _assert_not_nullable(self.right.result_type, role='right arithmetic operand')

    def __op_arithmetic(self, op: Callable[[Any, Any], Any], thing: Any) -> Any:
        left_value = self.left.evaluate(thing)
        _assert_is_numeric(left_value)
        right_value = self.right.evaluate(thing)
        _assert_is_numeric(right_value)
        try:
            result = op(left_value, right_value)
        except ZeroDivisionError:
            raise errors.ArithmeticError('arithmetic error: division by zero') from None
        except ArithmeticError:
            raise errors.ArithmeticError('arithmetic error') from None
        return result

    _op_fdiv = functools.partialmethod(__op_arithmetic, operator.floordiv)
    _op_tdiv = functools.partialmethod(__op_arithmetic, operator.truediv)
    _op_mod  = functools.partialmethod(__op_arithmetic, operator.mod)
    _op_mul  = functools.partialmethod(__op_arithmetic, operator.mul)
    _op_pow  = functools.partialmethod(__op_arithmetic, operator.pow)

class BitwiseExpression(BinaryExpressionBase):
    """
    A class for representing bitwise arithmetic expressions from the grammar text such as XOR and shifting operations.
    """
    compatible_types: tuple[_DataTypeDef, ...] = (DataType.FLOAT, DataType.SET)
    result_type: _DataTypeDef = DataType.UNDEFINED
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(BitwiseExpression, self).__init__(*args, **kwargs)
        _assert_not_nullable(self.left.result_type, role='left bitwise operand')
        _assert_not_nullable(self.right.result_type, role='right bitwise operand')
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
        if DataType.is_type(self.left.result_type, DataType.SET) or DataType.is_type(self.right.result_type, DataType.SET):
            self.result_type = DataType.SET  # this discards the member type info

    def _op_bitwise(self, op: Callable[[Any, Any], Any], thing: Any) -> Any:
        left = self.left.evaluate(thing)
        if DataType.from_value(left) == DataType.FLOAT:
            return self._op_bitwise_float(op, thing, left)
        elif DataType.is_type(DataType.from_value(left), DataType.SET):
            return self._op_bitwise_set(op, thing, left)
        raise errors.EvaluationError('data type mismatch')

    def _op_bitwise_float(self, op: Callable[[Any, Any], Any], thing: Any, left: Any) -> Any:
        _assert_is_natural_number(left)
        right = self.right.evaluate(thing)
        _assert_is_natural_number(right)
        return coerce_value(op(int(left), int(right)))

    def _op_bitwise_set(self, op: Callable[[Any, Any], Any], thing: Any, left: Any) -> Any:
        right = self.right.evaluate(thing)
        if not DataType.is_compatible(DataType.from_value(right), DataType.SET):
            raise errors.EvaluationError('data type mismatch')
        return op(left, right)

    _op_bwand = functools.partialmethod(_op_bitwise, operator.and_)
    _op_bwor  = functools.partialmethod(_op_bitwise, operator.or_)
    _op_bwxor = functools.partialmethod(_op_bitwise, operator.xor)

class BitwiseShiftExpression(BitwiseExpression):
    compatible_types: tuple[_DataTypeDef, ...] = (DataType.FLOAT,)
    result_type: _DataTypeDef = DataType.FLOAT
    def _op_bitwise_shift(self, *args: Any, **kwargs: Any) -> Any:
        return self._op_bitwise(*args, **kwargs)
    _op_bwlsh = functools.partialmethod(_op_bitwise_shift, operator.lshift)
    _op_bwrsh = functools.partialmethod(_op_bitwise_shift, operator.rshift)
