#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/types/sqlalchemy.py
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

from typing import Any, Callable, cast

from .definitions import _DataTypeDef, _NullableDataTypeDef, _ReferenceDataTypeDef
from ._object import _ObjectDataTypeDef

def _resolve_sqlalchemy_column_type(column: Any, strict: bool) -> _DataTypeDef:
    """
    Translate a SQLAlchemy column's :py:class:`~sqlalchemy.types.TypeEngine` into a :py:class:`_DataTypeDef`.
    When *strict* is ``False``, column types whose ``python_type`` raises :py:exc:`NotImplementedError`
    (typically dialect-specific types) and column types whose Python type cannot be mapped to a Rule Engine type
    fall back to :py:attr:`DataType.UNDEFINED` instead of raising :py:exc:`ValueError`.
    """
    import sqlalchemy
    # deferred to avoid the sqlalchemy.py -> datatype.py import cycle
    from .datatype import DataType
    column_type = column.type
    # Enum columns expose their member class via ``python_type``; Rule Engine has no enum data type, so they are
    # surfaced as STRING values matching how enum members typically serialize on the wire. IntEnum (and other
    # int-subclass enums) store integer values at runtime, so they map to FLOAT to match how Rule Engine already
    # represents numeric types.
    if isinstance(column_type, sqlalchemy.Enum):
        enum_class = getattr(column_type, 'enum_class', None)
        if enum_class is not None and issubclass(enum_class, int):
            return DataType.FLOAT
        return DataType.STRING
    # ARRAY columns know their element type via column.type.item_type; fall back to UNDEFINED (or raise under
    # strict) only when the element type is itself unmappable, otherwise rule authors lose parse-time checks
    # against the members
    if isinstance(column_type, sqlalchemy.ARRAY):
        item_type = column_type.item_type
        try:
            item_python_type = item_type.python_type
        except NotImplementedError:
            if strict:
                raise ValueError(
                    "can not map column {0!r} to a compatible data type: element python_type is not implemented".format(
                        column.key
                    )
                )
            return cast(_DataTypeDef, DataType.ARRAY(DataType.UNDEFINED))
        try:
            return cast(_DataTypeDef, DataType.ARRAY(DataType.from_type(item_python_type)))
        except (TypeError, ValueError):
            if strict:
                raise
            return cast(_DataTypeDef, DataType.ARRAY(DataType.UNDEFINED))
    try:
        python_type = column_type.python_type
    except NotImplementedError:
        if strict:
            raise ValueError(
                "can not map column {0!r} to a compatible data type: python_type is not implemented".format(
                    column.key
                )
            )
        return DataType.UNDEFINED
    try:
        return DataType.from_type(python_type)
    except (TypeError, ValueError):
        if strict:
            raise
        return DataType.UNDEFINED

def _resolve_sqlalchemy_relationship_type(
        relationship: Any,
        current_cls: type,
        seen: dict[type, str],
        strict: bool
) -> _DataTypeDef:
    """
    Translate a SQLAlchemy :py:class:`~sqlalchemy.orm.RelationshipProperty` into a :py:class:`_DataTypeDef`,
    recursing into the target mapped class. Collections (``uselist=True``) are wrapped in
    :py:attr:`DataType.ARRAY`. Back-references and cycles are handled via the *seen* stack: a relationship
    targeting the enclosing class emits the :py:attr:`_ObjectDataTypeDef.self` sentinel; a relationship
    targeting an ancestor class on the build stack emits an unresolved
    :py:class:`_ReferenceDataTypeDef` that the caller must resolve through the
    :py:class:`~rule_engine.engine.Context` ``type_resolver``.
    """
    # deferred to avoid the sqlalchemy.py -> datatype.py import cycle
    from .datatype import DataType
    target_cls = relationship.mapper.class_
    target: _DataTypeDef
    if target_cls is current_cls:
        target = _ObjectDataTypeDef.self
    elif target_cls in seen:
        target = _ReferenceDataTypeDef(seen[target_cls])
    else:
        target = _build_object_from_sqlalchemy(
            target_cls, target_cls.__name__, accessor=None, _seen=seen, strict=strict
        )
    if relationship.uselist:
        return cast(_DataTypeDef, DataType.ARRAY(target))
    return target

def _sqlalchemy_relationship_is_nullable(relationship: Any) -> bool:
    """
    Determine whether a SQLAlchemy relationship attribute may be :py:attr:`DataType.NULL`. Collections
    (``uselist=True``) are never nullable — the empty list is the "no items" state. Scalar relationships
    (``uselist=False``) are nullable iff any of their local foreign-key columns are nullable. When the local
    columns are not introspectable, default to nullable since the caller can always set a non-null value.
    """
    if relationship.uselist:
        return False
    local_columns = getattr(relationship, 'local_columns', None)
    if not local_columns:
        return True
    return any(bool(col.nullable) for col in local_columns)

def _build_object_from_sqlalchemy(
        cls: type,
        name: str,
        *,
        accessor: Callable[[Any, str], Any] | None,
        _seen: dict[type, str],
        strict: bool
) -> _ObjectDataTypeDef:
    import sqlalchemy
    seen = dict(_seen)
    seen[cls] = name
    mapper: Any = sqlalchemy.inspect(cls)
    attributes: dict[str, _DataTypeDef] = {}
    for column in mapper.columns:
        # column_property / expression-valued attributes show up in mapper.columns as Label / Comparator objects
        # that don't expose .nullable or a usable .type; the walker treats them as out of scope (matching the
        # docstring's stance on hybrid_property) and silently skips them
        if not isinstance(column, sqlalchemy.Column):
            continue
        attr_type = _resolve_sqlalchemy_column_type(column, strict)
        if bool(column.nullable):
            attr_type = _NullableDataTypeDef.wrap(attr_type)
        attributes[column.key] = attr_type
    for relationship in mapper.relationships:
        attr_type = _resolve_sqlalchemy_relationship_type(relationship, cls, seen, strict)
        if _sqlalchemy_relationship_is_nullable(relationship):
            attr_type = _NullableDataTypeDef.wrap(attr_type)
        attributes[relationship.key] = attr_type
    return _ObjectDataTypeDef(name, attributes=attributes, accessor=accessor)
