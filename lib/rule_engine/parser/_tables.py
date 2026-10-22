#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/parser/_tables.py
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

import io
import json
import os
import pkgutil
import sys
import types
from typing import TYPE_CHECKING, Any

from .._vendor.ply import yacc

if TYPE_CHECKING:
    from .base import ParserBase

_PACKAGE = 'rule_engine.parser'
_FILENAME = 'parsetab.json'
_DEBUG_FILENAME = 'parser.out'
_MODULE_NAME = _PACKAGE + '.parsetab'
# the types of a production's str, name, len, func, file and line fields
_PRODUCTION_TYPES: tuple[type | tuple[type, ...], ...] = (
    str, str, int, (str, type(None)), (str, type(None)), (int, type(None))
)

def signature(parser: 'ParserBase | type[ParserBase]') -> str:
    """
    Compute the signature ply uses to check that tables match the grammar. This works on a parser class too, so the
    tables don't need to be built.
    """
    # build the dictionary the same way yacc() does
    pdict = {key: getattr(parser, key) for key in dir(parser)}
    module = sys.modules[pdict['__module__']]
    pdict.setdefault('__file__', module.__file__)
    pdict.setdefault('__package__', module.__package__)
    reflection = yacc.ParserReflect(pdict, log=yacc.NullLogger())
    reflection.get_all()
    return reflection.signature()

def _production(production: Any) -> tuple[Any, ...]:
    # the same format that ply's write_table() uses
    if production.func:
        return (
            production.str,
            production.name,
            production.len,
            production.func,
            os.path.basename(production.file),
            production.line
        )
    return (str(production), production.name, production.len, None, None, None)

def dump(parser: 'ParserBase', path: str) -> None:
    """Write the tables of a built parser to *path* as JSON."""
    lr_parser = parser._parser
    tables = {
        'tabversion': yacc.__tabversion__,
        # LRParser doesn't keep the method, ParserBase always uses the default
        'method': 'LALR',
        'signature': signature(parser),
        'action': lr_parser.action,
        'goto': lr_parser.goto,
        'productions': [_production(production) for production in lr_parser.productions]
    }
    with open(path, 'w', encoding='utf-8') as file_h:
        json.dump(tables, file_h, separators=(',', ':'), sort_keys=True)

def dump_debug(path: str) -> None:
    """Build the tables of the rule parser and write ply's description of the grammar and its states to *path*."""
    # imported here to avoid a circular import
    from . import Parser
    # tables without a signature never match the grammar, so ply builds new ones and describes them while it does
    tables = types.ModuleType(_MODULE_NAME)
    tables.__dict__.update(
        _tabversion=yacc.__tabversion__,
        _lr_action={},
        _lr_goto={},
        _lr_productions=[],
        _lr_method='LALR',
        _lr_signature=None
    )
    # yacc() uses the directory of the table module as the output directory
    tables.__file__ = path
    with open(path, 'w', encoding='utf-8') as file_h:
        yacc.yacc(
            module=Parser.__new__(Parser),
            debug=True,
            tabmodule=tables,
            write_tables=False,
            debuglog=yacc.PlyLogger(file_h)
        )

def _states(data: Any) -> dict[int, dict[str, int | None]]:
    states = {}
    for state, entries in data.items():
        # nonassociative operators leave None (a syntax error) in the action table
        if not all(isinstance(name, str) and isinstance(value, (int, type(None))) for name, value in entries.items()):
            raise TypeError('invalid table entry')
        # json object keys are always strings
        states[int(state)] = entries
    return states

def _productions(data: Any) -> list[tuple[Any, ...]]:
    if not isinstance(data, list):
        raise TypeError('invalid productions')
    productions = []
    for production in data:
        if not isinstance(production, list) or len(production) != len(_PRODUCTION_TYPES):
            raise TypeError('invalid production')
        if not all(isinstance(value, expected) for value, expected in zip(production, _PRODUCTION_TYPES)):
            raise TypeError('invalid production')
        productions.append(tuple(production))
    return productions

