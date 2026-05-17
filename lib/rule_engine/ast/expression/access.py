#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/expression/access.py
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
import operator
from typing import TYPE_CHECKING, Any

from ... import builtins as _builtins
from ... import errors
from ...suggestions import suggest_symbol
from ...types import DataType, coerce_value
from ...types import _DataTypeDef

from ..base import (
        ExpressionBase,
        LiteralExpressionBase,
        _assert_is_integer_number,
        _assert_not_nullable,
        _is_reduced,
        _resolve_type,
)
from ..literal import BooleanExpression, NullExpression

if TYPE_CHECKING:
    from ...engine.context import Context

class ContainsExpression(ExpressionBase):
    """An expression used to test whether an item exists within a container."""
    __slots__ = ('container', 'member')
    result_type: _DataTypeDef = DataType.BOOLEAN
    def __init__(self, context: 'Context', container: ExpressionBase, member: ExpressionBase) -> None:
        _assert_not_nullable(container.result_type, role='containment container')
        container_type = container.result_type
        member_type = DataType.NULLABLE.unwrap(member.result_type)
        if container_type == DataType.BYTES or container_type == DataType.STRING:
            if member_type != DataType.UNDEFINED and member_type != container_type:
                raise errors.EvaluationError('data type mismatch')
        elif DataType.is_type(_resolve_type(container_type, context), DataType.OBJECT):
            raise errors.EvaluationError('data type mismatch (containment check on OBJECT)')
        elif container_type != DataType.UNDEFINED and container_type.is_scalar:
            raise errors.EvaluationError('data type mismatch')
        self.context = context
        self.member = member
        self.container = container

    @classmethod
    def build(cls, context: 'Context', container: ExpressionBase, member: ExpressionBase) -> ExpressionBase:  # type: ignore[override]
        container_built = container.build()
        assert isinstance(container_built, ExpressionBase)
        member_built = member.build()
        assert isinstance(member_built, ExpressionBase)
        reduced = cls(context, container_built, member_built).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def __repr__(self) -> str:
        return "<{0} container={1!r} member={2!r} >".format(self.__class__.__name__, self.container, self.member)

    def evaluate(self, thing: Any) -> bool:
        container_value = self.container.evaluate(thing)
        container_value_type = DataType.from_value(container_value)
        member_value = self.member.evaluate(thing)
        if container_value_type == DataType.BYTES or container_value_type == DataType.STRING:
            if DataType.from_value(member_value) != container_value_type:
                raise errors.EvaluationError('data type mismatch')
        return bool(member_value in container_value)

    def reduce(self) -> ExpressionBase:
        if not _is_reduced(self.container, self.member):
            return self
        return BooleanExpression(self.context, self.evaluate(None))

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        super(ContainsExpression, self).to_graphviz(digraph, *args, **kwargs)
        self.container.to_graphviz(digraph, *args, **kwargs)
        self.member.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.container)), label='container')
        digraph.edge(str(id(self)), str(id(self.member)), label='member')

