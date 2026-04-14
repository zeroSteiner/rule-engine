#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/types/definitions.py
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

import collections
import collections.abc
import dataclasses
import sys
import threading
import types as pytypes
import typing
from collections.abc import Mapping, Sequence
from typing import Any, Callable, ClassVar, cast

from .. import errors

_object_compare_tls = threading.local()

_PYTHON_FUNCTION_TYPE = type(lambda: None)
NoneType = type(None)

class _DataTypeDef(object):
    __slots__ = ('name', 'python_type', 'is_scalar', 'iterable_type')
    name: str
    python_type: type
    is_scalar: bool
    def __init__(self, name: str, python_type: type) -> None:
        self.name = name
        self.python_type = python_type
        self.is_scalar = True
        if '__call__' in dir(self) and self.__call__.__doc__:  # type: ignore[operator]
            # patch the call docs into the top-level class for Sphinx
            self.__class__.__doc__ = self.__call__.__doc__  # type: ignore[operator]

    @property
    def is_iterable(self) -> bool:
        return getattr(self, 'iterable_type', None) is not None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        return hash((self.python_type, self.is_scalar))

    def __repr__(self) -> str:
        return "<{} name={} python_type={} >".format(self.__class__.__name__, self.name,  self.python_type.__name__)

    @property
    def is_compound(self) -> bool:
        return not self.is_scalar

class _UndefinedDataTypeDef(_DataTypeDef):
    def __repr__(self) -> str:
        return 'UNDEFINED'

_DATA_TYPE_UNDEFINED = _UndefinedDataTypeDef('UNDEFINED', cast(type, errors.UNDEFINED))

class _CollectionDataTypeDef(_DataTypeDef):
    __slots__ = ('value_type', 'value_type_nullable')
    value_type: _DataTypeDef
    value_type_nullable: bool
    def __init__(
            self,
            name: str,
            python_type: type,
            value_type: _DataTypeDef = _DATA_TYPE_UNDEFINED,
            value_type_nullable: bool = True
    ) -> None:
        # check these three classes individually instead of using Collection which isn't available before Python v3.6
        if not issubclass(python_type, collections.abc.Container):
            raise TypeError('the specified python_type is not a container')
        if not issubclass(python_type, collections.abc.Iterable):
            raise TypeError('the specified python_type is not an iterable')
        if not issubclass(python_type, collections.abc.Sized):
            raise TypeError('the specified python_type is not a sized')
        super(_CollectionDataTypeDef, self).__init__(name, python_type)
        self.is_scalar = False
        self.value_type = value_type
        self.value_type_nullable = value_type_nullable

    @property
    def iterable_type(self) -> _DataTypeDef:  # type: ignore[override]
        return self.value_type

    def __call__(self, value_type: _DataTypeDef, value_type_nullable: bool = True) -> _CollectionDataTypeDef:
        """
        :param value_type: The type of the members.
        :param bool value_type_nullable: Whether or not members are allowed to be :py:attr:`.NULL`.
        """
        return self.__class__(
                self.name,
                self.python_type,
                value_type=value_type,
                value_type_nullable=value_type_nullable
        )

    def __repr__(self) -> str:
        return "<{} name={} python_type={} value_type={} >".format(
                self.__class__.__name__,
                self.name,
                self.python_type.__name__,
                self.value_type.name
        )

    def __eq__(self, other: object) -> bool:
        if not super().__eq__(other):
            return False
        assert isinstance(other, _CollectionDataTypeDef)
        return all((
                self.value_type == other.value_type,
                self.value_type_nullable == other.value_type_nullable
        ))

    def __hash__(self) -> int:
        return hash((self.python_type, self.is_scalar, hash((self.value_type, self.value_type_nullable))))

class _ArrayDataTypeDef(_CollectionDataTypeDef):
    pass

