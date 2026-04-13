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

import collections
import collections.abc
import datetime
import decimal
import threading

from .. import errors

_object_compare_tls = threading.local()

_PYTHON_FUNCTION_TYPE = type(lambda: None)
NoneType = type(None)

class _DataTypeDef(object):
    __slots__ = ('name', 'python_type', 'is_scalar', 'iterable_type')
    def __init__(self, name, python_type):
        self.name = name
        self.python_type = python_type
        self.is_scalar = True
        if '__call__' in dir(self) and self.__call__.__doc__:
            # patch the call docs into the top-level class for Sphinx
            self.__class__.__doc__ = self.__call__.__doc__

    @property
    def is_iterable(self):
        return getattr(self, 'iterable_type', None) is not None

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash((self.python_type, self.is_scalar))

    def __repr__(self):
        return "<{} name={} python_type={} >".format(self.__class__.__name__, self.name,  self.python_type.__name__)

    @property
    def is_compound(self):
        return not self.is_scalar

class _UndefinedDataTypeDef(_DataTypeDef):
    def __repr__(self):
        return 'UNDEFINED'

_DATA_TYPE_UNDEFINED = _UndefinedDataTypeDef('UNDEFINED', errors.UNDEFINED)

class _CollectionDataTypeDef(_DataTypeDef):
    __slots__ = ('value_type', 'value_type_nullable')
    def __init__(self, name, python_type, value_type=_DATA_TYPE_UNDEFINED, value_type_nullable=True):
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
    def iterable_type(self):
        return self.value_type

    def __call__(self, value_type, value_type_nullable=True):
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

    def __repr__(self):
        return "<{} name={} python_type={} value_type={} >".format(
                self.__class__.__name__,
                self.name,
                self.python_type.__name__,
                self.value_type.name
        )

    def __eq__(self, other):
        if not super().__eq__(other):
            return False
        return all((
                self.value_type == other.value_type,
                self.value_type_nullable == other.value_type_nullable
        ))

    def __hash__(self):
        return hash((self.python_type, self.is_scalar, hash((self.value_type, self.value_type_nullable))))

class _ArrayDataTypeDef(_CollectionDataTypeDef):
    pass

class _SetDataTypeDef(_CollectionDataTypeDef):
    def __init__(self, name, python_type, value_type=_DATA_TYPE_UNDEFINED, value_type_nullable=True):
        if isinstance(value_type, _ObjectDataTypeDef):
            raise errors.EngineError('OBJECT values may not be used as SET members')
        super(_SetDataTypeDef, self).__init__(name, python_type, value_type=value_type, value_type_nullable=value_type_nullable)

class _MappingDataTypeDef(_DataTypeDef):
    __slots__ = ('key_type', 'value_type', 'value_type_nullable')
    def __init__(self, name, python_type, key_type=_DATA_TYPE_UNDEFINED, value_type=_DATA_TYPE_UNDEFINED, value_type_nullable=True):
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
    def iterable_type(self):
        return self.key_type

    def __call__(self, key_type, value_type=_DATA_TYPE_UNDEFINED, value_type_nullable=True):
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

    def __repr__(self):
        return "<{} name={} python_type={} key_type={} value_type={} >".format(
                self.__class__.__name__,
                self.name,
                self.python_type.__name__,
                self.key_type.name,
                self.value_type.name
        )

    def __eq__(self, other):
        if not super().__eq__(other):
            return False
        return all((
                self.key_type == other.key_type,
                self.value_type == other.value_type,
                self.value_type_nullable == other.value_type_nullable
        ))

    def __hash__(self):
        return hash((self.python_type, self.is_scalar, hash((self.key_type, self.value_type, self.value_type_nullable))))

