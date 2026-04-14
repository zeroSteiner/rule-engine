#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/engine/_attribute_resolver.py
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

import binascii
import collections
import datetime
import decimal
import functools
import math
import re
from typing import Any, Callable, Iterable, Sequence, Sized

from .. import errors
from .. import parser
from .. import types
from ..suggestions import suggest_symbol
from ..types import _CollectionDataTypeDef, _DataTypeDef

def _float_op(value: decimal.Decimal, op: Callable[[decimal.Decimal], Any]) -> Any:
    if value.is_nan() or value.is_infinite():
        return value
    return op(value)

def _value_to_ary_result_type(object_type: _DataTypeDef) -> _DataTypeDef:
    if object_type == types.DataType.BYTES:
        return types.DataType.ARRAY(types.DataType.FLOAT)
    elif object_type == types.DataType.STRING:
        return types.DataType.ARRAY(types.DataType.STRING)
    assert isinstance(object_type, _CollectionDataTypeDef)
    return types.DataType.ARRAY(object_type.value_type)

def _value_to_set_result_type(object_type: _DataTypeDef) -> _DataTypeDef:
    if object_type == types.DataType.BYTES:
        return types.DataType.SET(types.DataType.FLOAT)
    elif object_type == types.DataType.STRING:
        return types.DataType.SET(types.DataType.STRING)
    assert isinstance(object_type, _CollectionDataTypeDef)
    return types.DataType.SET(object_type.value_type)

def _value_with_result_type(name: str, object_type: _DataTypeDef) -> _DataTypeDef:
    return types.DataType.FUNCTION(name, argument_types=(object_type,), return_type=types.DataType.BOOLEAN)

class _AttributeResolverFunction(object):
    __slots__ = ('function', 'type_resolver')
    def __init__(
            self,
            function: Callable[..., Any],
            *,
            result_type: _DataTypeDef,
            type_resolver: Callable[[_DataTypeDef], _DataTypeDef] | Any
    ) -> None:
        self.function = function
        if result_type and result_type is not types.DataType.UNDEFINED:
            if not types.DataType.is_definition(result_type):
                raise TypeError('result_type must be a types.DataType definition')
            if type_resolver:
                raise ValueError('both result_type and type_resolver can not be specified')
            type_resolver = functools.partial(self._type_resolver, result_type)
        elif not type_resolver:
            type_resolver = functools.partial(self._type_resolver, types.DataType.UNDEFINED)
        self.type_resolver: Callable[[_DataTypeDef], _DataTypeDef] = type_resolver

    @staticmethod
    def _type_resolver(result_type: _DataTypeDef, _object_type: _DataTypeDef) -> _DataTypeDef:
        return result_type

    def resolve_type(self, object_type: _DataTypeDef) -> _DataTypeDef:
        return self.type_resolver(object_type)

