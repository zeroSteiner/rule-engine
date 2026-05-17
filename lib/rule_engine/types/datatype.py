#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/types/datatype.py
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

import collections.abc
import datetime
import decimal
import types as pytypes
import typing
from typing import Any, TypeGuard, overload

from .definitions import (
        _ArrayDataTypeDef,
        _DATA_TYPE_UNDEFINED,
        _DataTypeDef,
        _FunctionDataTypeDef,
        _MappingDataTypeDef,
        _NullableDataTypeDef,
        _PYTHON_FUNCTION_TYPE,
        _ReferenceDataTypeDef,
        _SetDataTypeDef,
        NoneType,
)
from ._object import _ObjectDataTypeDef

def iterable_member_value_type(python_value: Any) -> _DataTypeDef:
    """
    Take a native *python_value* and return the corresponding data type of each of its members if the types are either
    the same or NULL. NULL is considered a special case to allow nullable-values. This by extension means that an
    iterable may not be defined as only capable of containing NULL values.

    :return: The data type of the sequence members. This will never be NULL, because that is considered a special case.
            It will either be UNSPECIFIED or one of the other types.
    """
    subvalue_types = set()
    for subvalue in python_value:
        if DataType.is_definition(subvalue):
            subvalue_type = subvalue
        else:
            try:
                subvalue_type = DataType.from_value(subvalue)
            except TypeError:
                # unknown runtime values (e.g. OBJECT instances) are left for the declared type to validate
                subvalue_type = _DATA_TYPE_UNDEFINED
        subvalue_types.add(subvalue_type)
    if DataType.NULL in subvalue_types:
        # treat NULL as a special case, allowing typed arrays to be a specified type *or* NULL
        # this however makes it impossible to define an array with a type of NULL
        subvalue_types.remove(DataType.NULL)
    if len(subvalue_types) == 1:
        subvalue_type = subvalue_types.pop()
    else:
        subvalue_type = DataType.UNDEFINED
    return subvalue_type

class DataTypeMeta(type):
    _members_: tuple[str, ...]

    def __new__(metacls, cls: str, bases: tuple[type, ...], classdict: dict[str, Any]) -> 'DataTypeMeta':
        data_type = super().__new__(metacls, cls, bases, classdict)
        members = []
        for key, value in classdict.items():
            if not key.upper() == key:
                continue
            if not isinstance(value, _DataTypeDef):
                continue
            members.append(key)
        data_type._members_ = tuple(members)
        return data_type

    def __contains__(cls, item: object) -> bool:
        return item in cls._members_

    def __getitem__(cls, item: str) -> _DataTypeDef:
        if item not in cls._members_:
            raise KeyError(item)
        return getattr(cls, item)

    def __iter__(cls) -> 'collections.abc.Iterator[str]':
        yield from cls._members_

    def __len__(cls) -> int:
        return len(cls._members_)

