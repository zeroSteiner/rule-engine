#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/types/dataclass.py
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

from __future__ import annotations

import dataclasses
import sys
import types as pytypes
import typing
from typing import Any, Callable, cast

from .. import errors
from .definitions import (
        _DATA_TYPE_UNDEFINED,
        _DataTypeDef,
        _MappingDataTypeDef,
        _NullableDataTypeDef,
        _ReferenceDataTypeDef,
        _SelfReferenceDataTypeDef,
)
from ._object import _ObjectDataTypeDef

def _resolve_forward_ref(annotation: Any, owner_cls: type) -> Any:
    """
    Resolve a string or :py:class:`typing.ForwardRef` annotation against *owner_cls*'s module globals. On
    Python 3.10, :py:func:`typing.get_type_hints` does not recurse into PEP 585 generic aliases like
    ``list['X']`` to resolve string args, so this is needed to evaluate them ourselves.
    """
    if isinstance(annotation, typing.ForwardRef):
        annotation = annotation.__forward_arg__
    if isinstance(annotation, str):
        module = sys.modules.get(owner_cls.__module__)
        globalns = getattr(module, '__dict__', {})
        try:
            return eval(annotation, globalns)
        except Exception:
            return annotation
    return annotation

def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """
    Strip a single ``None`` member from a :py:data:`typing.Union` (or PEP 604 ``X | Y``) annotation. Returns
    ``(unwrapped, is_nullable)``. If the annotation is not a Union containing ``None``, the input is returned with
    ``is_nullable=False``. Unions of more than one non-``None`` type are left intact (and ``is_nullable=True`` is
    reported); ``DataType.from_type`` will reject them downstream since Rule Engine has no union type.
    """
    from .definitions import NoneType
    origin = typing.get_origin(annotation)
    is_union = origin is typing.Union or origin is pytypes.UnionType
    if not is_union:
        return annotation, False
    args = typing.get_args(annotation)
    non_none = tuple(arg for arg in args if arg is not NoneType)
    if len(non_none) == len(args):
        return annotation, False
    if len(non_none) == 1:
        return non_none[0], True
    return annotation, True

def _resolve_dataclass_field_type(
        annotation: Any,
        current_cls: type,
        seen: dict[type, str],
        strict: bool,
        nested: bool = False
) -> _DataTypeDef:
    """
    Translate a dataclass field annotation into a :py:class:`_DataTypeDef`, recursing into nested dataclasses.
    *current_cls* is the dataclass whose schema is being built right now (used to emit
    :py:class:`_SelfReferenceDataTypeDef` for direct self-references). *seen* maps each ancestor dataclass on the
    build stack to the OBJECT name it will be registered under (used to emit unresolved references for mutual
    recursion). When *strict* is ``False``, annotations that cannot be mapped to a Rule Engine type fall back to
    :py:attr:`DataType.UNDEFINED` instead of raising. When *nested* is ``True``, which only
    :py:func:`_resolve_strict_field_type` does, dataclasses and forward references nested inside unions and
    containers are mapped too.
    """
    # deferred to avoid the dataclass.py -> datatype.py import cycle
    from .datatype import DataType
    annotation = _resolve_forward_ref(annotation, current_cls)
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        if annotation is current_cls:
            return _ObjectDataTypeDef.self
        if annotation in seen:
            return _ReferenceDataTypeDef(seen[annotation])
        return _build_object_from_dataclass(annotation, annotation.__name__, accessor=None, _seen=seen, strict=strict)

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    try:
        # the arguments of a Literal are values, which must not be evaluated as forward references
        if origin is not None and args and origin is not typing.Literal:
            resolved_args = tuple(_resolve_forward_ref(arg, current_cls) for arg in args)
            contains_dataclass = any(
                isinstance(arg, type) and dataclasses.is_dataclass(arg) for arg in resolved_args
            )
            if contains_dataclass:
                origin_type = DataType.from_type(origin)
                if origin_type is DataType.ARRAY:
                    return DataType.ARRAY(
                            _resolve_dataclass_field_type(resolved_args[0], current_cls, seen, strict, nested)
                    )
                if origin_type is DataType.SET:
                    value_type = _resolve_dataclass_field_type(resolved_args[0], current_cls, seen, strict, nested)
                    # SET rejects OBJECT members, but a self reference only becomes one when the schema is built, and a
                    # reference to another schema when a rule is parsed, which strict mode still allows for now
                    member_type = _NullableDataTypeDef.unwrap(value_type)
                    if isinstance(member_type, _SelfReferenceDataTypeDef) or (
                            isinstance(member_type, _ReferenceDataTypeDef) and not strict
                    ):
                        raise errors.EngineError('the OBJECT data type may not be used as a SET member')
                    return DataType.SET(value_type)
                if origin_type is DataType.MAPPING:
                    key_type = _resolve_dataclass_field_type(resolved_args[0], current_cls, seen, strict, nested)
                    value_type = _resolve_dataclass_field_type(resolved_args[1], current_cls, seen, strict, nested)
                    return cast(_MappingDataTypeDef, DataType.MAPPING(key_type, value_type))
        return DataType.from_type(annotation)
    except (errors.EngineError, TypeError, ValueError):
        if nested and _contains_nested_member(annotation):
            return _resolve_nested_member_type(annotation, current_cls, seen)
        # data types raise EngineError for member types they reject, such as a NULLABLE mapping key or an OBJECT set
        # member
        if strict:
            raise
        return DataType.UNDEFINED