class _SetDataTypeDef(_CollectionDataTypeDef):
    def __init__(
            self,
            name: str,
            python_type: type,
            value_type: _DataTypeDef = _DATA_TYPE_UNDEFINED,
            value_type_nullable: bool = True
    ) -> None:
        if isinstance(value_type, _ObjectDataTypeDef):
            raise errors.EngineError('OBJECT values may not be used as SET members')
        super(_SetDataTypeDef, self).__init__(name, python_type, value_type=value_type, value_type_nullable=value_type_nullable)

class _MappingDataTypeDef(_DataTypeDef):
    __slots__ = ('key_type', 'value_type', 'value_type_nullable')
    key_type: _DataTypeDef
    value_type: _DataTypeDef
    value_type_nullable: bool
    def __init__(
            self,
            name: str,
            python_type: type,
            key_type: _DataTypeDef = _DATA_TYPE_UNDEFINED,
            value_type: _DataTypeDef = _DATA_TYPE_UNDEFINED,
            value_type_nullable: bool = True
    ) -> None:
        if not issubclass(python_type, collections.abc.Mapping):
            raise TypeError('the specified python_type is not a mapping')
        super(_MappingDataTypeDef, self).__init__(name, python_type)
        self.is_scalar = False
        # ARRAY is the only compound data type that can be used as a mapping key, this is because ARRAY's are backed by
        # Python tuple's while SET and MAPPING objects are set and dict instances, respectively which are not hashable.
        if key_type.is_compound and not isinstance(key_type, _ArrayDataTypeDef):
            raise errors.EngineError("the {} data type may not be used for mapping keys".format(key_type.name))
        self.key_type = key_type
        self.value_type = value_type
        self.value_type_nullable = value_type_nullable

    @property
    def iterable_type(self) -> _DataTypeDef:  # type: ignore[override]
        return self.key_type

    def __call__(
            self,
            key_type: _DataTypeDef,
            value_type: _DataTypeDef = _DATA_TYPE_UNDEFINED,
            value_type_nullable: bool = True
    ) -> _MappingDataTypeDef:
        """
        :param key_type: The type of the mapping keys.
        :param value_type: The type of the mapping values.
        :param bool value_type_nullable: Whether or not mapping values are allowed to be :py:attr:`.NULL`.
        """
        return self.__class__(
                self.name,
                self.python_type,
                key_type=key_type,
                value_type=value_type,
                value_type_nullable=value_type_nullable
        )

    def __repr__(self) -> str:
        return "<{} name={} python_type={} key_type={} value_type={} >".format(
                self.__class__.__name__,
                self.name,
                self.python_type.__name__,
                self.key_type.name,
                self.value_type.name
        )

    def __eq__(self, other: object) -> bool:
        if not super().__eq__(other):
            return False
        assert isinstance(other, _MappingDataTypeDef)
        return all((
                self.key_type == other.key_type,
                self.value_type == other.value_type,
                self.value_type_nullable == other.value_type_nullable
        ))

    def __hash__(self) -> int:
        return hash((self.python_type, self.is_scalar, hash((self.key_type, self.value_type, self.value_type_nullable))))

