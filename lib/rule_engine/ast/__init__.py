#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/__init__.py
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

from .base import (
        ASTNodeBase,
        Assignment,
        Comment,
        ExpressionBase,
        LiteralExpressionBase,
        Statement,
        _assert_is_bytes,
        _assert_is_integer_number,
        _assert_is_natural_number,
        _assert_is_numeric,
        _assert_is_string,
        _assert_not_nullable,
        _is_reduced,
        _iterable_member_value_type,
        _resolve_type,
)
from .literal import (
        ArrayExpression,
        BooleanExpression,
        BytesExpression,
        DatetimeExpression,
        FloatExpression,
        FunctionExpression,
        MappingExpression,
        NullExpression,
        SetExpression,
        StringExpression,
        TimedeltaExpression,
        _CollectionMixin,
)
from .binary import (
        AddExpression,
        ArithmeticComparisonExpression,
        ArithmeticExpression,
        BinaryExpressionBase,
        BitwiseExpression,
        BitwiseShiftExpression,
        CoalesceExpression,
        ComparisonExpression,
        FuzzyComparisonExpression,
        LogicExpression,
        SubtractExpression,
)
from .expression import (
        ComprehensionExpression,
        ContainsExpression,
        FunctionCallExpression,
        GetAttributeExpression,
        GetItemExpression,
        GetSliceExpression,
        SymbolExpression,
        TernaryExpression,
        UnaryExpression,
)

# deprecated alias — use BinaryExpressionBase instead
LeftOperatorRightExpressionBase = BinaryExpressionBase

from ..types import _ObjectDataTypeDef, _ReferenceDataTypeDef