class GetAttributeExpression(ExpressionBase):
    """A class representing an expression in which *name* is retrieved as an attribute of *object*."""
    __slots__ = ('name', 'object', 'safe', '_object_type')
    def __init__(self, context: 'Context', object_: ExpressionBase, name: str, safe: bool = False) -> None:
        """
        :param context: The context to use for evaluating the expression.
        :type context: :py:class:`~rule_engine.engine.Context`
        :param object_: The parent object from which to retrieve the attribute.
        :param str name: The name of the attribute to retrieve.
        :param bool safe: Whether or not the safe version should be invoked.

        .. versionchanged:: 2.4.0
                Added the *safe* parameter.
        """
        self.context = context
        self.object = object_
        self._object_type = None
        if not safe:
            _assert_not_nullable(self.object.result_type, role='attribute access target')
        object_type = DataType.NULLABLE.unwrap(self.object.result_type)
        if object_type != DataType.UNDEFINED:
            if not (object_type == DataType.NULL and safe):
                resolved_object_type = _resolve_type(object_type, context)
                if DataType.is_type(resolved_object_type, DataType.OBJECT):
                    if name not in resolved_object_type.attributes:
                        raise errors.ObjectAttributeError(
                                name,
                                resolved_object_type,
                                suggestion=suggest_symbol(name, resolved_object_type.attributes.keys())
                        )
                    self._object_type = resolved_object_type
                    attribute_type = _resolve_type(resolved_object_type.attributes[name], context)
                    self.result_type = attribute_type
                else:
                    try:
                        self.result_type = context.resolve_attribute_type(object_type, name)
                    except errors.AttributeResolutionError as error:
                        # this is necessary because MAPPING objects can have their keys accessed as attributes
                        if not DataType.is_type(object_type, DataType.MAPPING):
                            raise error
                        if not context.mapping_attribute_lookup:
                            raise errors.EvaluationError(
                                    "attribute access on a MAPPING is disabled - use mapping[{0!r}] instead, "
                                    "or set mapping_attribute_lookup=True on the Context for v4-compatible "
                                    "behavior (deprecated, removal scheduled for v6.0)".format(name)
                            )
                        # leave the result type undefined because the name could be a mapping key or attribute
                if DataType.is_type(self.object.result_type, DataType.NULLABLE) and self.result_type != DataType.UNDEFINED:
                    self.result_type = DataType.NULLABLE.wrap(self.result_type)
        self.name = name
        self.safe = safe

    @classmethod
    def build(cls, context: 'Context', object_: ExpressionBase, name: str, safe: bool = False) -> ExpressionBase:  # type: ignore[override]
        object_built = object_.build()
        assert isinstance(object_built, ExpressionBase)
        reduced = cls(context, object_built, name, safe=safe).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def __repr__(self) -> str:
        return "<{0} name={1!r} >".format(self.__class__.__name__, self.name)

    def evaluate(self, thing: Any) -> Any:
        resolved_obj = self.object.evaluate(thing)
        if resolved_obj is None and self.safe:
            return resolved_obj
        if resolved_obj is None and DataType.is_type(self.object.result_type, DataType.NULLABLE):
            raise errors.EvaluationError(
                    "attribute access on a null value (use ?. to safely navigate a NULLABLE expression)"
            )

        if self._object_type is not None:
            try:
                value = self._object_type.accessor(resolved_obj, self.name)
            except (AttributeError, KeyError):
                default_value = self.context.default_value
                if default_value is errors.UNDEFINED:
                    raise errors.ObjectAttributeError(
                            self.name,
                            self._object_type,
                            thing=thing,
                            suggestion=suggest_symbol(self.name, self._object_type.attributes.keys())
                    ) from None
                value = default_value
            return self._new_value(value, verify_type=False)

        attribute_error = None
        try:
            value = self.context.resolve_attribute(thing, resolved_obj, self.name)
        except errors.AttributeResolutionError as error:
            attribute_error = error
        else:
            return self._new_value(value, verify_type=False)

        if isinstance(resolved_obj, collections.abc.Mapping) and not isinstance(resolved_obj, _builtins.Builtins):
            if not self.context.mapping_attribute_lookup:
                raise attribute_error
            self.context._warn_mapping_fallback(self.name)

        try:
            value = self.context.resolve(resolved_obj, self.name)
        except errors.SymbolResolutionError as symbol_error:
            default_value = self.context.default_value
            if default_value is errors.UNDEFINED:
                suggestion = attribute_error.suggestion or symbol_error.suggestion
                if attribute_error.suggestion and symbol_error.suggestion:
                    # if there are two suggestions, select the best one
                    suggestion = suggest_symbol(self.name, (attribute_error.suggestion, symbol_error.suggestion))
                attribute_error.suggestion = suggestion
                raise attribute_error from None
            value = default_value
        return self._new_value(value, verify_type=False)

    def reduce(self) -> ExpressionBase:
        if not _is_reduced(self.object):
            return self
        literal = LiteralExpressionBase.from_value(self.context, self.evaluate(None))
        if literal.result_type == DataType.FUNCTION and DataType.is_compatible(self.result_type, DataType.FUNCTION):
            literal.result_type = self.result_type
        return literal

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        digraph.node(str(id(self)), "{}\nname={!r}".format(self.__class__.__name__, self.name))
        self.object.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.object)))

