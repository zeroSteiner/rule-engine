#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/engine/chain.py
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
import sys
import threading
from typing import Any, Iterable, Iterator, NamedTuple, TypeVar, overload

from .. import errors
from .context import Context
from .rule import Rule

class ChainEntry(NamedTuple):
    """
    A single entry within a :py:class:`.Chain`, pairing a rule with the value that is returned when it matches.

    .. versionadded:: 5.1.0
    """
    rule: Rule
    """The :py:class:`.Rule` that objects are evaluated against."""
    value: Any
    """The value that is returned by :py:meth:`.Chain.evaluate` when :py:attr:`.rule` matches."""

def _check_rule(rule: Any, name: str = 'chain rule') -> None:
    if not isinstance(rule, (str, Rule)):
        raise TypeError("{0} must be a str or Rule instance, not {1}".format(name, type(rule).__name__))

def _unpack_entry(position: int, entry: Any) -> tuple[Any, Any]:
    # only accept real sequences, iterating a str or mapping would silently split it into a bogus (rule, value) pair
    if not isinstance(entry, collections.abc.Sequence) or isinstance(entry, (str, bytes, bytearray)):
        raise TypeError("chain entry #{0} must be a (rule, value) pair, not {1}".format(
                position,
                type(entry).__name__
        ))
    if len(entry) != 2:
        raise ValueError("chain entry #{0} has length {1}; 2 is required".format(position, len(entry)))
    _check_rule(entry[0], "chain entry #{0} rule".format(position))
    return entry[0], entry[1]

_ChainT = TypeVar('_ChainT', bound='Chain')