def _contains_nested_member(annotation: Any) -> bool:
    """
    Check whether *annotation* is, or has among its arguments at any depth, a dataclass or a forward reference. On
    Python 3.10, :py:func:`typing.get_type_hints` leaves the string arguments of PEP 585 generics unevaluated.
    """
    if isinstance(annotation, (str, typing.ForwardRef)):
        return True
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return True
    # the arguments of a Literal are values, not type hints
    if typing.get_origin(annotation) is typing.Literal:
        return False
    return any(_contains_nested_member(arg) for arg in typing.get_args(annotation))

def _resolve_nested_member_type(annotation: Any, current_cls: type, seen: dict[type, str]) -> _DataTypeDef:
    """
    Map an ``Optional`` union or a ``list``, ``set`` or ``dict`` whose arguments hold a dataclass or a forward reference
    that :py:meth:`DataType.from_type` can't map, such as ``list[Address | None]``, by resolving each argument in strict
    mode. Raises when *annotation* can't be mapped this way.
    """
    from .datatype import DataType
    member, is_nullable = _unwrap_optional(annotation)
    if is_nullable and member is not annotation:
        return _NullableDataTypeDef.wrap(_resolve_dataclass_field_type(member, current_cls, seen, True, True))
    origin = typing.get_origin(annotation)
    if origin in (list, set, dict):
        args = tuple(_resolve_forward_ref(arg, current_cls) for arg in typing.get_args(annotation))
        if origin is list and len(args) == 1:
            return DataType.ARRAY(_resolve_dataclass_field_type(args[0], current_cls, seen, True, True))
        if origin is set and len(args) == 1:
            value_type = _resolve_dataclass_field_type(args[0], current_cls, seen, True, True)
            # SET rejects OBJECT members, and references only become OBJECTs later
            if isinstance(_NullableDataTypeDef.unwrap(value_type), _ReferenceDataTypeDef):
                raise errors.EngineError('the OBJECT data type may not be used as a SET member')
            return DataType.SET(value_type)
        if origin is dict and len(args) == 2:
            key_type = _resolve_dataclass_field_type(args[0], current_cls, seen, True, True)
            value_type = _resolve_dataclass_field_type(args[1], current_cls, seen, True, True)
            return cast(_MappingDataTypeDef, DataType.MAPPING(key_type, value_type))
    raise ValueError("can not map python type {0!r} to a compatible data type".format(annotation))

