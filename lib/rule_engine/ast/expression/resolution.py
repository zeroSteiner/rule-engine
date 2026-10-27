#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/expression/resolution.py
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
from typing import TYPE_CHECKING, Any, Iterable

from ... import builtins as _builtins
from ... import errors
from ...types import DataType
from ...types import _CollectionDataTypeDef, _DataTypeDef, _FunctionDataTypeDef, _MappingDataTypeDef

from ..base import ExpressionBase, LiteralExpressionBase, _is_reduced

if TYPE_CHECKING:
    from ...engine.context import Context

def _null_allowed(member_type: _DataTypeDef) -> bool:
    """Whether a member slot of *member_type* may hold ``None``."""
    return member_type == DataType.UNDEFINED or member_type == DataType.NULL or DataType.is_type(member_type, DataType.NULLABLE)

_NullMemberPlan = tuple[bool, tuple[tuple[str, _DataTypeDef, bool, '_NullMemberPlan | None'], ...]]

# the containers that DataType.from_value treats as an ARRAY or a SET
_COLLECTION_TYPES = (collections.abc.Sequence, collections.abc.Set)
_NOT_COLLECTION_TYPES = (str, bytes, bytearray)

def _null_member_plan(declared: _DataTypeDef) -> '_NullMemberPlan | None':
    """
    Precompute where a value of the compound type *declared* may hold a ``None`` that its member type doesn't allow,
    for :py:func:`_find_null_member`. Each slot is a kind of member (``'key'``, ``'value'`` or ``'member'``), its
    declared type, whether that type allows ``None`` and the plan for its own members.

    :return: Whether the value is a mapping and the slots to check, or ``None`` when there is nothing to check.
    """
    declared = DataType.NULLABLE.unwrap(declared)
    slots: tuple[tuple[str, _DataTypeDef], ...]
    if isinstance(declared, _MappingDataTypeDef):
        is_mapping = True
        slots = (('key', declared.key_type), ('value', declared.value_type))
    elif isinstance(declared, _CollectionDataTypeDef):
        is_mapping = False
        slots = (('member', declared.value_type),)
    else:
        return None
    plan = []
    for kind, member_type in slots:
        null_allowed = _null_allowed(member_type)
        nested = _null_member_plan(member_type)
        if null_allowed and nested is None:
            continue
        plan.append((kind, member_type, null_allowed, nested))
    if not plan:
        return None
    return is_mapping, tuple(plan)

def _find_null_member(plan: _NullMemberPlan, value: Any) -> tuple[str, _DataTypeDef] | None:
    """
    Find a ``None`` member of *value* in a slot that doesn't allow one, including nested members, following a plan from
    :py:func:`_null_member_plan`. :py:attr:`~DataType.MAPPING` keys are checked against the key type and values against
    the value type.

    :return: The kind of member (``'key'``, ``'value'`` or ``'member'``) and its declared type, or ``None``.
    """
    is_mapping, slots = plan
    if is_mapping:
        if not isinstance(value, collections.abc.Mapping):
            return None
    elif type(value) not in (tuple, set) and (not isinstance(value, _COLLECTION_TYPES) or isinstance(value, _NOT_COLLECTION_TYPES)):
        return None
    container_value: Any = value
    members: Iterable[Any]
    for kind, member_type, null_allowed, nested in slots:
        if kind == 'key':
            members = container_value.keys()
        elif kind == 'value':
            members = container_value.values()
        else:
            members = container_value
        if nested is None:
            # null_allowed is False, otherwise the slot would have been skipped
            for member in members:
                if member is None:
                    return kind, member_type
            continue
        for member in members:
            if member is None:
                if not null_allowed:
                    return kind, member_type
            else:
                found = _find_null_member(nested, member)
                if found is not None:
                    return found
    return None

class SymbolExpression(ExpressionBase):
    """
    A class representing a symbol name to be resolved at evaluation time with the help of a
    :py:class:`~rule_engine.engine.Context` object.
    """
    __slots__ = ('name', 'result_type', 'scope', '_null_plan_cache')
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
        # the type the cached plan was made for and the plan, see _accept_members
        self._null_plan_cache: tuple[_DataTypeDef, _NullMemberPlan | None] | None = None

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
        if DataType.is_type(effective_type, DataType.NULLABLE):
            if value is None:
                return value
            effective_type = effective_type.inner_type

        # OBJECT values are opaque to DataType.from_value; trust the schema annotation and delegate attribute-level
        # type checking to GetAttributeExpression
        if DataType.is_type(effective_type, DataType.OBJECT):
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
                return self._accept_members(effective_type, value)
            if value_type.value_type == DataType.UNDEFINED:
                return self._accept_members(effective_type, value)
            if not self._is_re_groups(effective_type):
                if effective_type.value_type != DataType.NULL and not effective_type.value_type_nullable:
                    # for a MAPPING this checks the keys, not the values; a None key is fine when the key type allows
                    # it, but a None value found alongside it stays an error
                    has_null = any(v is None for v in value)
                    if has_null and isinstance(effective_type, _MappingDataTypeDef) and _null_allowed(effective_type.key_type):
                        has_null = any(v is None for v in value.values())
                    if has_null:
                        raise errors.SymbolTypeError(
                                self.name,
                                is_value=value,
                                is_type=_with_null_members(value_type, value),
                                expected_type=self.result_type
                        )
            if DataType.is_compatible(effective_type.value_type, value_type.value_type):
                return self._accept_members(effective_type, value)

        # if the type is null, return the value (treat null as a special case)
        if value_type == DataType.NULL:
            return value

        raise errors.SymbolTypeError(
                self.name,
                is_value=value,
                is_type=_with_null_members(value_type, value),
                expected_type=self.result_type
        )

    def _is_re_groups(self, effective_type: _DataTypeDef) -> bool:
        # $re_groups holds None for groups that did not participate in the match (see _RE_GROUPS_TYPE); the type object
        # can be passed on to other symbols (e.g. comprehension variables) so check the symbol site too
        return self.scope == _builtins.Builtins.scope_name and effective_type is _builtins._RE_GROUPS_TYPE

    def _accept_members(self, effective_type: _DataTypeDef, value: Any) -> Any:
        # accept a compound value whose members passed the checks above, but warn about a None member where the member
        # type doesn't allow one because v6.0 will raise SymbolTypeError for it
        if (self.scope, self.name) in self.context._null_member_warned or self._is_re_groups(effective_type):
            return value
        cache = self._null_plan_cache
        if cache is None or cache[0] is not effective_type:
            cache = self._null_plan_cache = (effective_type, _null_member_plan(effective_type))
        plan = cache[1]
        found = None if plan is None else _find_null_member(plan, value)
        # a variable assigned by an expression (e.g. a comprehension) holds a value that was checked where it came from
        if found is not None and not (self.scope is None and self.context._is_assigned(self.name)):
            self.context._warn_null_member(self.name, self.scope, *found)
        return value

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
                if DataType.is_type(arg1_type, DataType.NULLABLE) and not DataType.is_type(arg2_type, DataType.NULLABLE) and arg2_type != DataType.UNDEFINED:
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

def _with_null_members(value_type: _DataTypeDef, value: Any) -> _DataTypeDef:
    """
    Wrap the member type of the ARRAY or SET type *value_type* that was inferred from *value* in NULLABLE when *value*
    has null members, which the inferred member type leaves out.
    """
    if isinstance(value_type, _CollectionDataTypeDef) and value_type.value_type != DataType.UNDEFINED:
        if any(member is None for member in value):
            return value_type(DataType.NULLABLE(value_type.value_type))
    return value_type
