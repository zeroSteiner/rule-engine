#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/binary.py
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
import re
from typing import TYPE_CHECKING, Any, Callable

from .. import errors
from ..types import DataType, coerce_value
from ..types import _DataTypeDef

from .base import (
        ExpressionBase,
        LiteralExpressionBase,
        _assert_is_bytes,
        _assert_is_natural_number,
        _assert_is_numeric,
        _assert_is_string,
        _is_reduced,
)
from .literal import StringExpression

if TYPE_CHECKING:
    from ..engine.context import Context

################################################################################
# Binary Expressions
################################################################################
class BinaryExpressionBase(ExpressionBase):
    """
    A base class for representing complex expressions composed of a left side and a right side, separated by an
    operator.
    """
    compatible_types: tuple[_DataTypeDef, ...] = (DataType.ARRAY, DataType.BOOLEAN, DataType.DATETIME, DataType.TIMEDELTA, DataType.FLOAT, DataType.MAPPING, DataType.NULL, DataType.SET, DataType.STRING)
    """
    A tuple containing the compatible data types that the left and right expressions must return. This can for example
    be used to indicate that arithmetic operations are compatible with :py:attr:`~.DataType.FLOAT` but not
    :py:attr:`~.DataType.STRING` values.
    """
    result_type: _DataTypeDef = DataType.BOOLEAN
    def __init__(self, context: 'Context', type_: str, left: ExpressionBase, right: ExpressionBase) -> None:
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
        evaluator = getattr(self, '_op_' + type_, None)
        if evaluator is None:
            raise errors.EngineError('unsupported operator: ' + type_)
        self._evaluator: Callable[[Any], Any] = evaluator
        self._assert_type_is_compatible(left)
        self.left = left
        self._assert_type_is_compatible(right)
        self.right = right

    @classmethod
    def build(cls, context: 'Context', type_: str, left: ExpressionBase, right: ExpressionBase) -> ExpressionBase:  # type: ignore[override]
        left_built = left.build()
        assert isinstance(left_built, ExpressionBase)
        right_built = right.build()
        assert isinstance(right_built, ExpressionBase)
        reduced = cls(context, type_, left_built, right_built).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def _assert_type_is_compatible(self, value: ExpressionBase) -> None:
        if value.result_type == DataType.UNDEFINED:
            return
        if any(DataType.is_compatible(dt, value.result_type) for dt in self.compatible_types):
            return
        raise errors.EvaluationError('data type mismatch')

    def __repr__(self) -> str:
        return "<{} type={!r} >".format(self.__class__.__name__, self.type)

    def evaluate(self, thing: Any) -> Any:
        return self._evaluator(thing)

    def reduce(self) -> ExpressionBase:
        if not _is_reduced(self.left, self.right):
            return self
        return LiteralExpressionBase.from_value(self.context, self.evaluate(None))

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        digraph.node(str(id(self)), "{}\ntype={!r}".format(self.__class__.__name__, self.type))
        self.left.to_graphviz(digraph, *args, **kwargs)
        self.right.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.left)), label='left')
        digraph.edge(str(id(self)), str(id(self.right)), label='right')

class AddExpression(BinaryExpressionBase):
    """A class for representing addition expressions from the grammar text."""
    compatible_types: tuple[_DataTypeDef, ...] = (DataType.BYTES, DataType.FLOAT, DataType.STRING, DataType.DATETIME, DataType.TIMEDELTA)
    result_type: _DataTypeDef = DataType.UNDEFINED

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(AddExpression, self).__init__(*args, **kwargs)
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

    def _op_bitwise(self, op: Callable[[Any, Any], Any], thing: Any) -> Any:
        left = self.left.evaluate(thing)
        if DataType.from_value(left) == DataType.FLOAT:
            return self._op_bitwise_float(op, thing, left)
        elif isinstance(DataType.from_value(left), DataType.SET.__class__):
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

class LogicExpression(BinaryExpressionBase):
    """A class for representing logical expressions from the grammar text such as "and" and "or"."""
    def _op_and(self, thing: Any) -> bool:
        return bool(self.left.evaluate(thing) and self.right.evaluate(thing))

    def _op_or(self, thing: Any) -> bool:
        return bool(self.left.evaluate(thing) or self.right.evaluate(thing))

################################################################################
# Binary Comparison Expressions
################################################################################
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
