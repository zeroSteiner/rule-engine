#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/engine/rule.py
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

import decimal
from typing import Any, Iterable, Iterator, TYPE_CHECKING

from .. import errors
from ..parser import Parser
from .context import Context

if TYPE_CHECKING:
    import graphviz

class Rule(object):
    """
    A rule which parses a string with a logical expression and can then evaluate an arbitrary object for whether or not
    it matches based on the constraints of the expression.
    """
    parser: Parser = Parser()
    """
    The :py:class:`~rule_engine.parser.Parser` instance that will be used for parsing the rule text into a compatible
    abstract syntax tree (AST) for evaluation.
    """
    def __init__(self, text: str, context: Context | None = None) -> None:
        """
        :param str text: The text of the logical expression.
        :param context: The context to use for evaluating the expression on arbitrary objects. This can be used to
                change the default behavior. The default context is :py:class:`.Context` but any object providing the same
                interface (such as a subclass) can be used.
        :type context: :py:class:`.Context`
        """
        context = context or Context()
        self.text = text
        self.context = context
        self.statement = self.parser.parse(text, context)

    def __getstate__(self) -> dict[str, Any]:
        return {'text': self.text, 'context': self.context}

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.text = state['text']
        self.context = state['context']
        self.statement = self.parser.parse(self.text, self.context)

    def __repr__(self) -> str:
        return "<{0} text={1!r} >".format(self.__class__.__name__, self.text)

    def __str__(self) -> str:
        return self.text

    def filter(self, things: Iterable[Any]) -> Iterator[Any]:
        """
        A convenience function for iterating over *things* and yielding each member that :py:meth:`.matches` return True
        for.

        :param things: The collection of objects to iterate over.
        """
        yield from (thing for thing in things if self.matches(thing))

    @classmethod
    def is_valid(cls, text: str, context: Context | None = None) -> bool:
        """
        Test whether or not the rule is syntactically correct. This verifies the grammar is well structured and that
        there are no type compatibility issues regarding literals or symbols with known types (see
        :py:meth:`~.Context.resolve_type` for specifying symbol type information).

        :param str text: The text of the logical expression.
        :param context: The context as would be passed to the :py:meth:`.__init__` method. This can be used for
                specifying symbol type information.
        :return: Whether or not the expression is well formed and appears valid.
        :rtype: bool
        """
        try:
            cls.parser.parse(text, (context or Context()))
        except errors.EngineError:
            return False
        return True

    def evaluate(self, thing: Any) -> Any:
        """
        Evaluate the rule against the specified *thing* and return the value. This can be used to, for example, apply
        the symbol resolver.

        :param thing: The object on which to apply the rule.
        :return: The value the rule evaluates to. Unlike the :py:meth:`.matches` method, this is not necessarily a
                boolean.
        """
        self.context._tls.reset()
        with decimal.localcontext(self.context.decimal_context):
            return self.statement.evaluate(thing)

    def matches(self, thing: Any) -> bool:
        """
        Evaluate the rule against the specified *thing*. This will either return whether *thing* matches, or an
        exception will be raised.

        :param thing: The object on which to apply the rule.
        :return: Whether or not the rule matches.
        :rtype: bool
        """
        return bool(self.evaluate(thing))

    def to_graphviz(self) -> 'graphviz.Digraph':
        """
        Generate a diagram of the parsed rule's AST using GraphViz.

        :return: The rule diagram.
        :rtype: :py:class:`graphviz.Digraph`
        """
        import graphviz
        digraph = graphviz.Digraph(comment=self.text)
        self.statement.to_graphviz(digraph)
        return digraph

class DebugRule(Rule):
    parser: Parser  # set per-instance in __init__ (overrides the class-level attribute on Rule)
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.parser = Parser(debug=True)
        super(DebugRule, self).__init__(*args, **kwargs)
