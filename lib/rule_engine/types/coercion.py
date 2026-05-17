#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/types/coercion.py
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
import decimal
import math
from typing import Any

from .datatype import DataType

def _to_decimal(value: Any) -> decimal.Decimal:
    if isinstance(value, decimal.Decimal):
        return value
    if isinstance(value, int):
        # int subclasses (e.g. IntEnum) don't necessarily repr() as a plain number; convert via int() so the
        # Decimal constructor receives a value it can parse
        return decimal.Decimal(int(value))
    return decimal.Decimal(repr(value))

def coerce_value(value: Any, verify_type: bool = True) -> Any:
    """
    Take a native Python *value* and convert it to a value of a data type which can be represented by a Rule Engine
    :py:class:`~.DataType`. This function is useful for converting native Python values at the engine boundaries such as
    when resolving a symbol from an object external to the engine.

    .. versionadded:: 2.0.0

    :param value: The value to convert.
    :param bool verify_type: Whether or not to verify the converted value's type.
    :return: The converted value.
    """
    # ARRAY
    if isinstance(value, (list, range, tuple)):
        value = tuple(coerce_value(v, verify_type=verify_type) for v in value)
    # DATETIME
    elif isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        value = datetime.datetime(value.year, value.month, value.day)
    # FLOAT
    elif isinstance(value, (float, int)) and not isinstance(value, bool):
        value = _to_decimal(value)
    # MAPPING
    elif isinstance(value, (dict, collections.OrderedDict)):
        value = collections.OrderedDict(
                (coerce_value(k, verify_type=verify_type), coerce_value(v, verify_type=verify_type)) for k, v in value.items()
        )
    if verify_type:
        DataType.from_value(value)  # use this to raise a TypeError, if the type is incompatible
    return value

def is_integer_number(value: Any) -> bool:
    """
    Check whether *value* is an integer number (i.e. a whole, number). This can, for example, be used to check if a
    floating point number such as ``3.0`` can safely be converted to an integer without loss of information.

    .. versionadded:: 2.1.0

    :param value: The value to check. This value is a native Python type.
    :return: Whether or not the value is an integer number.
    :rtype: bool
    """
    if not is_real_number(value):
        return False
    if math.floor(value) != value:
        return False
    return True

def is_natural_number(value: Any) -> bool:
    """
    Check whether *value* is a natural number (i.e. a whole, non-negative number). This can, for example, be used to
    check if a floating point number such as ``3.0`` can safely be converted to an integer without loss of information.

    :param value: The value to check. This value is a native Python type.
    :return: Whether or not the value is a natural number.
    :rtype: bool
    """
    if not is_integer_number(value):
        return False
    if value < 0:
        return False
    return True

def is_real_number(value: Any) -> bool:
    """
    Check whether *value* is a real number (i.e. capable of being represented as a floating point value without loss of
    information as well as being finite). Despite being able to be represented as a float, ``NaN`` is not considered a
    real number for the purposes of this function.

    :param value: The value to check. This value is a native Python type.
    :return: Whether or not the value is a natural number.
    :rtype: bool
    """
    if not is_numeric(value):
        return False
    if not math.isfinite(value):
        return False
    return True

def is_numeric(value: Any) -> bool:
    """
    Check whether *value* is a numeric value (i.e. capable of being represented as a floating point value without loss
    of information).

    :param value: The value to check. This value is a native Python type.
    :return: Whether or not the value is numeric.
    :rtype: bool
    """
    if not isinstance(value, (decimal.Decimal, float, int)):
        return False
    if isinstance(value, bool):
        return False
    return True
