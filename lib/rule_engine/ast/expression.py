#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/expression.py
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
import functools
import operator
from typing import TYPE_CHECKING, Any, Callable, Iterable

from .. import builtins as _builtins
from .. import errors
from ..suggestions import suggest_symbol
from ..types import DataType, coerce_value, is_numeric
from ..types import _ArrayDataTypeDef, _CollectionDataTypeDef, _DataTypeDef, _FunctionDataTypeDef, _MappingDataTypeDef, _NullableDataTypeDef, _ObjectDataTypeDef

from .base import (
        Assignment,
        ExpressionBase,
        LiteralExpressionBase,
        _assert_is_integer_number,
        _assert_not_nullable,
        _is_reduced,
        _propagate_nullable,
        _resolve_type,
)
from .literal import BooleanExpression, FloatExpression, NullExpression, TimedeltaExpression

if TYPE_CHECKING:
    from ..engine.context import Context

################################################################################
# Miscellaneous Expressions
################################################################################
class ComprehensionExpression(ExpressionBase):
    result_type: _DataTypeDef = DataType.ARRAY
    def __init__(
            self,
            context: 'Context',
            result: ExpressionBase,
            variable: str,
            iterable: ExpressionBase,
            condition: ExpressionBase | None = None
    ) -> None:
        self.context = context
        self.result = result
        self.variable = variable
        self.iterable = iterable
        self.condition = condition
        self.result_type = DataType.ARRAY(self.result.result_type)

    @classmethod
    def build(  # type: ignore[override]
            cls,
            context: 'Context',
            result: ExpressionBase,
            variable: str,
            iterable: ExpressionBase,
            condition: ExpressionBase | None = None
    ) -> ExpressionBase:
        iterable_built = iterable.build()
        assert isinstance(iterable_built, ExpressionBase)
        if iterable_built.result_type is not DataType.UNDEFINED and not iterable_built.result_type.is_iterable:
            raise errors.EvaluationError('data type mismatch (comprehension requires an iterable)')
        resolved_iterable_type = _resolve_type(iterable_built.result_type, context)
        assignment = Assignment(variable, value_type=getattr(resolved_iterable_type, 'iterable_type', DataType.UNDEFINED))
        with context.assignments(assignment):
            if condition is not None:
                condition_built = condition.build()
                assert isinstance(condition_built, ExpressionBase)
                condition = condition_built
            result_built = result.build()
            assert isinstance(result_built, ExpressionBase)
            result = result_built
        reduced = cls(context, result, variable, iterable_built, condition=condition).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def __repr__(self) -> str:
        return "<{0} iterable={1!r} result={2!r} condition={3!r} >".format(self.__class__.__name__, self.iterable, self.result, self.condition)

    def evaluate(self, thing: Any) -> Any:
        output_array: 'collections.deque[Any]' = collections.deque()
        input_iterable = self.iterable.evaluate(thing)
        if not DataType.from_value(input_iterable).is_iterable:
            raise errors.EvaluationError('data type mismatch (comprehension requires an iterable)')
        for value in input_iterable:
            assignment = Assignment(self.variable, value=value)
            with self.context.assignments(assignment):
                if self.condition is None or self.condition.evaluate(thing):
                    output_array.append(self.result.evaluate(thing))
        return tuple(output_array)

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        digraph.node(str(id(self)), "{}\nvariable={!r}".format(self.__class__.__name__, self.variable))
        self.result.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.result)), label='result')
        self.iterable.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.iterable)), label='iterable')
        if self.condition is not None:
            self.condition.to_graphviz(digraph, *args, **kwargs)
            digraph.edge(str(id(self)), str(id(self.condition)), label='condition')

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
        elif isinstance(_resolve_type(container_type, context), _ObjectDataTypeDef):
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
                if isinstance(resolved_object_type, _ObjectDataTypeDef):
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
                if DataType.NULLABLE.is_nullable(self.object.result_type) and self.result_type != DataType.UNDEFINED:
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
        if resolved_obj is None and DataType.NULLABLE.is_nullable(self.object.result_type):
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
        # check against __class__ so the parent class is dynamic in case it changes in the future, what we're doing here
        # is explicitly checking if result_type is an array with out checking the value_type
        elif isinstance(resolved_container_type, _ArrayDataTypeDef):
            if not DataType.is_compatible(item.result_type, DataType.FLOAT):
                raise errors.EvaluationError('data type mismatch (not an integer number)')
            self.result_type = _resolve_type(resolved_container_type.value_type, context)
        elif isinstance(resolved_container_type, _MappingDataTypeDef):
            if not (safe or DataType.is_compatible(item.result_type, resolved_container_type.key_type)):
                raise errors.LookupError(errors.UNDEFINED, errors.UNDEFINED)
            self.result_type = _resolve_type(resolved_container_type.value_type, context)
        elif DataType.is_type(resolved_container_type, DataType.SET):
            raise errors.EvaluationError('data type mismatch (container is a set)')
        elif isinstance(resolved_container_type, _ObjectDataTypeDef):
            raise errors.EvaluationError(
                    "data type mismatch (item access on OBJECT - use {0}.attribute instead)".format(resolved_container_type.name)
            )
        elif container_type != DataType.UNDEFINED:
            if not (container_type == DataType.NULL and safe):
                raise errors.EvaluationError('data type mismatch')
        if DataType.NULLABLE.is_nullable(container.result_type) and self.result_type != DataType.UNDEFINED:
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
        if isinstance(self.container.result_type, _MappingDataTypeDef):
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
        if DataType.NULLABLE.is_nullable(container.result_type) and self.result_type != DataType.UNDEFINED:
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