class _FunctionDataTypeDef(_DataTypeDef):
    __slots__ = ('value_name', 'return_type', 'argument_types', 'minimum_arguments')
    value_name: str | None
    return_type: _DataTypeDef
    argument_types: tuple[_DataTypeDef, ...] | _DataTypeDef
    minimum_arguments: int | _DataTypeDef
    def __init__(
            self,
            name: str,
            python_type: type,
            value_name: str | None = None,
            return_type: _DataTypeDef = _DATA_TYPE_UNDEFINED,
            argument_types: tuple[_DataTypeDef, ...] | _DataTypeDef = _DATA_TYPE_UNDEFINED,
            minimum_arguments: int | _DataTypeDef | None = None
    ) -> None:
        super(_FunctionDataTypeDef, self).__init__(name, python_type)
        self.value_name = value_name
        self.return_type = return_type
        if argument_types is _DATA_TYPE_UNDEFINED:
            if minimum_arguments is None:
                minimum_arguments = _DATA_TYPE_UNDEFINED
        else:
            if not isinstance(argument_types, collections.abc.Sequence):
                raise TypeError('argument_types must be a sequence (list or tuple)')
            if minimum_arguments is None:
                # if arguments are specified, assume that they're all required by default
                minimum_arguments = len(argument_types)
            if len(argument_types) < minimum_arguments:  # type: ignore[operator]
                raise ValueError('minimum_arguments can not be greater than the length of argument_types')
        self.argument_types = argument_types
        self.minimum_arguments = minimum_arguments

    def __call__(
            self,
            name: str,
            return_type: _DataTypeDef = _DATA_TYPE_UNDEFINED,
            argument_types: tuple[_DataTypeDef, ...] | _DataTypeDef = _DATA_TYPE_UNDEFINED,
            minimum_arguments: int | _DataTypeDef | None = None
    ) -> _FunctionDataTypeDef:
        """
        .. versionadded:: 4.0.0

        :param str name: The name of the function, e.g. "split".
        :param return_type: The data type of the functions return value.
        :param tuple argument_types: The data types of the functions arguments.
        :param int minimum_arguments: The minimum number of arguments the function requires.

        If *argument_types* is specified and *minimum_arguments* is not, then *minimum_arguments* will default to the length
        of *argument_types* effectively meaning that every defined argument is required. If
        """
        return self.__class__(
                self.name,
                self.python_type,
                value_name=name,
                return_type=return_type,
                argument_types=argument_types,
                minimum_arguments=minimum_arguments
        )
    def __repr__(self) -> str:
        return "<{} name={} python_type={} return_type={} >".format(
                self.__class__.__name__,
                self.name,
                self.python_type.__name__,
                self.return_type.name
        )

    def __eq__(self, other: object) -> bool:
        if not super().__eq__(other):
            return False
        assert isinstance(other, _FunctionDataTypeDef)
        return all((
                self.return_type == other.return_type,
                self.argument_types == other.argument_types,
                self.minimum_arguments == other.minimum_arguments
        ))

    def __hash__(self) -> int:
        return hash((self.python_type, self.is_scalar, hash((self.return_type, self.argument_types, self.minimum_arguments))))

class _ReferenceDataTypeDef(_DataTypeDef):
    """
    A forward-reference placeholder used inside an :py:class:`_ObjectDataTypeDef` schema. This is not itself a data
    type; it exists only to be resolved to an :py:class:`_ObjectDataTypeDef` — either at construction time (for
    self-references) or at rule parse time (for cross-type references) via a Context's ``type_resolver``.

    .. versionadded:: 5.0.0
    """
    __slots__ = ()
    def __init__(self, name: str) -> None:
        super(_ReferenceDataTypeDef, self).__init__(name, object)
        self.is_scalar = False

    def __repr__(self) -> str:
        return "<{} name={} (unresolved forward reference) >".format(self.__class__.__name__, self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _ReferenceDataTypeDef):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(('REFERENCE', self.name))

class _SelfReferenceDataTypeDef(_ReferenceDataTypeDef):
    """
    Sentinel value for use inside an :py:attr:`~rule_engine.types.DataType.OBJECT` attribute schema to denote
    "the enclosing ``OBJECT`` schema", resolved automatically when the schema is constructed. Prefer this over
    :py:meth:`~rule_engine.types.DataType.OBJECT.reference` for self-references, since it avoids repeating the
    schema's own name.

    .. versionadded:: 5.0.0
    """
    __slots__ = ()
    def __init__(self) -> None:
        super(_SelfReferenceDataTypeDef, self).__init__('__self__')

    def __repr__(self) -> str:
        return "<{} (self reference placeholder) >".format(self.__class__.__name__)

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
    # deferred to avoid the definitions.py -> datatype.py import cycle
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
    attributes_nullable: dict[str, bool] = {}
    for field in dataclasses.fields(cls):
        annotation = type_hints.get(field.name, field.type)
        unwrapped, is_nullable = _unwrap_optional(annotation)
        attributes[field.name] = _resolve_dataclass_field_type(unwrapped, cls, seen, strict)
        attributes_nullable[field.name] = is_nullable
    return _ObjectDataTypeDef(name, attributes=attributes, accessor=accessor, attributes_nullable=attributes_nullable)