def _raised_while_building(error: BaseException) -> bool:
    """Check whether *error* was raised while a nested dataclass was being built, below the frame that caught it."""
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code is _build_object_from_dataclass.__code__:
            return True
        traceback = traceback.tb_next
    return False

def _resolve_strict_field_type(annotation: Any, current_cls: type, seen: dict[type, str]) -> _DataTypeDef:
    """
    Resolve a field annotation in strict mode. When it raises, the field is resolved again with the dataclasses and
    forward references nested inside unions and containers mapped too. If that fails as well, the first error is
    raised, so a field that can't be mapped raises the same exception it did before nested members were mapped.

    An error from building a nested dataclass is raised right away: the second try would build it the same way and
    fail the same way, and retrying at every level of a deep schema would take exponential time.
    """
    try:
        return _resolve_dataclass_field_type(annotation, current_cls, seen, True)
    except (errors.EngineError, TypeError, ValueError) as error:
        if _raised_while_building(error):
            raise
        try:
            return _resolve_dataclass_field_type(annotation, current_cls, seen, True, True)
        except Exception:
            pass
        raise


_UNRESOLVED = object()

def _get_field_type_hints(cls: type, strict: bool) -> dict[str, Any]:
    """
    Get the type hints of the fields of *cls* with :py:func:`typing.get_type_hints`. A forward reference that can't
    be resolved makes it raise a :py:exc:`NameError` for the whole class, so in non-strict mode each field is then
    evaluated on its own, and the ones that raise a :py:exc:`NameError` map to ``_UNRESOLVED``.
    """
    try:
        return typing.get_type_hints(cls)
    except NameError as error:
        if strict:
            raise
        name_error = error
    hints: dict[str, Any] = {}
    for field in dataclasses.fields(cls):
        # the most basic class that declares the field, whose namespaces get_type_hints evaluates it in
        owner = next(
                (
                    base for base in reversed(cls.__mro__)
                    if base.__dict__.get('__dataclass_fields__', {}).get(field.name) is field
                ),
                cls
        )
        holder = type(owner.__name__, (), {'__annotations__': {field.name: field.type}, '__module__': owner.__module__})
        module_globals = getattr(sys.modules.get(owner.__module__), '__dict__', {})
        try:
            # like get_type_hints does for a class, look names up in the module first, then in the class namespace
            field_hints = typing.get_type_hints(holder, globalns=dict(vars(owner)), localns=module_globals)
            hints[field.name] = field_hints[field.name]
        except NameError:
            hints[field.name] = _UNRESOLVED
        except Exception:
            # a field that fails for another reason keeps the class raising the error it did before
            raise name_error from None
    return hints

def _build_object_from_dataclass(
        cls: type,
        name: str,
        *,
        accessor: Callable[[Any, str], Any] | None,
        strict: bool,
        _seen: dict[type, str]
) -> _ObjectDataTypeDef:
    seen = dict(_seen)
    seen[cls] = name
    type_hints = _get_field_type_hints(cls, strict)
    attributes: dict[str, _DataTypeDef] = {}
    for field in dataclasses.fields(cls):
        annotation = type_hints.get(field.name, field.type)
        if annotation is _UNRESOLVED:
            attributes[field.name] = _DATA_TYPE_UNDEFINED
            continue
        unwrapped, is_nullable = _unwrap_optional(annotation)
        if strict:
            attr_type = _resolve_strict_field_type(unwrapped, cls, seen)
        else:
            # non-strict mode keeps mapping the nested members that only strict mode maps to UNDEFINED, because typing
            # them would change fields that resolve today
            attr_type = _resolve_dataclass_field_type(unwrapped, cls, seen, False)
        if is_nullable:
            attr_type = _NullableDataTypeDef.wrap(attr_type)
        attributes[field.name] = attr_type
    return _ObjectDataTypeDef(name, attributes=attributes, accessor=accessor)
