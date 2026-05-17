#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/types/__init__.py
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

from .coercion import coerce_value
from .coercion import is_integer_number
from .coercion import is_natural_number
from .coercion import is_numeric
from .coercion import is_real_number

from .datatype import DataType
from .datatype import iterable_member_value_type

from .definitions import NoneType
from .definitions import _ArrayDataTypeDef
from .definitions import _CollectionDataTypeDef
from .definitions import _DataTypeDef
from .definitions import _FunctionDataTypeDef
from .definitions import _MappingDataTypeDef
from .definitions import _NullableDataTypeDef
from .definitions import _ReferenceDataTypeDef
from ._object import _ObjectDataTypeDef

__all__ = (
        'DataType',
        'NoneType',
        'coerce_value',
        'is_integer_number',
        'is_natural_number',
        'is_numeric',
        'is_real_number',
        'iterable_member_value_type'
)
