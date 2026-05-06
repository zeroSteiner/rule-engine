#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/engine/context.py
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
import collections.abc
import contextlib
import dataclasses
import datetime
import decimal
import functools
import threading
import warnings
from typing import Any, Callable, Iterator

from .. import ast  # noqa: F401 — must be imported before builtins to avoid a circular import
from .. import builtins
from .. import errors
from .. import types
from ..suggestions import suggest_symbol
from ..types import DataType, _DataTypeDef

from ._attribute_resolver import _AttributeResolver

import dateutil.tz

def _tls_getter(thread_local: threading.local, key: str, _builtins: Any) -> Any:
    # a function stub to be used with functools.partial for retrieving thread-local values
    return getattr(thread_local.storage, key)

def _default_type_resolver(_: str) -> _DataTypeDef:
    return types.DataType.UNDEFINED

def resolve_attribute(thing: Any, name: str) -> Any:
    """
    A replacement resolver function for looking up symbols as members of *thing*. This is effectively the same as
    ``thing.name``. The *thing* object can be a :py:func:`~collections.namedtuple`, a custom Python class or any other
    object. Each of the members of *thing* must be of a compatible data type.

    .. warning::
            This effectively exposes all members of *thing*. If any members are sensitive, then a custom resolver should be
            used that checks *name* against a whitelist of attributes that are allowed to be accessed.

    :param thing: The object on which the *name* attribute will be accessed.
    :param str name: The symbol name that is being resolved.
    :return: The value for the corresponding attribute *name*.
    """
    if not hasattr(thing, name):
        raise errors.SymbolResolutionError(name, thing=thing, suggestion=suggest_symbol(name, dir(thing)))
    return getattr(thing, name)

def resolve_item(thing: Any, name: str) -> Any:
    """
    A resolver function for looking up symbols as items from an object (*thing*) which supports the
    :py:class:`~collections.abc.Mapping` interface, such as a dictionary. This is effectively the same as
    ``thing['name']``. Each of the values in *thing* must be of a compatible data type.

    :param thing: The object from which the *name* item will be accessed.
    :param str name: The symbol name that is being resolved.
    :return: The value for the corresponding attribute *name*.
    """
    if not isinstance(thing, collections.abc.Mapping):
        raise errors.SymbolResolutionError(name, thing=thing)
    if name not in thing:
        raise errors.SymbolResolutionError(name, thing=thing, suggestion=suggest_symbol(name, thing.keys()))
    return thing[name]

def _type_resolver(type_map: dict[str, _DataTypeDef], name: str) -> _DataTypeDef:
    if name not in type_map:
        raise errors.SymbolResolutionError(name, suggestion=suggest_symbol(name, type_map.keys()))
    return type_map[name]

def type_resolver_from_dict(dictionary: collections.abc.Mapping[str, Any]) -> Callable[[str], _DataTypeDef]:
    """
    Return a function suitable for use as the *type_resolver* for a :py:class:`.Context` instance from a dictionary. If
    any of the values within the dictionary are not of a compatible data type, a :py:exc:`TypeError` will be raised.
    Additionally, the resulting function will raise a :py:exc:`~rule_engine.errors.SymbolResolutionError` if the symbol
    name does not exist within the dictionary.

    :param dict dictionary: A dictionary (or any other object which supports the :py:class:`~collections.abc.Mapping`
            interface) from which to create the callback function.
    :return: The callback function.
    :rtype: function
    """
    type_map = {key: value if types.DataType.is_definition(value) else types.DataType.from_value(value) for key, value in dictionary.items()}
    return functools.partial(_type_resolver, type_map)

