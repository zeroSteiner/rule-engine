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

from .definitions import _DataTypeDef, _MappingDataTypeDef, _NullableDataTypeDef, _ReferenceDataTypeDef
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
        strict: bool
) -> _DataTypeDef:
    """
    Translate a dataclass field annotation into a :py:class:`_DataTypeDef`, recursing into nested dataclasses.
    *current_cls* is the dataclass whose schema is being built right now (used to emit
    :py:class:`_SelfReferenceDataTypeDef` for direct self-references). *seen* maps each ancestor dataclass on the
    build stack to the OBJECT name it will be registered under (used to emit unresolved references for mutual
    recursion). When *strict* is ``False``, annotations that cannot be mapped to a Rule Engine type fall back to
    :py:attr:`DataType.UNDEFINED` instead of raising :py:exc:`ValueError`.
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
    if origin is not None and args:
        resolved_args = tuple(_resolve_forward_ref(arg, current_cls) for arg in args)
        contains_dataclass = any(
            isinstance(arg, type) and dataclasses.is_dataclass(arg) for arg in resolved_args
        )
        if contains_dataclass:
            origin_type = DataType.from_type(origin)
            if origin_type is DataType.ARRAY:
                return DataType.ARRAY(_resolve_dataclass_field_type(resolved_args[0], current_cls, seen, strict))
            if origin_type is DataType.SET:
                return DataType.SET(_resolve_dataclass_field_type(resolved_args[0], current_cls, seen, strict))
            if origin_type is DataType.MAPPING:
                key_type = _resolve_dataclass_field_type(resolved_args[0], current_cls, seen, strict)
                value_type = _resolve_dataclass_field_type(resolved_args[1], current_cls, seen, strict)
                return cast(_MappingDataTypeDef, DataType.MAPPING(key_type, value_type))
    try:
        return DataType.from_type(annotation)
    except (TypeError, ValueError):
        if strict:
            raise
        return DataType.UNDEFINED


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
    type_hints = typing.get_type_hints(cls)
    attributes: dict[str, _DataTypeDef] = {}
    for field in dataclasses.fields(cls):
        annotation = type_hints.get(field.name, field.type)
        unwrapped, is_nullable = _unwrap_optional(annotation)
        attr_type = _resolve_dataclass_field_type(unwrapped, cls, seen, strict)
        if is_nullable:
            attr_type = _NullableDataTypeDef.wrap(attr_type)
        attributes[field.name] = attr_type
    return _ObjectDataTypeDef(name, attributes=attributes, accessor=accessor)