class _AttributeResolver(object):
    class attribute(object):
        __slots__ = ('types', 'name', 'result_type', 'type_resolver')
        type_map: dict[_DataTypeDef, dict[str, _AttributeResolverFunction]] = collections.defaultdict(dict)
        def __init__(
                self,
                name: str,
                *data_types: _DataTypeDef,
                result_type: _DataTypeDef = types.DataType.UNDEFINED,
                type_resolver: Callable[[_DataTypeDef], _DataTypeDef] | Any = errors.UNDEFINED
        ) -> None:
            self.types = data_types
            self.name = name
            self.result_type = result_type
            self.type_resolver = type_resolver

        def __call__(self, function: Callable[..., Any]) -> Callable[..., Any]:
            for type_ in self.types:
                self.type_map[type_][self.name] = _AttributeResolverFunction(function, result_type=self.result_type, type_resolver=self.type_resolver)
            return function

    def __call__(self, thing: Any, object_: Any, name: str) -> Any:
        try:
            object_type = types.DataType.from_value(object_)
        except TypeError:
            # if the object can't be mapped to a supported type, raise a resolution error
            raise errors.AttributeResolutionError(name, object_, thing=thing) from None
        resolver = self._get_resolver(object_type, name, thing=thing)
        value = resolver.function(self, object_)
        value = types.coerce_value(value)
        value_type = types.DataType.from_value(value)
        expected_value_type = resolver.resolve_type(value_type)
        if types.DataType.is_compatible(expected_value_type, value_type):
            return value
        raise errors.AttributeTypeError(name, object_, is_value=value, is_type=value_type, expected_type=expected_value_type)

    def _get_resolver(self, object_type: _DataTypeDef, name: str, thing: Any = errors.UNDEFINED) -> _AttributeResolverFunction:
        for data_type, attribute_resolvers in self.attribute.type_map.items():
            if types.DataType.is_compatible(data_type, object_type):
                break
        else:
            raise errors.AttributeResolutionError(name, object_type, thing=thing)
        resolver = attribute_resolvers.get(name)
        if resolver is None:
            raise errors.AttributeResolutionError(name, object_type, thing=thing, suggestion=suggest_symbol(name, attribute_resolvers.keys()))
        return resolver

    def resolve_type(self, object_type: _DataTypeDef, name: str) -> _DataTypeDef:
        """
        The method to use for resolving the data type of an attribute.

        :param object_type: The data type of the object that *name* is an attribute of.
        :param str name: The name of the attribute to retrieve the data type of.
        :return: The data type of the specified attribute.
        """
        return self._get_resolver(object_type, name).resolve_type(object_type)

    @attribute('decode', types.DataType.BYTES, result_type=types.DataType.FUNCTION('decode', return_type=types.DataType.STRING, argument_types=(types.DataType.STRING,)))
    def bytes_decode(self, value: bytes) -> Callable[..., str]:
        return functools.partial(self._bytes_decode, value)

    @classmethod
    def _bytes_decode(cls, value: bytes, encoding: str) -> str:
        encoding = encoding.lower()
        if encoding == 'base16' or encoding == 'hex':
            return binascii.b2a_hex(value).decode()
        elif encoding == 'base64':
            return binascii.b2a_base64(value).decode().strip()
        try:
            return value.decode(encoding)
        except LookupError as error:
            raise errors.FunctionCallError("invalid encoding name {}".format(encoding), error=error, function_name='decode')

    @attribute('to_epoch', types.DataType.DATETIME, result_type=types.DataType.FLOAT)
    def datetime_to_epoch(self, value: datetime.datetime) -> float:
        return value.timestamp()

    @attribute('date', types.DataType.DATETIME, result_type=types.DataType.DATETIME)
    def datetime_date(self, value: datetime.datetime) -> datetime.datetime:
        return value.replace(hour=0, minute=0, second=0, microsecond=0)

    @attribute('day', types.DataType.DATETIME, result_type=types.DataType.FLOAT)
    def datetime_day(self, value: datetime.datetime) -> int:
        return value.day

    @attribute('hour', types.DataType.DATETIME, result_type=types.DataType.FLOAT)
    def datetime_hour(self, value: datetime.datetime) -> int:
        return value.hour

    @attribute('microsecond', types.DataType.DATETIME, result_type=types.DataType.FLOAT)
    def datetime_microsecond(self, value: datetime.datetime) -> int:
        return value.microsecond

    @attribute('millisecond', types.DataType.DATETIME, result_type=types.DataType.FLOAT)
    def datetime_millisecond(self, value: datetime.datetime) -> float:
        return value.microsecond / 1000

    @attribute('minute', types.DataType.DATETIME, result_type=types.DataType.FLOAT)
    def datetime_minute(self, value: datetime.datetime) -> int:
        return value.minute

    @attribute('month', types.DataType.DATETIME, result_type=types.DataType.FLOAT)
    def datetime_month(self, value: datetime.datetime) -> int:
        return value.month

    @attribute('second', types.DataType.DATETIME, result_type=types.DataType.FLOAT)
    def datetime_second(self, value: datetime.datetime) -> int:
        return value.second

    @attribute('weekday', types.DataType.DATETIME, result_type=types.DataType.STRING)
    def datetime_weekday(self, value: datetime.datetime) -> str:
        # use strftime %A so the value is localized
        return value.strftime('%A')

    @attribute('year', types.DataType.DATETIME, result_type=types.DataType.FLOAT)
    def datetime_year(self, value: datetime.datetime) -> int:
        return value.year

    @attribute('zone_name', types.DataType.DATETIME, result_type=types.DataType.STRING)
    def datetime_zone_name(self, value: datetime.datetime) -> str | None:
        return value.tzname()

    @attribute('ceiling', types.DataType.FLOAT, result_type=types.DataType.FLOAT)
    def float_ceiling(self, value: decimal.Decimal) -> decimal.Decimal | int:
        return _float_op(value, math.ceil)

    @attribute('floor', types.DataType.FLOAT, result_type=types.DataType.FLOAT)
    def float_floor(self, value: decimal.Decimal) -> decimal.Decimal | int:
        return _float_op(value, math.floor)

    @attribute('is_nan', types.DataType.FLOAT, result_type=types.DataType.BOOLEAN)
    def float_is_nan(self, value: decimal.Decimal) -> bool:
        return math.isnan(value)

    @attribute('to_flt', types.DataType.FLOAT, result_type=types.DataType.FLOAT)
    def float_to_flt(self, value: decimal.Decimal) -> decimal.Decimal:
        return value

    @attribute('to_int', types.DataType.FLOAT, result_type=types.DataType.FLOAT)
    def float_to_int(self, value: decimal.Decimal) -> decimal.Decimal:
        if not types.is_integer_number(value):
            raise errors.EvaluationError('data type mismatch (not an integer number)')
        return value

    @attribute('keys', types.DataType.MAPPING, result_type=types.DataType.ARRAY)
    def mapping_keys(self, value: dict[Any, Any]) -> tuple[Any, ...]:
        return tuple(value.keys())

    @attribute('values', types.DataType.MAPPING, result_type=types.DataType.ARRAY)
    def mapping_values(self, value: dict[Any, Any]) -> tuple[Any, ...]:
        return tuple(value.values())

    @attribute('as_lower', types.DataType.STRING, result_type=types.DataType.STRING)
    def string_as_lower(self, value: str) -> str:
        return value.lower()

    @attribute('as_upper', types.DataType.STRING, result_type=types.DataType.STRING)
    def string_as_upper(self, value: str) -> str:
        return value.upper()

    @attribute('encode', types.DataType.STRING, result_type=types.DataType.FUNCTION('encode', return_type=types.DataType.BYTES, argument_types=(types.DataType.STRING,)))
    def string_encode(self, value: str) -> Callable[..., bytes]:
        return functools.partial(self._string_encode, value)

    @classmethod
    def _string_encode(cls, value: str, encoding: str) -> bytes:
        encoding = encoding.lower()
        try:
            if encoding == 'base16' or encoding == 'hex':
                return binascii.a2b_hex(value.encode())
            elif encoding == 'base64':
                return binascii.a2b_base64(value.encode())
        except binascii.Error as error:
            raise errors.FunctionCallError("error converting to {}".format(encoding), error=error, function_name='encode')
        try:
            return value.encode(encoding)
        except LookupError as error:
            raise errors.FunctionCallError("invalid encoding name {}".format(encoding), error=error, function_name='encode')

    @attribute('to_flt', types.DataType.STRING, result_type=types.DataType.FLOAT)
    def string_to_flt(self, value: str) -> decimal.Decimal:
        value = value.strip()
        if re.match(r'-?inf', value):
            return decimal.Decimal(value)
        match = re.match(r'^(' + parser.Parser.get_token_regex('FLOAT') + ')$', value)
        if match is None:
            return decimal.Decimal('nan')
        return parser.literal_eval(match.group(0))

    @attribute('to_int', types.DataType.STRING, result_type=types.DataType.FLOAT)
    def string_to_int(self, value: str) -> decimal.Decimal:
        result = self.string_to_flt(value)
        if not types.is_integer_number(result):
            raise errors.EvaluationError('data type mismatch (not an integer number)')
        return result

    @attribute('days', types.DataType.TIMEDELTA, result_type=types.DataType.FLOAT)
    def timedelta_days(self, value: datetime.timedelta) -> int:
        return value.days

    @attribute('seconds', types.DataType.TIMEDELTA, result_type=types.DataType.FLOAT)
    def timedelta_seconds(self, value: datetime.timedelta) -> int:
        return value.seconds

    @attribute('microseconds', types.DataType.TIMEDELTA, result_type=types.DataType.FLOAT)
    def timedelta_microseconds(self, value: datetime.timedelta) -> int:
        return value.microseconds

    @attribute('total_seconds', types.DataType.TIMEDELTA, result_type=types.DataType.FLOAT)
    def timedelta_total_seconds(self, value: datetime.timedelta) -> float:
        return value.total_seconds()

    @attribute('ends_with', types.DataType.ARRAY, types.DataType.BYTES, types.DataType.STRING, type_resolver=functools.partial(_value_with_result_type, 'ends_with'))
    def value_ends_with(self, value: Sequence[Any]) -> Callable[..., bool]:
        return functools.partial(self._value_ends_with, value)

    def _value_ends_with(self, value: Sequence[Any], suffix: Sequence[Any]) -> bool:
        return value[-len(suffix):] == suffix

    @attribute('is_empty', types.DataType.ARRAY, types.DataType.BYTES, types.DataType.STRING, types.DataType.MAPPING, types.DataType.SET, result_type=types.DataType.BOOLEAN)
    def value_is_empty(self, value: Sized) -> bool:
        return len(value) == 0

    @attribute('length', types.DataType.ARRAY, types.DataType.BYTES, types.DataType.STRING, types.DataType.MAPPING, types.DataType.SET, result_type=types.DataType.FLOAT)
    def value_length(self, value: Sized) -> int:
        return len(value)

    @attribute('starts_with', types.DataType.ARRAY, types.DataType.BYTES, types.DataType.STRING, type_resolver=functools.partial(_value_with_result_type, 'starts_with'))
    def value_starts_with(self, value: Sequence[Any]) -> Callable[..., bool]:
        return functools.partial(self._value_starts_with, value)

    def _value_starts_with(self, value: Sequence[Any], prefix: Sequence[Any]) -> bool:
        return value[:len(prefix)] == prefix

    @attribute('to_ary', types.DataType.ARRAY, types.DataType.BYTES, types.DataType.SET, types.DataType.STRING, type_resolver=_value_to_ary_result_type)
    def value_to_ary(self, value: Iterable[Any]) -> tuple[Any, ...]:
        return tuple(value)

    @attribute('to_str', types.DataType.FLOAT, types.DataType.STRING, result_type=types.DataType.STRING)
    def value_to_str(self, value: decimal.Decimal | str) -> str:
        if isinstance(value, str):
            return value
        # keep the string representations consistent for nan, inf, -inf
        if value.is_nan():
            return 'nan'
        elif value.is_infinite():
            if value.is_signed():
                return '-inf'
            else:
                return 'inf'
        return str(value)

    @attribute('to_set', types.DataType.ARRAY, types.DataType.BYTES, types.DataType.SET, types.DataType.STRING, type_resolver=_value_to_set_result_type)
    def value_to_set(self, value: Iterable[Any]) -> set[Any]:
        return set(value)