class Chain(object):
    """
    An ordered collection of rules, each of which is paired with a value. An object is evaluated against each rule in
    order and the value of the first rule that matches it is returned, much like a packet traversing a chain in iptables
    where the value is the target (e.g. ``ACCEPT`` or ``DROP``) and the default value is the chain's policy.

    A rule matches when :py:meth:`.Rule.matches` returns a truthy value. Exceptions raised while evaluating a rule, such
    as a :py:exc:`~rule_engine.errors.SymbolResolutionError`, are not caught and stop the evaluation.

    Evaluating a chain does not acquire a lock. Each evaluation uses the entries that were present when it started, so
    one thread can modify a chain while others are evaluating it. Modifications are serialized so concurrent changes
    are not lost, however adding or removing an entry copies the others, so a large chain is best built by passing its
    entries to the constructor. A chain should not be modified from a ``__del__`` method or a :py:mod:`weakref`
    finalizer because the garbage collector can run them while a modification is in progress, which would deadlock.
    A chain can be pickled as long as its context, rules and values can be.

    Indexes start at 0, unlike the rule numbers used by iptables, and negative indexes count from the end of the chain.
    Slicing a chain returns a new chain with the entries in the slice and the same :py:attr:`.default_value` and
    :py:attr:`.context`. Adding or removing entries in either chain afterwards does not change the other.

    .. versionadded:: 5.1.0
    """
    def __init__(
            self,
            entries: Iterable[tuple[Rule | str, Any]] | None = None,
            *,
            default_value: Any = errors.UNDEFINED,
            context: Context | None = None
    ) -> None:
        """
        :param entries: An optional iterable of ``(rule, value)`` pairs to initialize the chain with, in order. Each
                rule can be either a :py:class:`.Rule` instance or the text of one, which will be compiled using
                *context*.
        :param default_value: The value that :py:meth:`.evaluate` returns when no rule matches. If this is
                :py:data:`~rule_engine.errors.UNDEFINED` (the default), a
                :py:exc:`~rule_engine.errors.ChainExhaustedError` is raised instead.
        :param context: The context to use for compiling rules that are specified as text. If not specified, a new
                default :py:class:`.Context` is created and shared by all of them. :py:class:`.Rule` instances are used
                as-is and keep their own context.
        :type context: :py:class:`.Context`
        """
        if context is None:
            context = Context()
        self._lock = threading.Lock()
        self.context = context
        """The context that is used for compiling rules that are specified as text."""
        self.default_value = default_value
        """The *default_value* parameter from :py:meth:`~__init__`."""
        self._entries: tuple[ChainEntry, ...] = ()
        if entries is not None:
            # validate every entry before compiling any of them so an invalid one doesn't add symbols to the context
            pairs = [_unpack_entry(position, entry) for position, entry in enumerate(entries)]
            self._entries = tuple(self._new_entry(rule, value) for rule, value in pairs)

    @overload
    def __getitem__(self, index: int) -> ChainEntry: ...

    @overload
    def __getitem__(self: _ChainT, index: slice) -> _ChainT: ...

    def __getitem__(self, index: int | slice) -> 'ChainEntry | Chain':
        if isinstance(index, slice):
            chain = self.__class__(default_value=self.default_value, context=self.context)
            # the entries are immutable so the new chain can share them
            chain._entries = self._entries[index]
            return chain
        index = operator.index(index)
        try:
            return self._entries[index]
        except IndexError:
            raise IndexError('chain index out of range') from None

    def __getstate__(self) -> dict[str, Any]:
        return {'context': self.context, 'default_value': self.default_value, 'entries': self._entries}

    def __iter__(self) -> Iterator[ChainEntry]:
        # return the tuple's iterator directly so the entries are captured when iter() is called
        return iter(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return "<{0} entries={1} default_value={2!r} >".format(
                self.__class__.__name__,
                len(self._entries),
                self.default_value
        )

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.context = state['context']
        self.default_value = state['default_value']
        self._entries = state['entries']
        # recreate the lock which can not be pickled
        self._lock = threading.Lock()

    def _new_entry(self, rule: Rule | str, value: Any) -> ChainEntry:
        _check_rule(rule)
        if isinstance(rule, str):
            rule = Rule(rule, context=self.context)
        return ChainEntry(rule, value)

    def append(self, rule: Rule | str, value: Any) -> ChainEntry:
        """
        Add a new entry to the end of the chain, like ``iptables --append``.

        :param rule: The rule for the new entry, either a :py:class:`.Rule` instance or the text of one, which will be
                compiled using :py:attr:`.context`.
        :param value: The value to return when *rule* matches.
        :return: The new entry.
        :rtype: :py:class:`.ChainEntry`
        """
        entry = self._new_entry(rule, value)
        with self._lock:
            self._entries = self._entries + (entry,)
        return entry

    def delete(self, index: int) -> ChainEntry:
        """
        Remove the entry at *index* from the chain, like ``iptables --delete``. Indexes start at 0 and negative indexes
        count from the end of the chain.

        :param int index: The index of the entry to remove.
        :return: The entry that was removed.
        :rtype: :py:class:`.ChainEntry`
        :raises IndexError: There is no entry at *index*.
        """
        index = operator.index(index)
        with self._lock:
            entries = list(self._entries)
            try:
                entry = entries.pop(index)
            except (IndexError, OverflowError):
                raise IndexError('chain index out of range') from None
            self._entries = tuple(entries)
        return entry

    def evaluate(self, thing: Any) -> Any:
        """
        Evaluate *thing* against each rule in the chain and return the value of the first one that matches. If no rule
        matches, the :py:attr:`.default_value` is returned.

        :param thing: The object on which to apply the rules.
        :return: The value of the first matching rule, or the default value.
        :raises ChainExhaustedError: No rule matched and :py:attr:`.default_value` is
                :py:data:`~rule_engine.errors.UNDEFINED`.
        """
        default_value = self.default_value
        entry = self.find(thing)
        if entry is not None:
            return entry.value
        if default_value is errors.UNDEFINED:
            raise errors.ChainExhaustedError(thing=thing)
        return default_value

    def find(self, thing: Any) -> ChainEntry | None:
        """
        Evaluate *thing* against each rule in the chain and return the first entry that matches. Unlike
        :py:meth:`.evaluate`, the default value is not used. This can be used to determine which rule matched, and
        :py:meth:`.index` can then be used to determine its position.

        :param thing: The object on which to apply the rules.
        :return: The first matching :py:class:`.ChainEntry`, or ``None`` if no rule matched.
        """
        for entry in self._entries:
            if entry.rule.matches(thing):
                return entry
        return None

    def flush(self) -> None:
        """
        Remove all entries from the chain, like ``iptables --flush``. The :py:attr:`.default_value` is unchanged.
        """
        with self._lock:
            entries, self._entries = self._entries, ()
        # release the old entries after the lock so any finalizers they trigger can modify the chain
        del entries

    def index(self, entry: ChainEntry) -> int:
        """
        Return the index of *entry* in the chain, such as an entry that was returned by :py:meth:`.find`. Entries are
        compared as tuples and a rule is only equal to itself, so an entry is only found in a chain that contains the
        same rule, like the chain it came from or a slice of it.

        :param entry: The entry to look up.
        :type entry: :py:class:`.ChainEntry`
        :return: The index of the first entry that is equal to *entry*.
        :rtype: int
        :raises ValueError: *entry* is not in the chain.
        """
        # compare the entries here instead of using tuple.index so an error raised while comparing two values isn't
        # mistaken for the entry being missing
        for position, other in enumerate(self._entries):
            if other is entry or other == entry:
                return position
        raise ValueError('entry is not in the chain')

    def insert(self, index: int, rule: Rule | str, value: Any) -> ChainEntry:
        """
        Insert a new entry into the chain before *index*, like ``iptables --insert``. Indexes start at 0 and negative
        indexes count from the end of the chain. This follows the semantics of :py:meth:`list.insert`, so an *index*
        past either end of the chain adds the entry to that end.

        :param int index: The index to insert the new entry before.
        :param rule: The rule for the new entry, either a :py:class:`.Rule` instance or the text of one, which will be
                compiled using :py:attr:`.context`.
        :param value: The value to return when *rule* matches.
        :return: The new entry.
        :rtype: :py:class:`.ChainEntry`
        """
        # clamp the index to the range list.insert supports, it then clamps it again to the ends of the chain
        index = max(-sys.maxsize - 1, min(operator.index(index), sys.maxsize))
        entry = self._new_entry(rule, value)
        with self._lock:
            entries = list(self._entries)
            entries.insert(index, entry)
            self._entries = tuple(entries)
        return entry