class GetItemExpression(ExpressionBase):
    """A class representing an expression in which an *item* is retrieved from a container *object*."""
    __slots__ = ('container', 'item', 'safe')
    def __init__(self, context: 'Context', container: ExpressionBase, item: ExpressionBase, safe: bool = False) -> None:
        """
        :param context: The context to use for evaluating the expression.
        :type context: :py:class:`~rule_engine.engine.Context`
        :param container: The container object from which to retrieve the item.
        :param str item: The item to retrieve from the container.
        :param bool safe: Whether or not the safe version should be invoked.

        .. versionchanged:: 2.4.0
                Added the *safe* parameter.
        """
        self.context = context
        self.container = container
        if not safe:
            _assert_not_nullable(container.result_type, role='item access container')
        container_type = DataType.NULLABLE.unwrap(container.result_type)
        resolved_container_type = _resolve_type(container_type, context)
        if container_type == DataType.BYTES:
            if not DataType.is_compatible(item.result_type, DataType.FLOAT):
                raise errors.EvaluationError('data type mismatch (not an integer number)')
            self.result_type = DataType.FLOAT
        elif container_type == DataType.STRING:
            if not DataType.is_compatible(item.result_type, DataType.FLOAT):
                raise errors.EvaluationError('data type mismatch (not an integer number)')
            self.result_type = DataType.STRING
        elif DataType.is_type(resolved_container_type, DataType.ARRAY):
            if not DataType.is_compatible(item.result_type, DataType.FLOAT):
                raise errors.EvaluationError('data type mismatch (not an integer number)')
            self.result_type = _resolve_type(resolved_container_type.value_type, context)
        elif DataType.is_type(resolved_container_type, DataType.MAPPING):
            if not (safe or DataType.is_compatible(item.result_type, resolved_container_type.key_type)):
                raise errors.LookupError(errors.UNDEFINED, errors.UNDEFINED)
            self.result_type = _resolve_type(resolved_container_type.value_type, context)
        elif DataType.is_type(resolved_container_type, DataType.SET):
            raise errors.EvaluationError('data type mismatch (container is a set)')
        elif DataType.is_type(resolved_container_type, DataType.OBJECT):
            raise errors.EvaluationError(
                    "data type mismatch (item access on OBJECT - use {0}.attribute instead)".format(resolved_container_type.name)
            )
        elif container_type != DataType.UNDEFINED:
            if not (container_type == DataType.NULL and safe):
                raise errors.EvaluationError('data type mismatch')
        if DataType.is_type(container.result_type, DataType.NULLABLE) and self.result_type != DataType.UNDEFINED:
            self.result_type = DataType.NULLABLE.wrap(self.result_type)
        self.item = item
        self.safe = safe

    @classmethod
    def build(cls, context: 'Context', container: ExpressionBase, item: ExpressionBase, safe: bool = False) -> ExpressionBase:  # type: ignore[override]
        container_built = container.build()
        assert isinstance(container_built, ExpressionBase)
        item_built = item.build()
        assert isinstance(item_built, ExpressionBase)
        reduced = cls(context, container_built, item_built, safe=safe).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def __repr__(self) -> str:
        return "<{0} container={1!r} item={2!r} >".format(self.__class__.__name__, self.container, self.item)

    def evaluate(self, thing: Any) -> Any:
        resolved_obj = self.container.evaluate(thing)
        if resolved_obj is None:
            if self.safe:
                return resolved_obj
            raise errors.EvaluationError('data type mismatch (container is null)')

        resolved_item = self.item.evaluate(thing)
        if isinstance(resolved_obj, (bytes, str, tuple)):
            _assert_is_integer_number(resolved_item)
            resolved_item = int(resolved_item)
        try:
            value = operator.getitem(resolved_obj, resolved_item)
        except (IndexError, KeyError):
            if self.safe:
                return None
            raise errors.LookupError(resolved_obj, resolved_item)
        return self._new_value(value, verify_type=False)

    def reduce(self) -> ExpressionBase:
        if DataType.is_type(self.container.result_type, DataType.MAPPING):
            if self.safe and not DataType.is_compatible(self.item.result_type, self.container.result_type.key_type):
                return NullExpression(self.context)
        if _is_reduced(self.container, self.item):
            return LiteralExpressionBase.from_value(self.context, self.evaluate(None))
        return self

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        super(GetItemExpression, self).to_graphviz(digraph, *args, **kwargs)
        self.container.to_graphviz(digraph, *args, **kwargs)
        self.item.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.container)), label='container')
        digraph.edge(str(id(self)), str(id(self.item)), label='item')