def _resolve_sqlalchemy_column_type(column: Any, strict: bool) -> _DataTypeDef:
    """
    Translate a SQLAlchemy column's :py:class:`~sqlalchemy.types.TypeEngine` into a :py:class:`_DataTypeDef`.
    When *strict* is ``False``, column types whose ``python_type`` raises :py:exc:`NotImplementedError`
    (e.g. :py:class:`~sqlalchemy.JSON` and dialect-specific types) and column types whose Python type cannot be
    mapped to a Rule Engine type fall back to :py:attr:`DataType.UNDEFINED` instead of raising
    :py:exc:`ValueError`.
    """
    import sqlalchemy
    # deferred to avoid the definitions.py -> datatype.py import cycle
    from .datatype import DataType
    column_type = column.type
    # Enum columns expose their member class via ``python_type``; Rule Engine has no enum data type, so they are
    # surfaced as STRING values matching how enum members typically serialize on the wire
    if isinstance(column_type, sqlalchemy.Enum):
        return DataType.STRING
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
    # deferred to avoid the definitions.py -> datatype.py import cycle
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
    attributes_nullable: dict[str, bool] = {}
    for column in mapper.columns:
        attributes[column.key] = _resolve_sqlalchemy_column_type(column, strict)
        attributes_nullable[column.key] = bool(column.nullable)
    for relationship in mapper.relationships:
        attributes[relationship.key] = _resolve_sqlalchemy_relationship_type(relationship, cls, seen, strict)
        attributes_nullable[relationship.key] = _sqlalchemy_relationship_is_nullable(relationship)
    return _ObjectDataTypeDef(name, attributes=attributes, accessor=accessor, attributes_nullable=attributes_nullable)

def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    """
    Strip a single ``None`` member from a :py:data:`typing.Union` (or PEP 604 ``X | Y``) annotation. Returns
    ``(unwrapped, is_nullable)``. If the annotation is not a Union containing ``None``, the input is returned with
    ``is_nullable=False``. Unions of more than one non-``None`` type are left intact (and ``is_nullable=True`` is
    reported); ``DataType.from_type`` will reject them downstream since Rule Engine has no union type.
    """
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

def _substitute_self_references(definition: _DataTypeDef, target: _ObjectDataTypeDef) -> _DataTypeDef:
    """
    Walk a data type *definition* and replace any :py:class:`_ReferenceDataTypeDef` whose name matches *target.name*
    (or any :py:class:`_SelfReferenceDataTypeDef` sentinel) with *target*. Cross-name references are left intact for
    later resolution. Nested :py:class:`_ObjectDataTypeDef` schemas are not descended into — their own ``__init__``
    already resolved self references within their scope.
    """
    if isinstance(definition, _ReferenceDataTypeDef):
        if isinstance(definition, _SelfReferenceDataTypeDef) or definition.name == target.name:
            return target
        return definition
    if isinstance(definition, _ObjectDataTypeDef):
        return definition
    if isinstance(definition, _CollectionDataTypeDef):
        new_value_type = _substitute_self_references(definition.value_type, target)
        if new_value_type is definition.value_type:
            return definition
        return definition.__class__(
                definition.name,
                definition.python_type,
                value_type=new_value_type,
                value_type_nullable=definition.value_type_nullable
        )
    if isinstance(definition, _MappingDataTypeDef):
        new_key_type = _substitute_self_references(definition.key_type, target)
        new_value_type = _substitute_self_references(definition.value_type, target)
        if new_key_type is definition.key_type and new_value_type is definition.value_type:
            return definition
        return definition.__class__(
                definition.name,
                definition.python_type,
                key_type=new_key_type,
                value_type=new_value_type,
                value_type_nullable=definition.value_type_nullable
        )
    if isinstance(definition, _FunctionDataTypeDef):
        new_return_type = _substitute_self_references(definition.return_type, target)
        if definition.argument_types is _DATA_TYPE_UNDEFINED:
            new_argument_types: tuple[_DataTypeDef, ...] | _DataTypeDef = definition.argument_types
        else:
            assert isinstance(definition.argument_types, tuple)
            new_argument_types = tuple(_substitute_self_references(arg_type, target) for arg_type in definition.argument_types)
        if new_return_type is definition.return_type and new_argument_types is definition.argument_types:
            return definition
        return definition.__class__(
                definition.name,
                definition.python_type,
                value_name=definition.value_name,
                return_type=new_return_type,
                argument_types=new_argument_types,
                minimum_arguments=definition.minimum_arguments
        )
    return definition