class SymbolExpression(ExpressionBase):
    """
    A class representing a symbol name to be resolved at evaluation time with the help of a
    :py:class:`~rule_engine.engine.Context` object.
    """
    __slots__ = ('name', 'result_type', 'scope')
    def __init__(self, context: 'Context', name: str, scope: str | None = None) -> None:
        """
        :param context: The context to use for evaluating the expression.
        :type context: :py:class:`~rule_engine.engine.Context`
        :param str name: The name of the symbol. This will be resolved with a given context object on the specified
                *thing*.
        :param str scope: The optional scope to use while resolving the symbol.
        """
        context.symbols.add(name)
        self.context = context
        self.name = name
        type_hint = context.resolve_type(name, scope=scope)
        if type_hint is not None:
            self.result_type = type_hint
        self.scope = scope

    def __repr__(self) -> str:
        return "<{0} name={1!r} >".format(self.__class__.__name__, self.name)

    def evaluate(self, thing: Any) -> Any:
        try:
            value = self.context.resolve(thing, self.name, scope=self.scope)
        except errors.SymbolResolutionError:
            default_value = self.context.default_value
            if default_value is errors.UNDEFINED:
                raise
            value = default_value
        value = self._new_value(value, verify_type=False)

        # if the expected result type is undefined, return the value
        if self.result_type == DataType.UNDEFINED:
            return value

        # NULLABLE(T) is T-or-None at runtime; None is always valid, and any other value is checked against the
        # unwrapped inner type
        effective_type: _DataTypeDef = self.result_type
        if isinstance(effective_type, _NullableDataTypeDef):
            if value is None:
                return value
            effective_type = effective_type.inner_type

        # OBJECT values are opaque to DataType.from_value; trust the schema annotation and delegate attribute-level
        # type checking to GetAttributeExpression
        if isinstance(effective_type, _ObjectDataTypeDef):
            return value

        # use DataType.from_value to raise a TypeError if value is not of a
        # compatible data type
        value_type = DataType.from_value(value)

        # if the type is the expected result type, return the value
        if DataType.is_compatible(value_type, effective_type):
            if effective_type.is_scalar:
                return value
            assert isinstance(effective_type, (_CollectionDataTypeDef, _MappingDataTypeDef))
            assert isinstance(value_type, (_CollectionDataTypeDef, _MappingDataTypeDef))
            if effective_type.value_type == DataType.UNDEFINED:
                return value
            if value_type.value_type == DataType.UNDEFINED:
                return value
            if effective_type.value_type != DataType.NULL and not effective_type.value_type_nullable and any(v is None for v in value):
                raise errors.SymbolTypeError(self.name, is_value=value, is_type=value_type, expected_type=self.result_type)
            if DataType.is_compatible(effective_type.value_type, value_type.value_type):
                return value

        # if the type is null, return the value (treat null as a special case)
        if value_type == DataType.NULL:
            return value

        raise errors.SymbolTypeError(self.name, is_value=value, is_type=value_type, expected_type=self.result_type)

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        digraph.node(str(id(self)), "{}\nname={!r}".format(self.__class__.__name__, self.name))