class GetSliceExpression(ExpressionBase):
    """A class representing an expression in which a range of items is retrieved from a container *object*."""
    __slots__ = ('container', 'start', 'stop', 'safe')
    def __init__(
            self,
            context: 'Context',
            container: ExpressionBase,
            start: ExpressionBase | None = None,
            stop: ExpressionBase | None = None, safe: bool = False
    ) -> None:
        """
        :param context: The context to use for evaluating the expression.
        :type context: :py:class:`~rule_engine.engine.Context`
        :param container: The container object from which to retrieve the item.
        :param start: The expression that represents the starting index of the slice.
        :param stop: The expression that represents the stopping index of the slice.
        :param bool safe: Whether or not the safe version should be invoked.

        .. versionchanged:: 2.4.0
                Added the *safe* parameter.
        """
        self.context = context
        self.container = container
        if not safe:
            _assert_not_nullable(container.result_type, role='slice container')
        container_type = DataType.NULLABLE.unwrap(container.result_type)
        if container_type == DataType.BYTES:
            self.result_type = DataType.BYTES
        elif container_type == DataType.STRING:
            self.result_type = DataType.STRING
        # check against __class__ so the parent class is dynamic in case it changes in the future, what we're doing here
        # is explicitly checking if result_type is an array with out checking the value_type
        elif DataType.is_type(container_type, DataType.ARRAY):
            self.result_type = container_type
        elif DataType.is_type(container_type, DataType.SET):
            raise errors.EvaluationError('data type mismatch (container is a set)')
        elif container_type != DataType.UNDEFINED:
            if not (container_type == DataType.NULL and safe):
                raise errors.EvaluationError('data type mismatch')
        if DataType.is_type(container.result_type, DataType.NULLABLE) and self.result_type != DataType.UNDEFINED:
            self.result_type = DataType.NULLABLE.wrap(self.result_type)
        self.start = start or LiteralExpressionBase.from_value(context, 0)
        self.stop = stop or LiteralExpressionBase.from_value(context, None)
        self.safe = safe

    @classmethod
    def build(  # type: ignore[override]
            cls,
            context: 'Context',
            container: ExpressionBase,
            start: ExpressionBase | None = None,
            stop: ExpressionBase | None = None,
            safe: bool = False
    ) -> ExpressionBase:
        if start is not None:
            start_built = start.build()
            assert isinstance(start_built, ExpressionBase)
            start = start_built
        if stop is not None:
            stop_built = stop.build()
            assert isinstance(stop_built, ExpressionBase)
            stop = stop_built
        container_built = container.build()
        assert isinstance(container_built, ExpressionBase)
        reduced = cls(context, container_built, start=start, stop=stop, safe=safe).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def __repr__(self) -> str:
        return "<{0} container={1!r} start={2!r} stop={3!r} >".format(self.__class__.__name__, self.container, self.start, self.stop)

    def evaluate(self, thing: Any) -> Any:
        resolved_obj = self.container.evaluate(thing)
        if resolved_obj is None:
            if self.safe:
                return resolved_obj
            raise errors.EvaluationError('data type mismatch')

        resolved_start = self.start.evaluate(thing)
        if resolved_start is not None:
            _assert_is_integer_number(resolved_start)
            resolved_start = int(resolved_start)
        resolved_stop = self.stop.evaluate(thing)
        if resolved_stop is not None:
            _assert_is_integer_number(resolved_stop)
            resolved_stop = int(resolved_stop)
        value = operator.getitem(resolved_obj, slice(resolved_start, resolved_stop))
        return coerce_value(value, verify_type=False)

    def reduce(self) -> ExpressionBase:
        if not _is_reduced(self.container, self.start, self.stop):
            return self
        return LiteralExpressionBase.from_value(self.context, self.evaluate(None))

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        super(GetSliceExpression, self).to_graphviz(digraph, *args, **kwargs)
        self.container.to_graphviz(digraph, *args, **kwargs)
        self.start.to_graphviz(digraph, *args, **kwargs)
        self.stop.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.container)), label='container')
        digraph.edge(str(id(self)), str(id(self.start)), label='start')
        digraph.edge(str(id(self)), str(id(self.stop)), label='stop')