class DataType(metaclass=DataTypeMeta):
    """
    A collection of constants representing the different supported data types. There are three ways to compare data
    types. All three are effectively the same when dealing with scalars.

    Equality checking
      .. code-block::

        dt == DataType.TYPE

      This is the most explicit form of testing and when dealing with compound data types, it recursively checks that
      all of the member types are also equal.

    Type checking
      .. code-block::

        DataType.is_type(dt, DataType.TYPE)

      This checks that the data type belongs to the same family as the given sentinel. For scalar types this is
      equivalent to an equality check; for compound types (e.g. :py:attr:`.ARRAY`, :py:attr:`.MAPPING`) it matches
      any parameterization of that type without inspecting member types. When used in an ``if`` branch mypy narrows
      the type of *dt* to the matching concrete class (e.g. after ``DataType.is_type(dt, DataType.NULLABLE)`` mypy
      knows *dt* is a :py:class:`~rule_engine.types._NullableDataTypeDef`).

    Compatibility checking
      .. code-block::

        DataType.is_compatible(dt, DataType.TYPE)

      This checks that the types are compatible without any kind of conversion. When dealing with compound data types,
      this ensures that the member types are either the same or :py:attr:`~.UNDEFINED`.
    """
    ARRAY = _ArrayDataTypeDef('ARRAY', tuple)
    BYTES = _DataTypeDef('BYTES', bytes)
    BOOLEAN = _DataTypeDef('BOOLEAN', bool)
    DATETIME = _DataTypeDef('DATETIME', datetime.datetime)
    FLOAT = _DataTypeDef('FLOAT', decimal.Decimal)
    FUNCTION = _FunctionDataTypeDef('FUNCTION', _PYTHON_FUNCTION_TYPE)
    MAPPING = _MappingDataTypeDef('MAPPING', dict)
    NULL = _DataTypeDef('NULL', NoneType)
    NULLABLE = _NullableDataTypeDef('NULLABLE', object)
    OBJECT = _ObjectDataTypeDef('OBJECT', object)
    SET = _SetDataTypeDef('SET', set)
    STRING = _DataTypeDef('STRING', str)
    TIMEDELTA = _DataTypeDef('TIMEDELTA', datetime.timedelta)
    UNDEFINED = _DATA_TYPE_UNDEFINED
    """
    Undefined values. This constant can be used to indicate that a particular symbol is valid, but it's data type is
    currently unknown.
    """
    @classmethod
    def from_name(cls, name: str) -> _DataTypeDef:
        """
        Get the data type from its name.

        .. versionadded:: 2.0.0

        :param str name: The name of the data type to retrieve.
        :return: One of the constants.
        """
        if not isinstance(name, str):
            raise TypeError('from_name argument 1 must be str, not ' + type(name).__name__)
        dt = getattr(cls, name, None)
        if not isinstance(dt, _DataTypeDef):
            raise ValueError("can not map name {0!r} to a compatible data type".format(name))
        return dt

    @classmethod
    def from_type(cls, python_type: Any) -> _DataTypeDef:
        """
        Get the supported data type constant for the specified Python type/type hint. If the type or typehint can not be
        mapped to a supported data type, then a :py:exc:`ValueError` exception will be raised. This function will not
        return :py:attr:`.UNDEFINED`.

        :param type python_type: The native Python type or type hint to retrieve the corresponding type constant for.
        :return: One of the constants.

        .. versionchanged:: 4.1.0
                Added support for typehints.
        """
        if not (isinstance(python_type, type) or hasattr(python_type, '__origin__')):
            raise TypeError('from_type argument 1 must be a type or a type hint, not ' + type(python_type).__name__)
        # Optional[X] / X | None resolve to NULLABLE(from_type(X)); unions of more than one non-None member are
        # unsupported because Rule Engine has no sum type
        origin = typing.get_origin(python_type)
        if origin is typing.Union or origin is pytypes.UnionType:
            args = typing.get_args(python_type)
            non_none = tuple(arg for arg in args if arg is not NoneType)
            if len(non_none) == 1 and len(args) == 2:
                return cls.NULLABLE(cls.from_type(non_none[0]))
            raise ValueError("can not map python type {0!r} to a compatible data type".format(python_type))
        if python_type in (list, range, tuple):
            return cls.ARRAY
        elif python_type is bool:
            return cls.BOOLEAN
        elif python_type is bytes:
            return cls.BYTES
        elif python_type is datetime.date or python_type is datetime.datetime:
            return cls.DATETIME
        elif python_type is datetime.timedelta:
            return cls.TIMEDELTA
        elif python_type in (decimal.Decimal, float, int):
            return cls.FLOAT
        elif python_type is dict:
            return cls.MAPPING
        elif python_type is NoneType:
            return cls.NULL
        elif python_type is set:
            return cls.SET
        elif python_type is str:
            return cls.STRING
        elif python_type is _PYTHON_FUNCTION_TYPE:
            return cls.FUNCTION
        elif hasattr(python_type, "__origin__"):
            origin_python_type = python_type.__origin__
            maintype = cls.from_type(origin_python_type)
            if origin_python_type in (list, tuple, set):
                if hasattr(python_type, "__args__") and origin_python_type is not tuple:
                    valuetype = cls.from_type(python_type.__args__[0])
                    return maintype(valuetype)  # type: ignore[operator]
            if origin_python_type is dict:
                if hasattr(python_type, "__args__"):
                    key_type = cls.from_type(python_type.__args__[0])
                    value_type = cls.from_type(python_type.__args__[1])
                    return maintype(key_type, value_type)  # type: ignore[operator]
            return maintype
        raise ValueError("can not map python type {0!r} to a compatible data type".format(python_type.__name__))

    @classmethod
    def from_value(cls, python_value: Any) -> _DataTypeDef:
        """
        Get the supported data type constant for the specified Python value. If the value can not be mapped to a
        supported data type, then a :py:exc:`TypeError` exception will be raised. This function will not return
        :py:attr:`.UNDEFINED`.

        :param python_value: The native Python value to retrieve the corresponding data type constant for.
        :return: One of the constants.
        """
        if isinstance(python_value, bool):
            return cls.BOOLEAN
        elif isinstance(python_value, bytes):
            return cls.BYTES
        elif isinstance(python_value, (datetime.date, datetime.datetime)):
            return cls.DATETIME
        elif isinstance(python_value, datetime.timedelta):
            return cls.TIMEDELTA
        elif isinstance(python_value, (decimal.Decimal, float, int)):
            return cls.FLOAT
        elif python_value is None:
            return cls.NULL
        elif isinstance(python_value, (set,)):
            return cls.SET(value_type=iterable_member_value_type(python_value))
        elif isinstance(python_value, (str,)):
            return cls.STRING
        elif isinstance(python_value, collections.abc.Mapping):
            return cls.MAPPING(
                    key_type=iterable_member_value_type(python_value.keys()),
                    value_type=iterable_member_value_type(python_value.values())
            )
        elif isinstance(python_value, collections.abc.Sequence):
            return cls.ARRAY(value_type=iterable_member_value_type(python_value))
        elif callable(python_value):
            return cls.FUNCTION
        raise TypeError("can not map python type {0!r} to a compatible data type".format(type(python_value).__name__))

    @classmethod
    def is_compatible(cls, dt1: _DataTypeDef, dt2: _DataTypeDef) -> bool:
        """
        Check if two data type definitions are compatible without any kind of conversion. This evaluates to ``True``
        when one or both are :py:attr:`.UNDEFINED` or both types are the same. In the case of compound data types (such
        as :py:attr:`.ARRAY`) the member types are checked recursively in the same manner.

        .. versionadded:: 2.1.0

        :param dt1: The first data type to compare.
        :param dt2: The second data type to compare.
        :return: Whether or not the two types are compatible.
        :rtype: bool
        """
        if not (cls.is_definition(dt1) and cls.is_definition(dt2)):
            raise TypeError('argument is not a data type definition')
        if dt1 is _DATA_TYPE_UNDEFINED or dt2 is _DATA_TYPE_UNDEFINED:
            return True
        # unresolved forward references are treated as compatible with anything; actual resolution happens at rule
        # parse time via Context.resolve_type
        if isinstance(dt1, _ReferenceDataTypeDef) or isinstance(dt2, _ReferenceDataTypeDef):
            return True
        # NULLABLE is a parse-time marker: a NULLABLE(T) value is T-or-NULL at runtime, so it is compatible with
        # T (non-null case), with NULL (null case), and with another NULLABLE whose inner type is compatible.
        # This check is symmetric; argument-position strictness (rejecting NULLABLE(T) where plain T is required)
        # lives at the caller.
        if isinstance(dt1, _NullableDataTypeDef) or isinstance(dt2, _NullableDataTypeDef):
            if dt1 == cls.NULL or dt2 == cls.NULL:
                return True
            inner1 = dt1.inner_type if isinstance(dt1, _NullableDataTypeDef) else dt1
            inner2 = dt2.inner_type if isinstance(dt2, _NullableDataTypeDef) else dt2
            return cls.is_compatible(inner1, inner2)
        if dt1.is_scalar and dt2.is_scalar:
            if DataType.is_type(dt1, DataType.FUNCTION) and DataType.is_type(dt2, DataType.FUNCTION):
                if not cls.is_compatible(dt1.return_type, dt2.return_type):
                    return False
                if dt1.argument_types != _DATA_TYPE_UNDEFINED and dt2.argument_types != _DATA_TYPE_UNDEFINED:
                    assert isinstance(dt1.argument_types, tuple) and isinstance(dt2.argument_types, tuple)
                    if len(dt1.argument_types) != len(dt2.argument_types):
                        return False
                    if not all(cls.is_compatible(arg1_dt, arg2_dt) for (arg1_dt, arg2_dt) in zip(dt1.argument_types, dt2.argument_types)):
                        return False
                if dt1.minimum_arguments != _DATA_TYPE_UNDEFINED and dt2.minimum_arguments != _DATA_TYPE_UNDEFINED:
                    if dt1.minimum_arguments != dt2.minimum_arguments:
                        return False
                return True
            return dt1 == dt2
        elif dt1.is_compound and dt2.is_compound:
            if DataType.is_type(dt1, DataType.ARRAY) and DataType.is_type(dt2, DataType.ARRAY):
                return cls.is_compatible(dt1.value_type, dt2.value_type)
            elif DataType.is_type(dt1, DataType.MAPPING) and DataType.is_type(dt2, DataType.MAPPING):
                if not cls.is_compatible(dt1.key_type, dt2.key_type):
                    return False
                if not cls.is_compatible(dt1.value_type, dt2.value_type):
                    return False
                return True
            elif DataType.is_type(dt1, DataType.SET) and DataType.is_type(dt2, DataType.SET):
                return cls.is_compatible(dt1.value_type, dt2.value_type)
            elif DataType.is_type(dt1, DataType.OBJECT) and DataType.is_type(dt2, DataType.OBJECT):
                # bare DataType.OBJECT acts as a wildcard, mirroring how an untyped ARRAY (value_type UNDEFINED)
                # matches any typed ARRAY via its value_type compatibility check
                if dt1 is DataType.OBJECT or dt2 is DataType.OBJECT:
                    return True
                return dt1.name == dt2.name
        return False

    @classmethod
    def is_definition(cls, value: Any) -> bool:
        """
        Check if *value* is a data type definition.

        .. versionadded:: 2.1.0

        :param value: The value to check.
        :return: ``True`` if *value* is a data type definition.
        :rtype: bool
        """
        return isinstance(value, _DataTypeDef)

    @classmethod
    @overload
    def is_type(cls, dt: _DataTypeDef, kind: _ArrayDataTypeDef) -> TypeGuard[_ArrayDataTypeDef]: ...
    @classmethod
    @overload
    def is_type(cls, dt: _DataTypeDef, kind: _FunctionDataTypeDef) -> TypeGuard[_FunctionDataTypeDef]: ...
    @classmethod
    @overload
    def is_type(cls, dt: _DataTypeDef, kind: _MappingDataTypeDef) -> TypeGuard[_MappingDataTypeDef]: ...
    @classmethod
    @overload
    def is_type(cls, dt: _DataTypeDef, kind: _NullableDataTypeDef) -> TypeGuard[_NullableDataTypeDef]: ...
    @classmethod
    @overload
    def is_type(cls, dt: _DataTypeDef, kind: _ObjectDataTypeDef) -> TypeGuard[_ObjectDataTypeDef]: ...
    @classmethod
    @overload
    def is_type(cls, dt: _DataTypeDef, kind: _SetDataTypeDef) -> TypeGuard[_SetDataTypeDef]: ...
    @classmethod
    @overload
    def is_type(cls, dt: _DataTypeDef, kind: _DataTypeDef) -> bool: ...
    @classmethod
    def is_type(cls, dt: _DataTypeDef, kind: _DataTypeDef) -> bool:
        """
        Check if *dt* is the same base type as *kind*, ignoring member types for compound types. This is the
        preferred replacement for ``isinstance(dt, DataType.TYPE.__class__)``.

        For scalar types (e.g. :py:attr:`.STRING`, :py:attr:`.BOOLEAN`) *kind* is a singleton so this is
        equivalent to an equality check. For compound types (e.g. :py:attr:`.ARRAY`, :py:attr:`.MAPPING`,
        :py:attr:`.OBJECT`) it checks the type family without inspecting member / key / value types — use
        :py:meth:`is_compatible` when those matter.

        .. versionadded:: 5.0.0

        :param dt: The data type to test.
        :param kind: The base type to test against (e.g. ``DataType.ARRAY``).
        :return: ``True`` if *dt* belongs to the same type family as *kind*.
        :rtype: bool
        """
        if type(kind) is _DataTypeDef:
            return dt is kind
        return isinstance(dt, type(kind))