def _collect_object_types(definition: _DataTypeDef, type_map: dict[str, _DataTypeDef], seen: set[str]) -> None:
    if DataType.is_type(definition, DataType.OBJECT):
        if definition.name in seen:
            return
        seen.add(definition.name)
        # don't overwrite an entry that was set earlier (e.g. a top-level field whose name happens to match)
        type_map.setdefault(definition.name, definition)
        for attr_type in definition.attributes.values():
            _collect_object_types(attr_type, type_map, seen)
        return
    if DataType.is_type(definition, DataType.MAPPING):
        _collect_object_types(definition.key_type, type_map, seen)
        _collect_object_types(definition.value_type, type_map, seen)
        return
    if isinstance(definition, types._CollectionDataTypeDef):
        _collect_object_types(definition.value_type, type_map, seen)
        return
    if DataType.is_type(definition, DataType.NULLABLE):
        _collect_object_types(definition.inner_type, type_map, seen)
        return

def type_resolver_from_dataclass(cls: type, *, strict: bool = True) -> Callable[[str], _DataTypeDef]:
    """
    Return a function suitable for use as the *type_resolver* for a :py:class:`.Context` instance from a Python
    :py:func:`~dataclasses.dataclass`. The dataclass's top-level fields become resolvable symbols (so a rule may
    reference them by name) and every transitively-reachable :py:attr:`~rule_engine.types.DataType.OBJECT` schema
    is registered by its OBJECT name so that cross-type references in mutually-recursive schemas resolve at parse
    time.

    The companion :py:meth:`~rule_engine.types.DataType.OBJECT.from_dataclass` is used internally to derive the
    schema; see its documentation for the supported annotation forms (primitives, generics, ``Optional``, nested
    dataclasses and self/mutual recursion). Nullable fields (annotated ``Optional[T]`` or ``T | None``) surface as
    :py:attr:`~rule_engine.types.DataType.NULLABLE` wrappers in the resolved symbol types.

    .. versionadded:: 5.0.0

    :param type cls: A class decorated with :py:func:`~dataclasses.dataclass`.
    :param bool strict: Forwarded to :py:meth:`~rule_engine.types.DataType.OBJECT.from_dataclass`. When ``True``
            (the default), a field annotated with a type that cannot be mapped to a Rule Engine data type raises
            :py:exc:`ValueError`. When ``False``, such fields fall back to
            :py:attr:`~rule_engine.types.DataType.UNDEFINED`.
    :return: The callback function.
    :rtype: function
    """
    if not dataclasses.is_dataclass(cls):
        raise TypeError('type_resolver_from_dataclass argument 1 must be a dataclass, not ' + type(cls).__name__)
    root = types.DataType.OBJECT.from_dataclass(cls.__name__, cls, strict=strict)
    type_map: dict[str, _DataTypeDef] = dict(root.attributes)
    _collect_object_types(root, type_map, set())
    return functools.partial(_type_resolver, type_map)

def type_resolver_from_sqlalchemy(cls: type, *, strict: bool = True) -> Callable[[str], _DataTypeDef]:
    """
    Return a function suitable for use as the *type_resolver* for a :py:class:`.Context` instance from a
    SQLAlchemy ORM mapped class. The class's top-level columns and relationships become resolvable symbols
    and every transitively-reachable :py:attr:`~rule_engine.types.DataType.OBJECT` schema is registered by
    its OBJECT name so that cross-type references in mutually-recursive relationship graphs resolve at parse
    time.

    The companion :py:meth:`~rule_engine.types.DataType.OBJECT.from_sqlalchemy` is used internally to derive
    the schema; see its documentation for the column → :py:class:`~rule_engine.types.DataType` mapping and
    how relationships are expanded into nested OBJECT types. Columns with ``nullable=True`` and scalar
    relationships whose local foreign-key columns are nullable surface as
    :py:attr:`~rule_engine.types.DataType.NULLABLE` wrappers in the resolved symbol types.

    SQLAlchemy is an *optional* dependency; the import is deferred until this function is actually called.

    .. versionadded:: 5.0.0

    :param type cls: A SQLAlchemy ORM mapped class.
    :param bool strict: Forwarded to :py:meth:`~rule_engine.types.DataType.OBJECT.from_sqlalchemy`. When ``True``
            (the default), a column whose ``python_type`` raises :py:exc:`NotImplementedError` or cannot be mapped
            to a Rule Engine data type raises :py:exc:`ValueError`. When ``False``, such columns fall back to
            :py:attr:`~rule_engine.types.DataType.UNDEFINED`.
    :return: The callback function.
    :rtype: function
    """
    if not hasattr(cls, '__mapper__'):
        raise TypeError(
                'type_resolver_from_sqlalchemy argument 1 must be a SQLAlchemy mapped class, not '
                + type(cls).__name__
        )
    root = types.DataType.OBJECT.from_sqlalchemy(cls.__name__, cls, strict=strict)
    type_map: dict[str, _DataTypeDef] = dict(root.attributes)
    _collect_object_types(root, type_map, set())
    return functools.partial(_type_resolver, type_map)

