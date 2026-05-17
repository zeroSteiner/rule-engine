#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/binary/__init__.py
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

from typing import TYPE_CHECKING, Any

from ... import errors
from ...types import DataType
from ...types import _DataTypeDef

from ..base import ExpressionBase, LiteralExpressionBase, _is_reduced

from .arithmetic import AddExpression, ArithmeticExpression, BitwiseExpression, BitwiseShiftExpression, SubtractExpression
from .base import BinaryExpressionBase
from .comparison import ArithmeticComparisonExpression, ComparisonExpression, FuzzyComparisonExpression, LogicExpression

if TYPE_CHECKING:
    from ...engine.context import Context

class CoalesceExpression(ExpressionBase):
    """
    A class representing a null-coalesce (``??``) expression. Evaluates to the left operand when it is not ``None``;
    otherwise evaluates to the right operand. The result type discharges nullability from the left operand when the
    right operand is non-nullable.

    .. versionadded:: 5.0.0
    """
    __slots__ = ('left', 'right')
    result_type: _DataTypeDef = DataType.UNDEFINED
    def __init__(self, context: 'Context', left: ExpressionBase, right: ExpressionBase) -> None:
        self.context = context
        self.left = left
        self.right = right
        left_peeled = DataType.NULLABLE.unwrap(left.result_type)
        right_peeled = DataType.NULLABLE.unwrap(right.result_type)
        if left_peeled != DataType.UNDEFINED and right_peeled != DataType.UNDEFINED:
            if left_peeled != DataType.NULL and right_peeled != DataType.NULL:
                if not DataType.is_compatible(left_peeled, right_peeled):
                    raise errors.EvaluationError('data type mismatch')
        if left_peeled == DataType.NULL or left_peeled == DataType.UNDEFINED:
            base_type = right_peeled
        else:
            base_type = left_peeled
        if DataType.is_type(right.result_type, DataType.NULLABLE) or right_peeled == DataType.NULL:
            self.result_type = DataType.NULLABLE.wrap(base_type)
        else:
            self.result_type = base_type

    @classmethod
    def build(cls, context: 'Context', left: ExpressionBase, right: ExpressionBase) -> ExpressionBase:  # type: ignore[override]
        left_built = left.build()
        assert isinstance(left_built, ExpressionBase)
        right_built = right.build()
        assert isinstance(right_built, ExpressionBase)
        reduced = cls(context, left_built, right_built).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def evaluate(self, thing: Any) -> Any:
        left_value = self.left.evaluate(thing)
        if left_value is None:
            return self.right.evaluate(thing)
        return left_value

    def reduce(self) -> ExpressionBase:
        if not _is_reduced(self.left, self.right):
            return self
        return LiteralExpressionBase.from_value(self.context, self.evaluate(None))

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        digraph.node(str(id(self)), self.__class__.__name__)
        self.left.to_graphviz(digraph, *args, **kwargs)
        self.right.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.left)), label='left')
        digraph.edge(str(id(self)), str(id(self.right)), label='right')