class _ObjectDataTypeDef(_DataTypeDef):
    """
    A user-defined object schema. OBJECT is a nominal compound type: two OBJECT definitions are compatible iff they
    share the same ``name`` (and, for equality, structurally-equal attribute schemas). Attribute access on an OBJECT
    value is type-checked at rule parse time and fetches values via the type's :py:attr:`accessor` callable
    (defaulting to :py:func:`getattr`). Unknown attributes raise at parse time; attribute access does not fall
    through to the context's symbol resolver.

    .. versionadded:: 5.0.0
    """
    __slots__ = ('attributes', 'attributes_nullable', 'accessor')
    attributes: dict[str, _DataTypeDef]
    attributes_nullable: dict[str, bool]
    accessor: Callable[[Any, str], Any]
    # class attribute (not in __slots__) — set after class definition below; a sentinel used inside attribute
    # schemas to self-reference the enclosing OBJECT without repeating its name
    self: ClassVar[_SelfReferenceDataTypeDef]
    def __init__(
            self,
            name: str,
            python_type: type = object,
            attributes: Mapping[str, _DataTypeDef] | None = None,
            accessor: Callable[[Any, str], Any] | None = None,
            attributes_nullable: Mapping[str, bool] | None = None
    ) -> None:
        super(_ObjectDataTypeDef, self).__init__(name, python_type)
        self.is_scalar = False
        self.attributes = dict(attributes) if attributes else {}
        self.attributes_nullable = dict(attributes_nullable) if attributes_nullable else {}
        self.accessor = accessor if accessor is not None else getattr
        # resolve self-references in the attribute schema now that self exists; cross-name references are left intact
        # and will be resolved lazily at rule parse time via Context.resolve_type
        for attr_name, attr_type in list(self.attributes.items()):
            self.attributes[attr_name] = _substitute_self_references(attr_type, self)

    def __call__(
            self,
            name: str,
            attributes: Mapping[str, _DataTypeDef] | None = None,
            accessor: Callable[[Any, str], Any] | None = None,
            attributes_nullable: Mapping[str, bool] | None = None
    ) -> _ObjectDataTypeDef:
        """
        .. versionadded:: 5.0.0

        :param str name: The name of the object schema.
        :param dict attributes: A mapping of attribute names to their data type definitions. A
                :py:meth:`~rule_engine.types.DataType.OBJECT.reference` placeholder with the same ``name`` (or the
                :py:attr:`~rule_engine.types.DataType.OBJECT.self` sentinel) resolves to the new type itself,
                enabling self-referential schemas.
        :param accessor: A callable of the form ``accessor(value, attribute_name)`` used to fetch an attribute's
                value at evaluation time. Defaults to :py:func:`getattr`.
        :param dict attributes_nullable: A mapping of attribute names to a ``bool`` indicating whether the attribute
                value is allowed to be :py:attr:`.NULL`. Unspecified attributes default to ``True``.
        """
        return self.__class__(
                name,
                self.python_type,
                attributes=attributes,
                accessor=accessor,
                attributes_nullable=attributes_nullable
        )

    @staticmethod
    def reference(name: str) -> _ReferenceDataTypeDef:
        """
        Construct a forward-reference placeholder for use inside an :py:attr:`~rule_engine.types.DataType.OBJECT`
        schema. This is **not** itself a data type — it is a placeholder that resolves to an
        :py:attr:`~rule_engine.types.DataType.OBJECT` either at construction time (for self references within the
        same schema) or at rule parse time (for cross-type references) via a
        :py:class:`~rule_engine.engine.Context`'s ``type_resolver``.

        For self-references within a schema, prefer the :py:attr:`~rule_engine.types.DataType.OBJECT.self` sentinel,
        which avoids repeating the enclosing schema's name.

        .. versionadded:: 5.0.0

        :param str name: The name of the referenced OBJECT schema.
        """
        return _ReferenceDataTypeDef(name)

    @staticmethod
    def from_dataclass(
            name: str,
            cls: type,
            *,
            accessor: Callable[[Any, str], Any] | None = None,
            strict: bool = True
    ) -> _ObjectDataTypeDef:
        """
        Build an :py:attr:`~rule_engine.types.DataType.OBJECT` schema from a Python
        :py:func:`~dataclasses.dataclass`. Each field of *cls* becomes an attribute in the resulting OBJECT schema,
        with its type derived from the field annotation via :py:meth:`DataType.from_type`. Stringified annotations
        (e.g. from ``from __future__ import annotations``) are resolved using :py:func:`typing.get_type_hints`.

        Fields annotated with :py:data:`typing.Optional` (or the PEP 604 ``T | None`` form) are unwrapped to their
        non-``None`` type, and the corresponding attribute is recorded as nullable. Non-Optional fields are recorded
        as non-nullable.

        Fields whose annotation is itself a dataclass (or contains one inside a ``list``/``set``/``dict`` generic)
        produce nested OBJECT schemas. Self-references resolve to the enclosing schema via the
        :py:attr:`~rule_engine.types.DataType.OBJECT.self` sentinel; references to a dataclass already on the build
        stack (mutual recursion) become unresolved :py:meth:`~rule_engine.types.DataType.OBJECT.reference`
        placeholders that the caller must resolve via the :py:class:`~rule_engine.engine.Context` ``type_resolver``.

        .. versionadded:: 5.0.0

        :param str name: The name of the resulting OBJECT schema.
        :param type cls: A class decorated with :py:func:`~dataclasses.dataclass`.
        :param accessor: An optional accessor callable forwarded to the new schema. Defaults to :py:func:`getattr`,
            which matches normal dataclass attribute access.
        :param bool strict: When ``True`` (the default), a field annotated with a type that cannot be mapped to a
            Rule Engine data type raises :py:exc:`ValueError`. When ``False``, such fields fall back to
            :py:attr:`DataType.UNDEFINED` so the attribute remains selectable without parse-time type checking.
        """
        if not dataclasses.is_dataclass(cls):
            raise TypeError('from_dataclass argument 2 must be a dataclass, not ' + type(cls).__name__)
        return _build_object_from_dataclass(cls, name, accessor=accessor, _seen={}, strict=strict)

    @staticmethod
    def from_sqlalchemy(
            name: str,
            cls: type,
            *,
            accessor: Callable[[Any, str], Any] | None = None,
            strict: bool = True
    ) -> _ObjectDataTypeDef:
        """
        Build an :py:attr:`~rule_engine.types.DataType.OBJECT` schema from a SQLAlchemy ORM mapped class. Each
        mapped column of *cls* becomes an attribute in the resulting OBJECT schema, with its type derived from the
        column's :py:meth:`~sqlalchemy.types.TypeEngine.python_type` via :py:meth:`DataType.from_type`. Column
        nullability is taken directly from :py:attr:`~sqlalchemy.Column.nullable`.

        By default (``strict=True``) a column whose ``python_type`` raises :py:exc:`NotImplementedError`
        (e.g. :py:class:`~sqlalchemy.JSON`) or resolves to a Python type Rule Engine cannot map raises
        :py:exc:`ValueError`; pass ``strict=False`` to record such columns as :py:attr:`DataType.UNDEFINED` so
        they remain selectable without parse-time type checking. :py:class:`~sqlalchemy.Enum` columns are
        surfaced as :py:attr:`DataType.STRING`.

        Relationships declared on *cls* are expanded into nested OBJECT schemas. Collection relationships
        (``uselist=True``) are wrapped in :py:attr:`DataType.ARRAY`. Back-references to the enclosing class
        resolve to :py:attr:`~rule_engine.types.DataType.OBJECT.self`; references to a class already on the build
        stack (mutual recursion across more than two classes) become unresolved
        :py:meth:`~rule_engine.types.DataType.OBJECT.reference` placeholders that the caller must resolve via the
        :py:class:`~rule_engine.engine.Context` ``type_resolver``.

        SQLAlchemy is an *optional* dependency. The library imports cleanly without it; ``import sqlalchemy`` is
        deferred until this method is actually called and propagates :py:exc:`ImportError` if SQLAlchemy is not
        installed.

        .. versionadded:: 5.0.0

        :param str name: The name of the resulting OBJECT schema.
        :param type cls: A SQLAlchemy ORM mapped class.
        :param accessor: An optional accessor callable forwarded to the new schema. Defaults to :py:func:`getattr`,
                which matches normal attribute access on a mapped instance.
        :param bool strict: When ``True`` (the default), a column whose ``python_type`` raises
                :py:exc:`NotImplementedError` or cannot be mapped to a Rule Engine data type raises
                :py:exc:`ValueError`. When ``False``, such columns fall back to :py:attr:`DataType.UNDEFINED` so
                the attribute remains selectable without parse-time type checking. This is useful for dialect-
                specific column types (e.g. :py:class:`~sqlalchemy.JSON`) whose values can not be statically
                described.
        """
        if not hasattr(cls, '__mapper__'):
            raise TypeError('from_sqlalchemy argument 2 must be a SQLAlchemy mapped class, not ' + type(cls).__name__)
        return _build_object_from_sqlalchemy(cls, name, accessor=accessor, _seen={}, strict=strict)

    def is_attributes_nullable(self, attribute_name: str) -> bool:
        return self.attributes_nullable.get(attribute_name, True)

    def __repr__(self) -> str:
        return "<{} name={} attributes=[{}] >".format(
                self.__class__.__name__,
                self.name,
                ', '.join(self.attributes.keys())
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _ObjectDataTypeDef):
            return False
        if self.name != other.name:
            return False
        if self.attributes.keys() != other.attributes.keys():
            return False
        stack = getattr(_object_compare_tls, 'stack', None)
        if stack is None:
            stack = set()
            _object_compare_tls.stack = stack
        key = (id(self), id(other))
        if key in stack:
            # break recursive comparisons by assuming equality (standard cycle-breaking fixpoint)
            return True
        stack.add(key)
        try:
            for attr_name in self.attributes:
                if self.attributes[attr_name] != other.attributes[attr_name]:
                    return False
                if self.is_attributes_nullable(attr_name) != other.is_attributes_nullable(attr_name):
                    return False
            return True
        finally:
            stack.discard(key)

    def __hash__(self) -> int:
        # nominal hashing only: hashing the attribute schema would infinite-loop on self-references and provides no
        # benefit over name-based hashing since equality requires a full structural match anyway
        return hash(('OBJECT', self.name))

# Sentinel used inside OBJECT attribute schemas to denote "the enclosing OBJECT schema". Attached as a class attribute
# so it is available via ``DataType.OBJECT.self`` without depending on any particular OBJECT instance.
_ObjectDataTypeDef.self = _SelfReferenceDataTypeDef()
