#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/expression/control.py
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

import collections
import datetime
import functools
import operator
from typing import TYPE_CHECKING, Any, Callable

from ... import errors
from ...types import DataType, is_numeric
from ...types import _DataTypeDef

from ..base import (
        Assignment,
        ExpressionBase,
        LiteralExpressionBase,
        _assert_not_nullable,
        _is_reduced,
        _propagate_nullable,
        _resolve_type,
)
from ..literal import BooleanExpression, FloatExpression, TimedeltaExpression

if TYPE_CHECKING:
    from ...engine.context import Context

class ComprehensionExpression(ExpressionBase):
    result_type: _DataTypeDef = DataType.ARRAY
    def __init__(
            self,
            context: 'Context',
            result: ExpressionBase,
            variable: str,
            iterable: ExpressionBase,
            condition: ExpressionBase | None = None
    ) -> None:
        self.context = context
        self.result = result
        self.variable = variable
        self.iterable = iterable
        self.condition = condition
        self.result_type = DataType.ARRAY(self.result.result_type)

    @classmethod
    def build(  # type: ignore[override]
            cls,
            context: 'Context',
            result: ExpressionBase,
            variable: str,
            iterable: ExpressionBase,
            condition: ExpressionBase | None = None
    ) -> ExpressionBase:
        iterable_built = iterable.build()
        assert isinstance(iterable_built, ExpressionBase)
        if iterable_built.result_type is not DataType.UNDEFINED and not iterable_built.result_type.is_iterable:
            raise errors.EvaluationError('data type mismatch (comprehension requires an iterable)')
        resolved_iterable_type = _resolve_type(iterable_built.result_type, context)
        assignment = Assignment(variable, value_type=getattr(resolved_iterable_type, 'iterable_type', DataType.UNDEFINED))
        with context.assignments(assignment):
            if condition is not None:
                condition_built = condition.build()
                assert isinstance(condition_built, ExpressionBase)
                condition = condition_built
            result_built = result.build()
            assert isinstance(result_built, ExpressionBase)
            result = result_built
        reduced = cls(context, result, variable, iterable_built, condition=condition).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def __repr__(self) -> str:
        return "<{0} iterable={1!r} result={2!r} condition={3!r} >".format(self.__class__.__name__, self.iterable, self.result, self.condition)

    def evaluate(self, thing: Any) -> Any:
        output_array: 'collections.deque[Any]' = collections.deque()
        input_iterable = self.iterable.evaluate(thing)
        if not DataType.from_value(input_iterable).is_iterable:
            raise errors.EvaluationError('data type mismatch (comprehension requires an iterable)')
        for value in input_iterable:
            assignment = Assignment(self.variable, value=value)
            with self.context.assignments(assignment):
                if self.condition is None or self.condition.evaluate(thing):
                    output_array.append(self.result.evaluate(thing))
        return tuple(output_array)

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        digraph.node(str(id(self)), "{}\nvariable={!r}".format(self.__class__.__name__, self.variable))
        self.result.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.result)), label='result')
        self.iterable.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.iterable)), label='iterable')
        if self.condition is not None:
            self.condition.to_graphviz(digraph, *args, **kwargs)
            digraph.edge(str(id(self)), str(id(self.condition)), label='condition')