class FunctionCallExpression(ExpressionBase):
    __slots__ = ('function', 'arguments',)
    arguments: tuple[ExpressionBase, ...]
    def __init__(self, context: 'Context', function: ExpressionBase, arguments: Iterable[ExpressionBase]) -> None:
        self.context = context
        self.function = function
        argument_tuple: tuple[ExpressionBase, ...] = tuple(arguments)
        if self.function.result_type != DataType.UNDEFINED:
            function_type = self.function.result_type
            self._validate_function(function_type, argument_tuple)
            assert isinstance(function_type, _FunctionDataTypeDef)
            self.result_type = function_type.return_type
        self.arguments = argument_tuple

    @classmethod
    def build(cls, context: 'Context', function: ExpressionBase, arguments: Iterable[ExpressionBase]) -> ExpressionBase:  # type: ignore[override]
        function_built = function.build()
        assert isinstance(function_built, ExpressionBase)
        built_args: list[ExpressionBase] = []
        for argument in arguments:
            argument_built = argument.build()
            assert isinstance(argument_built, ExpressionBase)
            built_args.append(argument_built)
        reduced = cls(context, function_built, tuple(built_args)).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def reduce(self) -> ExpressionBase:
        if not _is_reduced(self.function, *self.arguments):
            return self
        return LiteralExpressionBase.from_value(self.context, self.evaluate(None))

    def evaluate(self, thing: Any) -> Any:
        function = self.function.evaluate(thing)
        if not callable(function):
            raise errors.EvaluationError('data type mismatch (not a callable value)')
        arguments = tuple(argument.evaluate(thing) for argument in self.arguments)
        function_name: str | None = '<unknown>'
        if self.function.result_type != DataType.UNDEFINED:
            function_type = self.function.result_type
            assert isinstance(function_type, _FunctionDataTypeDef)
            function_name = function_type.value_name
            self._validate_function(function_type, arguments)
        elif hasattr(function, '__name__'):
            function_name = function.__name__ + '?'
        try:
            result = function(*arguments)
        except errors.FunctionCallError as error:
            error.function_name = function_name
            raise error
        except Exception as error:
            raise errors.FunctionCallError('function call failed', error=error, function_name=function_name) from None
        result = self._new_value(result)
        if not DataType.is_compatible(DataType.from_value(result), self.result_type):
            raise errors.FunctionCallError('function call failed (data type mismatch on returned value)', function_name=function_name)
        return result

    def _validate_function(self, function_type: _DataTypeDef, arguments: 'tuple[Any, ...]') -> None:
        if not isinstance(function_type, _FunctionDataTypeDef):
            raise errors.EvaluationError('data type mismatch (not a callable value)')
        if function_type.minimum_arguments is not DataType.UNDEFINED:
            assert isinstance(function_type.minimum_arguments, int)
            if len(arguments) < function_type.minimum_arguments:
                raise errors.FunctionCallError(
                        "expected at least {} positional arguments".format(function_type.minimum_arguments),
                        function_name=function_type.value_name
                )
        if function_type.argument_types is not DataType.UNDEFINED:
            assert isinstance(function_type.argument_types, tuple)
            if len(arguments) > len(function_type.argument_types):
                raise errors.FunctionCallError(
                        "expected at most {} positional arguments".format(len(function_type.argument_types)),
                        function_name=function_type.value_name
                )
            for pos, (arg1, arg2_type) in enumerate(zip(arguments, function_type.argument_types), 1):
                if isinstance(arg1, ExpressionBase):
                    arg1_type = arg1.result_type
                else:
                    arg1_type = DataType.from_value(arg1)
                if not DataType.is_compatible(arg1_type, arg2_type):
                    raise errors.FunctionCallError(
                            "data type mismatch (argument #{})".format(pos),
                            function_name=function_type.value_name
                    )
                if DataType.NULLABLE.is_nullable(arg1_type) and not DataType.NULLABLE.is_nullable(arg2_type) and arg2_type != DataType.UNDEFINED:
                    raise errors.FunctionCallError(
                            "data type mismatch (argument #{} is nullable; discharge with '??' or use '&.' / '&[' for safe navigation)".format(pos),
                            function_name=function_type.value_name
                    )

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        super(FunctionCallExpression, self).to_graphviz(digraph, *args, **kwargs)
        self.function.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.function)), label='function')
        for idx, argument in enumerate(self.arguments, 1):
            argument.to_graphviz(digraph, *args, **kwargs)
            digraph.edge(str(id(self)), str(id(argument)), label="argument #{}".format(idx))