class _ThreadLocalStorage(object):
    """
    An object whose attributes are required to be tracked separately among multiple threads. This is to guarantee that
    if a context is used by one or more rules that are being evaluated simultaneously in multiple threads, that the
    states are kept isolated.
    """
    __slots__ = ('assignment_scopes', 'regex_groups')
    assignment_scopes: 'collections.deque[dict[str, ast.Assignment]]'
    regex_groups: tuple[str, ...] | None
    def __init__(self) -> None:
        self.assignment_scopes = collections.deque()
        self.regex_groups = None

    def reset(self) -> None:
        self.assignment_scopes.clear()
        self.regex_groups = None

class Context(object):
    """
    An object defining the context for a rule's evaluation. This can be used to change the behavior of certain aspects
    of the rule such as how symbols are resolved and what regex flags should be used.
    """
    def __init__(
                    self,
                    *,
                    regex_flags: int = 0,
                    resolver: Callable[[Any, str], Any] | None = None,
                    type_resolver: Callable[[str], _DataTypeDef] | collections.abc.Mapping[str, Any] | None = None,
                    default_timezone: str | datetime.tzinfo = 'local',
                    default_value: Any = errors.UNDEFINED,
                    decimal_context: decimal.Context | None = None,
                    mapping_attribute_lookup: bool = True
    ) -> None:
        """
        :param int regex_flags: The flags to provide to functions in the :py:mod:`re` module when calling either the
                :py:func:`~re.match` or :py:func:`~re.search` functions for comparison expressions.
        :param resolver: An optional callback function to use in place of :py:meth:`.resolve`.
        :param type_resolver: An optional callback function to use in place of :py:meth:`.resolve_type`.
        :type type_resolver: function, dict
        :param default_timezone: The default timezone to apply to :py:class:`~datetime.datetime` instances which do not
                have one specified. This is necessary for comparison operations. The value should either be a
                :py:class:`~datetime.tzinfo` instance, or a string. If *default_timzezone* is a string it must be one of the
                specially supported (case-insensitive) values of "local" or "utc".
        :type default_timezone: str, :py:class:`~datetime.tzinfo`
        :param default_value: The default value to return when resolving either a missing symbol or attribute.
        :param decimal_context: A specific :py:class:`decimal.Context` object to use for evaluation of ``FLOAT`` values.
                The default value will be taken from the current thread and will be used by all evaluations using this
                :py:class:`~rule_engine.engine.Context` regardless of the decimal context of the thread which evaluates the
                rule. This causes the rule evaluation to be consistent regardless of the calling thread.
        :param bool mapping_attribute_lookup: Whether or not to allow attribute-style access on :py:attr:`.MAPPING`
                values as a fallback to key-style lookup. When ``True`` (the default), accessing ``mapping.key`` falls
                back to ``mapping['key']`` and emits a :py:exc:`~rule_engine.errors.MappingAttributeLookupDeprecation`
                once per context. When ``False``, attribute access on a :py:attr:`.MAPPING` raises a parse-time error.
                This fallback is scheduled for removal in v6.0.

        .. versionchanged:: 2.0.0
                Added the *default_value* parameter.

        .. versionchanged:: 2.1.0
                If *type_resolver* is a dictionary, :py:func:`~.type_resolver_from_dict` will be called on it automatically
                and the result will be used as the callback.

        .. versionchanged:: 3.0.0
                Added the *decimal_context* parameter.

        .. versionchanged:: 5.0.0
                Added the *mapping_attribute_lookup* parameter.
        """
        self.regex_flags = regex_flags
        """The *regex_flags* parameter from :py:meth:`~__init__`"""
        self.symbols: set[str] = set()
        """
        The symbols that are referred to by the rule. Some or all of these will need to be resolved at evaluation time.
        This attribute can be used after a rule is generated to ensure that all symbols are valid before it is
        evaluated.
        """
        if isinstance(default_timezone, str):
            default_timezone = default_timezone.lower()
            if default_timezone == 'local':
                default_timezone = dateutil.tz.tzlocal()
            elif default_timezone == 'utc':
                default_timezone = dateutil.tz.tzutc()
            else:
                raise ValueError('unsupported timezone: ' + default_timezone)
        elif not isinstance(default_timezone, datetime.tzinfo):
            raise TypeError('invalid default_timezone type')
        self._thread_local = threading.local()
        self.default_timezone = default_timezone
        """The *default_timezone* parameter from :py:meth:`~__init__`"""
        self.default_value = default_value
        """The *default_value* parameter from :py:meth:`~__init__`"""
        self.builtins = builtins.Builtins.from_defaults(
                values={'re_groups': builtins.BuiltinValueGenerator(functools.partial(_tls_getter, self._thread_local, 'regex_groups'))},
                value_types={'re_groups': types.DataType.ARRAY(types.DataType.STRING)},
                timezone=default_timezone
        )
        """An instance of :py:class:`~rule_engine.builtins.Builtins` to provided a default set of builtin symbol values."""
        self.decimal_context = decimal_context or decimal.getcontext()
        """The *decimal_context* parameter from :py:meth:`~__init__`"""
        if isinstance(type_resolver, collections.abc.Mapping):
            type_resolver = type_resolver_from_dict(type_resolver)
        self.__type_resolver = type_resolver or _default_type_resolver
        self.__resolver = resolver or resolve_item
        self.mapping_attribute_lookup = mapping_attribute_lookup
        """The *mapping_attribute_lookup* parameter from :py:meth:`~__init__`."""
        self._mapping_fallback_lock = threading.Lock()
        self._mapping_fallback_warned = False

    def __getstate__(self) -> dict[str, Any]:
        return {
                'regex_flags': self.regex_flags,
                'symbols': self.symbols,
                'default_timezone': self.default_timezone,
                'default_value': self.default_value,
                'decimal_context': self.decimal_context,
                'mapping_attribute_lookup': self.mapping_attribute_lookup,
                '_mapping_fallback_warned': self._mapping_fallback_warned,
                '_Context__type_resolver': self.__type_resolver,
                '_Context__resolver': self.__resolver,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.regex_flags = state['regex_flags']
        self.symbols = state['symbols']
        self.default_timezone = state['default_timezone']
        self.default_value = state['default_value']
        self.decimal_context = state['decimal_context']
        self.mapping_attribute_lookup = state['mapping_attribute_lookup']
        self._mapping_fallback_warned = state['_mapping_fallback_warned']
        self.__type_resolver = state['_Context__type_resolver']
        self.__resolver = state['_Context__resolver']
        # recreate transient objects that can not be pickled
        self._thread_local = threading.local()
        self._mapping_fallback_lock = threading.Lock()
        self.builtins = builtins.Builtins.from_defaults(
                values={'re_groups': builtins.BuiltinValueGenerator(functools.partial(_tls_getter, self._thread_local, 'regex_groups'))},
                value_types={'re_groups': types.DataType.ARRAY(types.DataType.STRING)},
                timezone=self.default_timezone
        )

    @contextlib.contextmanager
    def assignments(self, *assignments: 'ast.Assignment') -> Iterator[None]:
        """
        Add the specified assignments to a thread-specific scope. This is used when an assignment originates from an
        expression.

        :param assignments: The one or more assignments to define.
        :type assignments: :py:class:`~rule_engine.ast.Assignment`
        """
        self._tls.assignment_scopes.append({assign.name: assign for assign in assignments})
        try:
            yield
        finally:
            self._tls.assignment_scopes.pop()

    @property
    def _tls(self) -> _ThreadLocalStorage:
        if not hasattr(self._thread_local, 'storage'):
            self._thread_local.storage = _ThreadLocalStorage()
        storage = self._thread_local.storage
        assert isinstance(storage, _ThreadLocalStorage)
        return storage

    def resolve(self, thing: Any, name: str, scope: str | None = None) -> Any:
        """
        The method to use for resolving symbols names to values. This function must return a compatible value for the
        specified symbol name. When a *scope* is defined, this function handles the resolution itself, however when the
        *scope* is ``None`` the resolver specified in :py:meth:`~.Context.__init__` is used which defaults to
        :py:func:`resolve_item`.

        If *name* fails to resolve, this method will raise :py:exc:`~rule_engine.errors.SymbolResolutionError`. It is
        then up to the caller to determine whether or not it is appropriate to use :py:attr:`.default_value`.

        :param thing: The object from which the *name* item will be accessed.
        :param str name: The symbol name that is being resolved.
        :return: The value for the corresponding symbol *name*.
        """
        if scope == builtins.Builtins.scope_name:
            thing = self.builtins
        if isinstance(thing, builtins.Builtins):
            return resolve_item(thing, name)
        if scope is None:
            for assignments in self._tls.assignment_scopes:
                if name in assignments:
                    return assignments[name].value
            return self.__resolver(thing, name)
        raise errors.SymbolResolutionError(name, symbol_scope=scope, thing=thing)

    __resolve_attribute = _AttributeResolver()
    def resolve_attribute(self, thing: Any, object_: Any, name: str) -> Any:
        """
        The method to use for resolving attributes from values. This function must return a compatible value for the
        specified attribute name.

        If *name* fails to resolve, this method will raise :py:exc:`~rule_engine.errors.AttributeResolutionError`. It is
        then up to the caller to determine whether or not it is appropriate to use :py:attr:`.default_value`.

        :param thing: The object from which the *object_* was retrieved.
        :param object_: The object from which the *name* attribute will be accessed.
        :param str name: The attribute name that is being resolved.
        :return: The value for the corresponding attribute *name*.
        """
        return self.__resolve_attribute(thing, object_, name)
    resolve_attribute_type = __resolve_attribute.resolve_type

    def _warn_mapping_fallback(self, attribute_name: str) -> None:
        with self._mapping_fallback_lock:
            if self._mapping_fallback_warned:
                return
            self._mapping_fallback_warned = True
        message = (
                "accessing attribute {0!r} on a MAPPING value via dot syntax is deprecated; "
                "use mapping[{0!r}] instead. This fallback will be removed in v6.0. Set "
                "Context(mapping_attribute_lookup=False) to opt out now, or filter "
                "rule_engine.errors.MappingAttributeLookupDeprecation to silence this warning."
        ).format(attribute_name)
        warnings.warn(errors.MappingAttributeLookupDeprecation(message), stacklevel=2)

    def resolve_type(self, name: str, scope: str | None = None) -> _DataTypeDef:
        """
        A method for providing type hints while the rule is being generated. This can be used to ensure that all symbol
        names are valid and that the types are appropriate for the operations being performed. It must then return one
        of the compatible data type constants if the symbol is valid or raise an exception. The default behavior is to
        return :py:data:`~rule_engine.types.DataType.UNDEFINED` for all symbols.

        :param str name: The symbol name to provide a type hint for.
        :param str scope: An optional scope name that identifies from where to resolve the name.
        :return: The type of the specified symbol.
        """
        if scope == builtins.Builtins.scope_name:
            return self.builtins.resolve_type(name)
        for assignments in self._tls.assignment_scopes:
            if name in assignments:
                value_type = assignments[name].value_type
                return value_type if value_type is not None else types.DataType.UNDEFINED
        return self.__type_resolver(name)
