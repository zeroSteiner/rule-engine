#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/binary/base.py
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

from typing import TYPE_CHECKING, Any, Callable

from ... import errors
from ...types import DataType
from ...types import _DataTypeDef

from ..base import ExpressionBase, LiteralExpressionBase, _is_reduced

if TYPE_CHECKING:
    from ...engine.context import Context

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