def load(path: str | None = None) -> types.ModuleType | None:
    """
    Load tables written by :py:func:`dump` as a module that can be passed to ``yacc.yacc(tabmodule=...)``. When *path*
    is None, the tables packaged with rule_engine are loaded. None is returned if the tables can't be loaded.
    """
    try:
        if path is None:
            path = os.path.join(os.path.dirname(__file__), _FILENAME)
            data = pkgutil.get_data(_PACKAGE, _FILENAME)
            # get_data() returns None when the loader can't read files
            if data is None:
                return None
        else:
            with open(path, 'rb') as file_h:
                data = file_h.read()
        tables = json.loads(data)
        # ply would warn about tables for another version before building them
        if tables['tabversion'] != yacc.__tabversion__:
            return None
        module = types.ModuleType(_MODULE_NAME)
        module.__dict__.update(
            _tabversion=tables['tabversion'],
            _lr_action=_states(tables['action']),
            _lr_goto=_states(tables['goto']),
            _lr_productions=_productions(tables['productions']),
            _lr_method=tables['method'],
            _lr_signature=tables['signature']
        )
        # yacc() uses the directory of the table module as the output directory
        module.__file__ = path
        return module
    except Exception:
        # any problem with the file means the tables can't be used
        return None

def _check(path: str | None) -> int:
    # imported here to avoid a circular import
    from . import Parser
    packaged = path is None
    tables = load(path)
    if path is None:
        path = os.path.join(os.path.dirname(__file__), _FILENAME)
    if tables is None:
        print('the parser tables could not be loaded from ' + path, file=sys.stderr)
        return 1
    if tables._lr_signature != signature(Parser):
        print('the parser tables in ' + path + ' do not match the grammar', file=sys.stderr)
        return 1
    # let ply decide if it would use the tables, anything it logs means it would build them instead
    messages = io.StringIO()
    lr_parser = yacc.yacc(
        module=Parser.__new__(Parser),
        debug=False,
        tabmodule=tables,
        write_tables=False,
        debuglog=yacc.NullLogger(),
        errorlog=yacc.PlyLogger(messages)
    )
    if messages.getvalue() or not isinstance(lr_parser.productions[0], yacc.MiniProduction):
        reason = (messages.getvalue().splitlines() or ['ply built new tables'])[0]
        print('the parser tables in ' + path + ' can not be used (' + reason + ')', file=sys.stderr)
        return 1
    if packaged:
        # the rule parser was built when the package was imported, make sure it used the packaged tables too
        from ..engine import Rule
        if not isinstance(Rule.parser._parser.productions[0], yacc.MiniProduction):
            print('the rule parser did not use the parser tables in ' + path, file=sys.stderr)
            return 1
    return 0

def main(argv: list[str] | None = None) -> int:
    # imported here because it's slow to import and only the command line needs it
    import argparse
    arg_parser = argparse.ArgumentParser(
        prog='python -m rule_engine.parser',
        description='Rule Engine: Generate the parser tables'
    )
    modes = arg_parser.add_mutually_exclusive_group()
    modes.add_argument('--check', action='store_true', help='check that the tables in PATH can be used')
    modes.add_argument(
        '--debug',
        action='store_true',
        help='also write the grammar debug output to ' + _DEBUG_FILENAME + ' next to PATH'
    )
    arg_parser.add_argument('path', metavar='PATH', nargs='?', help='the tables file (optional with --check)')
    arguments = arg_parser.parse_args(argv)
    if arguments.check:
        return _check(arguments.path)
    if arguments.path is None:
        arg_parser.error('the following arguments are required: PATH')
    if arguments.debug and os.path.basename(arguments.path) == _DEBUG_FILENAME:
        arg_parser.error('PATH can not be named ' + _DEBUG_FILENAME + ' with --debug')
    # importing the package already built the rule parser, so write its tables instead of building them again
    from ..engine import Rule
    dump(Rule.parser, arguments.path)
    if arguments.debug:
        dump_debug(os.path.join(os.path.dirname(arguments.path), _DEBUG_FILENAME))
    return 0
