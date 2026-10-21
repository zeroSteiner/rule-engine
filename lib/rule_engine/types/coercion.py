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
import functools
import math
import sys
from typing import Any, Callable, Iterable, NoReturn

from .. import errors
from .datatype import DataType

# sys.get_int_max_str_digits was added in Python 3.10.7, older versions use CPython's default limit
_get_int_max_str_digits: Callable[[], int] = getattr(sys, 'get_int_max_str_digits', lambda: 4300)

def _get_int_max_digits(int_max_digits: int | None) -> int:
    if int_max_digits is None:
        # read the interpreter's limit each time so changes to it take effect
        int_max_digits = _get_int_max_str_digits()
    return int_max_digits

def _int_max_bits(int_max_digits: int) -> int:
    # an upper bound for the bit length of 10 ** int_max_digits, calculated without creating it because that's slow for
    # large limits (log2(10) < 3.321929)
    return int_max_digits * 3321929 // 1000000 + 1

@functools.lru_cache(maxsize=16)
def _int_limit(int_max_digits: int) -> int:
    # the smallest integer with more than int_max_digits digits
    return 10 ** int_max_digits

def _raise_int_size_error(int_max_digits: int) -> NoReturn:
    raise errors.ArithmeticError("arithmetic error: integer exceeds the limit ({0} digits)".format(int_max_digits))

def _assert_int_size(value: int, int_max_digits: int | None = None) -> None:
    # converting an int to a Decimal takes time that grows quadratically with its size, so large values are rejected
    # like Python's own int to str conversion
    int_max_digits = _get_int_max_digits(int_max_digits)
    if not int_max_digits:
        return
    bit_length = value.bit_length()
    # values with at most 3 bits per allowed digit are always less than the limit
    if bit_length <= 3 * int_max_digits:
        return
    # only compare the value to the limit when the bit length alone isn't enough to tell
    if bit_length > _int_max_bits(int_max_digits) or abs(value) >= _int_limit(int_max_digits):
        _raise_int_size_error(int_max_digits)

def _assert_member_int_sizes(values: Iterable[Any], int_max_digits: int) -> None:
    # SET members aren't converted, but comparing one to a FLOAT value converts it, so check the size of the integers
    for value in values:
        if isinstance(value, int):
            _assert_int_size(value, int_max_digits)
        elif isinstance(value, (frozenset, tuple)):
            _assert_member_int_sizes(value, int_max_digits)

def _assert_int_bit_length(bit_length: int, int_max_digits: int | None = None) -> None:
    # check the size of an integer that hasn't been created yet, this only rejects bit lengths that are too large for
    # any value so the integer still needs to be checked with _assert_int_size once it has been created
    int_max_digits = _get_int_max_digits(int_max_digits)
    if int_max_digits and bit_length > _int_max_bits(int_max_digits):
        _raise_int_size_error(int_max_digits)

def _assert_int_digits(digits: int, int_max_digits: int | None = None) -> None:
    # check the number of digits of an integer that hasn't been created yet
    int_max_digits = _get_int_max_digits(int_max_digits)
    if int_max_digits and digits > int_max_digits:
        _raise_int_size_error(int_max_digits)

def _to_decimal(value: Any, int_max_digits: int | None = None) -> decimal.Decimal:
    if isinstance(value, decimal.Decimal):
        return value
    if isinstance(value, int):
        # int subclasses (e.g. IntEnum) don't necessarily repr() as a plain number; convert via int() so the
        # Decimal constructor receives a value it can parse
        value = int(value)
        if int_max_digits is None:
            int_max_digits = _get_int_max_str_digits()
        # skip the call for values with at most 3 bits per allowed digit which are always within the limit, this is the
        # common case and is checked here to keep it fast
        if value.bit_length() > 3 * int_max_digits:
            _assert_int_size(value, int_max_digits)
        return decimal.Decimal(value)
    return decimal.Decimal(repr(value))

def coerce_value(value: Any, verify_type: bool = True, *, int_max_digits: int | None = None) -> Any:
    """
    Take a native Python *value* and convert it to a value of a data type which can be represented by a Rule Engine
    :py:class:`~.DataType`. This function is useful for converting native Python values at the engine boundaries such as
    when resolving a symbol from an object external to the engine.

    .. versionadded:: 2.0.0

    .. versionchanged:: 5.1.1
            Added the *int_max_digits* parameter.

    :param value: The value to convert.
    :param bool verify_type: Whether or not to verify the converted value's type.
    :param int int_max_digits: The maximum number of digits that an integer can have to be converted to a ``FLOAT``
            value. Converting an integer takes time that grows quadratically with its size. ``0`` disables the limit,
            and ``None`` (the default) uses the interpreter's limit from :py:func:`sys.get_int_max_str_digits`.
    :return: The converted value.
    :raises ~rule_engine.errors.ArithmeticError: *value* is an integer with more digits than allowed by
            *int_max_digits*, or it is a :py:class:`dict`, :py:class:`list`, :py:class:`range`, :py:class:`set` or
            :py:class:`tuple` that contains one.
    """
    # ARRAY
    if isinstance(value, (list, range, tuple)):
        int_max_digits = _get_int_max_digits(int_max_digits)
        value = tuple(coerce_value(v, verify_type=verify_type, int_max_digits=int_max_digits) for v in value)
    # DATETIME
    elif isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        value = datetime.datetime(value.year, value.month, value.day)
    # FLOAT
    elif isinstance(value, (float, int)) and not isinstance(value, bool):
        value = _to_decimal(value, int_max_digits)
    # MAPPING
    elif isinstance(value, (dict, collections.OrderedDict)):
        int_max_digits = _get_int_max_digits(int_max_digits)
        value = collections.OrderedDict(
                (
                    coerce_value(k, verify_type=verify_type, int_max_digits=int_max_digits),
                    coerce_value(v, verify_type=verify_type, int_max_digits=int_max_digits)
                ) for k, v in value.items()
        )
    # SET
    elif isinstance(value, set):
        int_max_digits = _get_int_max_digits(int_max_digits)
        if int_max_digits:
            _assert_member_int_sizes(value, int_max_digits)
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