class _FunctionDataTypeDef(_DataTypeDef):
    __slots__ = ('value_name', 'return_type', 'argument_types', 'minimum_arguments')
    def __init__(self, name, python_type, value_name=None, return_type=_DATA_TYPE_UNDEFINED, argument_types=_DATA_TYPE_UNDEFINED, minimum_arguments=None):
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
            if len(argument_types) < minimum_arguments:
                raise ValueError('minimum_arguments can not be greater than the length of argument_types')
        self.argument_types = argument_types
        self.minimum_arguments = minimum_arguments

    def __call__(self, name, return_type=_DATA_TYPE_UNDEFINED, argument_types=_DATA_TYPE_UNDEFINED, minimum_arguments=None):
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
    def __repr__(self):
        return "<{} name={} python_type={} return_type={} >".format(
                self.__class__.__name__,
                self.name,
                self.python_type.__name__,
                self.return_type.name
        )

    def __eq__(self, other):
        if not super().__eq__(other):
            return False
        return all((
                self.return_type == other.return_type,
                self.argument_types == other.argument_types,
                self.minimum_arguments == other.minimum_arguments
        ))

    def __hash__(self):
        return hash((self.python_type, self.is_scalar, hash((self.return_type, self.argument_types, self.minimum_arguments))))

class _ReferenceDataTypeDef(_DataTypeDef):
    """
    A forward-reference placeholder used inside an :py:class:`_ObjectDataTypeDef` schema. This is not itself a data
    type; it exists only to be resolved to an :py:class:`_ObjectDataTypeDef` — either at construction time (for
    self-references) or at rule parse time (for cross-type references) via a Context's ``type_resolver``.

    .. versionadded:: 5.0.0
    """
    __slots__ = ()
    def __init__(self, name):
        super(_ReferenceDataTypeDef, self).__init__(name, object)
        self.is_scalar = False

    def __repr__(self):
        return "<{} name={} (unresolved forward reference) >".format(self.__class__.__name__, self.name)

    def __eq__(self, other):
        if not isinstance(other, _ReferenceDataTypeDef):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(('REFERENCE', self.name))

def _substitute_self_references(definition, target):
    """
    Walk a data type *definition* and replace any :py:class:`_ReferenceDataTypeDef` whose name matches *target.name*
    with *target*. Cross-name references are left intact for later resolution. Nested :py:class:`_ObjectDataTypeDef`
    schemas are not descended into — their own ``__init__`` already resolved self references within their scope.
    """
    if isinstance(definition, _ReferenceDataTypeDef):
        if definition.name == target.name:
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
            new_argument_types = definition.argument_types
        else:
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
    def __init__(self, name, python_type=object, attributes=None, accessor=None, attributes_nullable=None):
        super(_ObjectDataTypeDef, self).__init__(name, python_type)
        self.is_scalar = False
        self.attributes = dict(attributes) if attributes else {}
        self.attributes_nullable = dict(attributes_nullable) if attributes_nullable else {}
        self.accessor = accessor if accessor is not None else getattr
        # resolve self-references in the attribute schema now that self exists; cross-name references are left intact
        # and will be resolved lazily at rule parse time via Context.resolve_type
        for attr_name, attr_type in list(self.attributes.items()):
            self.attributes[attr_name] = _substitute_self_references(attr_type, self)

    def __call__(self, name, attributes=None, accessor=None, attributes_nullable=None):
        """
        .. versionadded:: 5.0.0

        :param str name: The name of the object schema.
        :param dict attributes: A mapping of attribute names to their data type definitions. A
                :py:func:`~.DataType.reference` placeholder with the same ``name`` resolves to the new type itself,
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

    def is_attributes_nullable(self, attribute_name):
        return self.attributes_nullable.get(attribute_name, True)

    def __repr__(self):
        return "<{} name={} attributes=[{}] >".format(
                self.__class__.__name__,
                self.name,
                ', '.join(self.attributes.keys())
        )

    def __eq__(self, other):
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

    def __hash__(self):
        # nominal hashing only: hashing the attribute schema would infinite-loop on self-references and provides no
        # benefit over name-based hashing since equality requires a full structural match anyway
        return hash(('OBJECT', self.name))