class TernaryExpression(ExpressionBase):
    """
    A class for representing ternary expressions from the grammar text. These involve evaluating :py:attr:`.condition`
    before evaluating either :py:attr:`.case_true` or :py:attr:`.case_false` based on the results.
    """
    def __init__(self, context: 'Context', condition: ExpressionBase, case_true: ExpressionBase, case_false: ExpressionBase) -> None:
        """
        :param context: The context to use for evaluating the expression.
        :type context: :py:class:`~rule_engine.engine.Context`
        :param condition: The condition expression whose evaluation determines whether the *case_true* or *case_false*
                expression is evaluated.
        :param case_true: The expression that's evaluated when *condition* is True.
        :param case_false:The expression that's evaluated when *condition* is False.
        """
        self.context = context
        self.condition = condition
        self.case_true = case_true
        self.case_false = case_false
        true_type = DataType.NULLABLE.unwrap(self.case_true.result_type)
        false_type = DataType.NULLABLE.unwrap(self.case_false.result_type)
        if true_type == false_type:
            self.result_type = true_type
        elif DataType.is_type(true_type, DataType.ARRAY) and DataType.is_type(false_type, DataType.ARRAY):
            self.result_type = DataType.ARRAY
        # todo: the other compound types should be checked here as well.
        self.result_type = _propagate_nullable(self.result_type, self.case_true.result_type, self.case_false.result_type)

    @classmethod
    def build(cls, context: 'Context', condition: ExpressionBase, case_true: ExpressionBase, case_false: ExpressionBase) -> ExpressionBase:  # type: ignore[override]
        condition_built = condition.build()
        assert isinstance(condition_built, ExpressionBase)
        case_true_built = case_true.build()
        assert isinstance(case_true_built, ExpressionBase)
        case_false_built = case_false.build()
        assert isinstance(case_false_built, ExpressionBase)
        reduced = cls(context, condition_built, case_true_built, case_false_built).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def evaluate(self, thing: Any) -> Any:
        case = (self.case_true if self.condition.evaluate(thing) else self.case_false)
        return case.evaluate(thing)

    def reduce(self) -> ExpressionBase:
        if not _is_reduced(self.condition):
            return self
        assert isinstance(self.condition, LiteralExpressionBase)
        reduced_condition = bool(self.condition.value)
        reduced = self.case_true.reduce() if reduced_condition else self.case_false.reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        super(TernaryExpression, self).to_graphviz(digraph, *args, **kwargs)
        self.condition.to_graphviz(digraph, *args, **kwargs)
        self.case_true.to_graphviz(digraph, *args, **kwargs)
        self.case_false.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.condition)), label='condition')
        digraph.edge(str(id(self)), str(id(self.case_true)), label='true case')
        digraph.edge(str(id(self)), str(id(self.case_false)), label='false case')

class UnaryExpression(ExpressionBase):
    """
    A class for representing unary expressions from the grammar text. These involve a single operator on the left side.
    """
    def __init__(self, context: 'Context', type_: str, right: ExpressionBase) -> None:
        """
        :param context: The context to use for evaluating the expression.
        :type context: :py:class:`~rule_engine.engine.Context`
        :param str type_: The grammar type of operator to the left of the expression.
        :param right: The expression to the right of the operator.
        :type right: :py:class:`~.ExpressionBase`
        """
        self.context = context
        type_ = type_.lower()
        self.type = type_
        if type_ == 'not':
            self.result_type = DataType.BOOLEAN
        elif type_ == 'uminus':
            _assert_not_nullable(right.result_type, role='unary minus operand')
            self.result_type = right.result_type
        else:
            raise ValueError('unknown unary expression type')
        self._evaluator = getattr(self, '_op_' + type_)
        self.right = right

    @classmethod
    def build(cls, context: 'Context', type_: str, right: ExpressionBase) -> ExpressionBase:  # type: ignore[override]
        right_built = right.build()
        assert isinstance(right_built, ExpressionBase)
        reduced = cls(context, type_, right_built).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def __repr__(self) -> str:
        return "<{} type={!r} >".format(self.__class__.__name__, self.type)

    def evaluate(self, thing: Any) -> Any:
        return self._evaluator(thing)

    def __op(self, op: Callable[[Any], Any], thing: Any) -> Any:
        return op(self.right.evaluate(thing))

    _op_not = functools.partialmethod(__op, operator.not_)

    def __op_arithmetic(self, op: Callable[[Any], Any], thing: Any) -> Any:
        right = self.right.evaluate(thing)
        if not is_numeric(right) and not isinstance(right, datetime.timedelta):
            raise errors.EvaluationError('data type mismatch (not a numeric or timedelta value)')
        return op(right)

    _op_uminus = functools.partialmethod(__op_arithmetic, operator.neg)

    def reduce(self) -> ExpressionBase:
        type_ = self.type.lower()
        if not _is_reduced(self.right):
            return self
        if type_ == 'not':
            return BooleanExpression(self.context, self.evaluate(None))
        elif type_ == 'uminus':
            if isinstance(self.right, FloatExpression):
                return FloatExpression(self.context, self.evaluate(None))
            elif isinstance(self.right, TimedeltaExpression):
                return TimedeltaExpression(self.context, self.evaluate(None))
            raise errors.EvaluationError('data type mismatch (not a float or timedelta expression)')
        raise errors.EngineError('unsupported unary expression type')

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        digraph.node(str(id(self)), "{}\ntype={!r}".format(self.__class__.__name__, self.type.lower()))
        self.right.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.right)))