class TernaryExpression(ExpressionBase):
    """
    A class for representing ternary expressions from the grammar text. These involve evaluating :py:attr:`.condition`
    before evaluating either :py:attr:`.case_true` or :py:attr:`.case_false` based on the results.
    """
    def __init__(self, context: 'Context', condition: ExpressionBase, case_true: ExpressionBase, case_false: ExpressionBase) -> None:
        """
        :param context: The context to use for evaluating the expression.
        :type context: :py:class:`~rule_engine.engine.Context`
        :param condition: The condition expression whose evaluation determines whether the *case_true* or *case_false*
                expression is evaluated.
        :param case_true: The expression that's evaluated when *condition* is True.
        :param case_false:The expression that's evaluated when *condition* is False.
        """
        self.context = context
        self.condition = condition
        self.case_true = case_true
        self.case_false = case_false
        true_type = DataType.NULLABLE.unwrap(self.case_true.result_type)
        false_type = DataType.NULLABLE.unwrap(self.case_false.result_type)
        if true_type == false_type:
            self.result_type = true_type
        elif DataType.is_type(true_type, DataType.ARRAY) and DataType.is_type(false_type, DataType.ARRAY):
            self.result_type = DataType.ARRAY
        # todo: the other compound types should be checked here as well.
        self.result_type = _propagate_nullable(self.result_type, self.case_true.result_type, self.case_false.result_type)

    @classmethod
    def build(cls, context: 'Context', condition: ExpressionBase, case_true: ExpressionBase, case_false: ExpressionBase) -> ExpressionBase:  # type: ignore[override]
        condition_built = condition.build()
        assert isinstance(condition_built, ExpressionBase)
        case_true_built = case_true.build()
        assert isinstance(case_true_built, ExpressionBase)
        case_false_built = case_false.build()
        assert isinstance(case_false_built, ExpressionBase)
        reduced = cls(context, condition_built, case_true_built, case_false_built).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def evaluate(self, thing: Any) -> Any:
        case = (self.case_true if self.condition.evaluate(thing) else self.case_false)
        return case.evaluate(thing)

    def reduce(self) -> ExpressionBase:
        if not _is_reduced(self.condition):
            return self
        assert isinstance(self.condition, LiteralExpressionBase)
        reduced_condition = bool(self.condition.value)
        reduced = self.case_true.reduce() if reduced_condition else self.case_false.reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        super(TernaryExpression, self).to_graphviz(digraph, *args, **kwargs)
        self.condition.to_graphviz(digraph, *args, **kwargs)
        self.case_true.to_graphviz(digraph, *args, **kwargs)
        self.case_false.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.condition)), label='condition')
        digraph.edge(str(id(self)), str(id(self.case_true)), label='true case')
        digraph.edge(str(id(self)), str(id(self.case_false)), label='false case')

class UnaryExpression(ExpressionBase):
    """
    A class for representing unary expressions from the grammar text. These involve a single operator on the left side.
    """
    def __init__(self, context: 'Context', type_: str, right: ExpressionBase) -> None:
        """
        :param context: The context to use for evaluating the expression.
        :type context: :py:class:`~rule_engine.engine.Context`
        :param str type_: The grammar type of operator to the left of the expression.
        :param right: The expression to the right of the operator.
        :type right: :py:class:`~.ExpressionBase`
        """
        self.context = context
        type_ = type_.lower()
        self.type = type_
        if type_ == 'not':
            self.result_type = DataType.BOOLEAN
        elif type_ == 'uminus':
            _assert_not_nullable(right.result_type, role='unary minus operand')
            self.result_type = right.result_type
        else:
            raise ValueError('unknown unary expression type')
        self._evaluator = getattr(self, '_op_' + type_)
        self.right = right

    @classmethod
    def build(cls, context: 'Context', type_: str, right: ExpressionBase) -> ExpressionBase:  # type: ignore[override]
        right_built = right.build()
        assert isinstance(right_built, ExpressionBase)
        reduced = cls(context, type_, right_built).reduce()
        assert isinstance(reduced, ExpressionBase)
        return reduced

    def __repr__(self) -> str:
        return "<{} type={!r} >".format(self.__class__.__name__, self.type)

    def evaluate(self, thing: Any) -> Any:
        return self._evaluator(thing)

    def __op(self, op: Callable[[Any], Any], thing: Any) -> Any:
        return op(self.right.evaluate(thing))

    _op_not = functools.partialmethod(__op, operator.not_)

    def __op_arithmetic(self, op: Callable[[Any], Any], thing: Any) -> Any:
        right = self.right.evaluate(thing)
        if not is_numeric(right) and not isinstance(right, datetime.timedelta):
            raise errors.EvaluationError('data type mismatch (not a numeric or timedelta value)')
        return op(right)

    _op_uminus = functools.partialmethod(__op_arithmetic, operator.neg)

    def reduce(self) -> ExpressionBase:
        type_ = self.type.lower()
        if not _is_reduced(self.right):
            return self
        if type_ == 'not':
            return BooleanExpression(self.context, self.evaluate(None))
        elif type_ == 'uminus':
            if isinstance(self.right, FloatExpression):
                return FloatExpression(self.context, self.evaluate(None))
            elif isinstance(self.right, TimedeltaExpression):
                return TimedeltaExpression(self.context, self.evaluate(None))
            raise errors.EvaluationError('data type mismatch (not a float or timedelta expression)')
        raise errors.EngineError('unsupported unary expression type')

    def to_graphviz(self, digraph: Any, *args: Any, **kwargs: Any) -> None:
        digraph.node(str(id(self)), "{}\ntype={!r}".format(self.__class__.__name__, self.type.lower()))
        self.right.to_graphviz(digraph, *args, **kwargs)
        digraph.edge(str(id(self)), str(id(self.right)))
