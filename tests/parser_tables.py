#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/parser_tables.py
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

import contextlib
import errno
import functools
import importlib
import inspect
import io
import json
import os
import runpy
import sys
import tempfile
import types
import unittest
import unittest.mock

import rule_engine.engine as engine
import rule_engine.errors as errors
import rule_engine.parser as parser
import rule_engine.parser._tables as _tables
import rule_engine.parser.base as base
from rule_engine._vendor.ply import yacc

__all__ = (
    'ParserTablesCliTests',
    'ParserTablesGrammarTests',
    'ParserTablesLoadTests',
    'ParserTablesNormalizationTests',
    'ParserTablesTests',
)

_PACKAGED_PATH = os.path.join(os.path.dirname(_tables.__file__), 'parsetab.json')
_RULES = (
    'a + b * 2 == 7',
    '-a ** 2 < b and not c',
    '[x for x in [1, 2, 3] if x > 1] == [2, 3]',
    '{"x": a}["x"] ?? b',
    'a < b ? "lt" : "ge"',
    '"abcd"[1:3] =~ "b.$" # comment',
    '$abs(-a) in {1, 2} and d"2020-01-01" < d"2021-01-01" and t"PT1H" > t"PT1M"',
    'b"a\\x62"',
)
_THING = {'a': 1, 'b': 3, 'c': False}
# a package with its own grammar, it reuses the lexer below because ply rejects rules that are defined twice in a file
_PACKAGE_SOURCE = '''
from {module} import _CalculatorLexer, _Result

class Calculator(_CalculatorLexer):
    def p_package_statement(self, p):
        """
        statement : expression
        """
        p[0] = _Result(p[1])

    def p_package_expression(self, p):
        """
        expression : expression ADD NUMBER
                   | expression MUL NUMBER
                   | NUMBER
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = p[1] + p[3] if p[2] == '+' else p[1] * p[3]

    # recorded before ParserBase sees the class
    raw_docstrings = {{name: value.__doc__ for name, value in list(locals().items()) if name.startswith('p_')}}
'''

@functools.lru_cache(maxsize=None)
def _generated_parser():
    # building the tables takes about a second so do it once for the whole module
    with unittest.mock.patch.object(_tables, 'load', return_value=None):
        return parser.Parser()

def _dump(directory, name='parsetab.json'):
    path = os.path.join(directory, name)
    _tables.dump(_generated_parser(), path)
    return path

def _evaluate(parser_, text):
    return parser_.parse(text, engine.Context()).evaluate(_THING)

@contextlib.contextmanager
def _no_writes():
    # refuse to open files for writing so nothing is written even when a test fails
    writes = []
    real_open = open
    def guarded_open(file, mode='r', *args, **kwargs):
        if set(mode) & set('wax+'):
            writes.append(file)
            raise PermissionError(errno.EACCES, 'writing files is not allowed', file)
        return real_open(file, mode, *args, **kwargs)
    # the import system caches bytecode, that isn't the parser writing files
    with unittest.mock.patch('builtins.open', guarded_open), \
            unittest.mock.patch.object(sys, 'dont_write_bytecode', True):
        yield writes

def _custom_error(self, token):
    raise errors.RuleSyntaxError('custom syntax error', token)

class _SameGrammarParser(parser.Parser):
    p_error = _custom_error

class _ExtendedParser(parser.Parser):
    @staticmethod
    def p_expression_extended(p):
        """
            object : LPAREN LPAREN expression RPAREN RPAREN
                   | LBRACKET LBRACKET expression RBRACKET RBRACKET
        """
        p[0] = p[3]

class _Result(object):
    def __init__(self, value):
        self.value = value

    def build(self):
        return self.value

class _CalculatorLexer(base.ParserBase):
    tokens = ('ADD', 'MUL', 'NUMBER')
    precedence = (('left', 'ADD'), ('left', 'MUL'))
    t_ignore = ' '
    t_ADD = r'\+'
    t_MUL = r'\*'

    def t_NUMBER(self, t):
        r'[0-9]+'
        t.value = int(t.value)
        return t

    def t_error(self, t):
        raise errors.RuleSyntaxError('syntax error')

    def p_error(self, token):
        raise errors.RuleSyntaxError('syntax error', token)

class _CalculatorParser(_CalculatorLexer):
    _normalize_grammar = True

    @classmethod
    def p_statement(cls, p):
        """
        statement : expression
        """
        p[0] = _Result(p[1])

    def p_expression_binary(self, p):
        """
        expression : expression ADD expression
                   | expression MUL expression
        """
        p[0] = p[1] + p[3] if p[2] == '+' else p[1] * p[3]

    @staticmethod
    def p_expression_number(p):
        """
        expression : NUMBER

        """
        p[0] = p[1]

# the same grammar indented the way python 3.13 leaves it
class _DedentedCalculatorParser(_CalculatorLexer):
    _normalize_grammar = True

    @classmethod
    def p_dedented_statement(cls, p):
        """
statement : expression
"""
        p[0] = _Result(p[1])

    def p_dedented_expression_binary(self, p):
        """
expression : expression ADD expression
           | expression MUL expression
"""
        p[0] = p[1] + p[3] if p[2] == '+' else p[1] * p[3]

    @staticmethod
    def p_dedented_expression_number(p):
        """
expression : NUMBER

"""
        p[0] = p[1]

class ParserTablesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = _generated_parser()
        cls._directory = tempfile.TemporaryDirectory()
        cls.path = _dump(cls._directory.name)
        cls.tables = _tables.load(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls._directory.cleanup()

    def test_dump_is_compact_json(self):
        with open(self.path, 'r', encoding='utf-8') as file_h:
            text = file_h.read()
        data = json.loads(text)
        self.assertEqual(text, json.dumps(data, separators=(',', ':')))
        # the keys are sorted, the states numerically
        self.assertEqual(list(data), sorted(data))
        self.assertEqual(list(data['action']), sorted(data['action'], key=int))
        self.assertEqual(list(data['action']['0']), sorted(data['action']['0']))
        self.assertEqual(set(data), {'action', 'goto', 'method', 'productions', 'signature', 'tabversion'})
        self.assertEqual(data['tabversion'], yacc.__tabversion__)
        self.assertEqual(data['method'], 'LALR')

    def test_load_round_trip(self):
        tables = self.tables
        self.assertIsInstance(tables, types.ModuleType)
        self.assertEqual(tables.__name__, 'rule_engine.parser.parsetab')
        self.assertEqual(tables.__file__, self.path)
        self.assertEqual(tables._tabversion, yacc.__tabversion__)
        self.assertEqual(tables._lr_method, 'LALR')
        self.assertEqual(tables._lr_signature, _tables.signature(self.parser))
        for table in (tables._lr_action, tables._lr_goto):
            self.assertTrue(table)
            self.assertTrue(all(isinstance(state, int) for state in table))
        self.assertEqual(tables._lr_action, self.parser._parser.action)
        self.assertEqual(tables._lr_goto, self.parser._parser.goto)
        # nonassociative operators leave None in the action table
        self.assertTrue(any(None in entries.values() for entries in tables._lr_action.values()))

        productions = tables._lr_productions
        self.assertEqual(len(productions), len(self.parser._parser.productions))
        self.assertTrue(all(isinstance(production, tuple) and len(production) == 6 for production in productions))
        self.assertEqual(productions[0], ("S' -> statement", "S'", 1, None, None, None))
        for production, original in zip(productions[1:], self.parser._parser.productions[1:]):
            self.assertEqual(
                production,
                (original.str, original.name, original.len, original.func, '__init__.py', original.line)
            )

    def _parser_from_tables(self, cls):
        stderr = io.StringIO()
        with unittest.mock.patch.object(_tables, 'load', return_value=self.tables), \
                unittest.mock.patch.object(yacc, 'LRGeneratedTable', side_effect=AssertionError('generated tables')), \
                _no_writes() as writes, contextlib.redirect_stderr(stderr):
            parser_ = cls()
        self.assertEqual(writes, [])
        self.assertEqual(stderr.getvalue(), '')
        self.assertIs(parser_._parser.action, self.tables._lr_action)
        return parser_

    def test_parser_from_tables(self):
        parser_ = self._parser_from_tables(parser.Parser)
        for text in _RULES:
            self.assertEqual(_evaluate(parser_, text), _evaluate(self.parser, text), msg=text)
        # comparisons are nonassociative
        with self.assertRaises(errors.RuleSyntaxError):
            parser_.parse('a == b == c', engine.Context())

    def test_parser_subclass_from_tables(self):
        parser_ = self._parser_from_tables(_SameGrammarParser)
        self.assertEqual(_evaluate(parser_, 'a + b * 2'), 7)
        with self.assertRaisesRegex(errors.RuleSyntaxError, 'custom syntax error'):
            parser_.parse('a ==', engine.Context())

    def test_signature(self):
        signatures = []
        original = yacc.ParserReflect.signature
        def record(reflection):
            signatures.append(original(reflection))
            return signatures[-1]
        with unittest.mock.patch.object(_tables, 'load', return_value=self.tables), \
                unittest.mock.patch.object(yacc.ParserReflect, 'signature', record):
            parser_ = parser.Parser()
        self.assertEqual(set(signatures), {_tables.signature(parser.Parser)})
        self.assertEqual(_tables.signature(parser_), _tables.signature(parser.Parser))
        self.assertEqual(_tables.signature(_SameGrammarParser), _tables.signature(parser.Parser))
        self.assertNotEqual(_tables.signature(_CalculatorParser), _tables.signature(parser.Parser))

    def test_dump_from_loaded_tables(self):
        with unittest.mock.patch.object(_tables, 'load', return_value=self.tables):
            parser_ = parser.Parser()
        path = os.path.join(self._directory.name, 'reloaded.json')
        _tables.dump(parser_, path)
        with open(self.path, 'rb') as file_h, open(path, 'rb') as reloaded_h:
            self.assertEqual(file_h.read(), reloaded_h.read())

class ParserTablesLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._directory = tempfile.TemporaryDirectory()
        with open(_dump(cls._directory.name), 'r', encoding='utf-8') as file_h:
            cls.document = json.load(file_h)

    @classmethod
    def tearDownClass(cls):
        cls._directory.cleanup()

    def _write(self, content):
        path = os.path.join(self._directory.name, 'tables.json')
        with open(path, 'w', encoding='utf-8') as file_h:
            file_h.write(content if isinstance(content, str) else json.dumps(content))
        return path

    def _document(self, **changes):
        document = json.loads(json.dumps(self.document))
        document.update(changes)
        return document

    def test_load_missing(self):
        self.assertIsNone(_tables.load(os.path.join(self._directory.name, 'missing.json')))

    def test_load_unreadable(self):
        self.assertIsNone(_tables.load(self._directory.name))

    def test_load_invalid_json(self):
        for content in ('', '{', 'null', '\xff'):
            self.assertIsNone(_tables.load(self._write(content)), msg=content)

    def test_load_wrong_shape(self):
        production = self.document['productions'][1]
        documents = (
            [],
            {},
            {key: value for key, value in self.document.items() if key != 'signature'},
            self._document(action=[]),
            self._document(action={'0': []}),
            self._document(action={'zero': {}}),
            self._document(action={'0': {'SYMBOL': '11'}}),
            self._document(goto={'0': {'1': 1.5}}),
            self._document(productions={}),
            self._document(productions=['abcdef']),
            self._document(productions=[production[:5]]),
            self._document(productions=[production + [None]]),
            self._document(productions=[[production[0], production[1], '1'] + production[3:]]),
            self._document(productions=[production[:5] + ['1']]),
        )
        for document in documents:
            self.assertIsNone(_tables.load(self._write(document)), msg=document)
        # an unchanged copy does load
        tables = _tables.load(self._write(self._document()))
        self.assertEqual(tables._lr_signature, self.document['signature'])

    def test_load_tabversion(self):
        # ply warns about tables for another version before building them
        self.assertIsNone(_tables.load(self._write(self._document(tabversion='3.8'))))

    def test_load_packaged(self):
        content = json.dumps(self.document).encode()
        with unittest.mock.patch('pkgutil.get_data', return_value=content) as mock_get_data:
            tables = _tables.load()
        mock_get_data.assert_called_once_with('rule_engine.parser', 'parsetab.json')
        self.assertEqual(tables.__file__, _PACKAGED_PATH)
        self.assertEqual(tables._lr_signature, self.document['signature'])

    def test_load_packaged_missing(self):
        with unittest.mock.patch('pkgutil.get_data', side_effect=FileNotFoundError):
            self.assertIsNone(_tables.load())
        # loaders that can't read files return None
        with unittest.mock.patch('pkgutil.get_data', return_value=None):
            self.assertIsNone(_tables.load())

    @unittest.skipUnless(os.path.isfile(_PACKAGED_PATH), 'the packaged parser tables have not been generated')
    def test_load_packaged_file(self):
        tables = _tables.load()
        self.assertEqual(tables.__file__, _PACKAGED_PATH)
        self.assertIsNotNone(tables._lr_signature)

    def test_parser_without_tables(self):
        parser_ = _generated_parser()
        self.assertIsInstance(parser_._parser.productions[0], yacc.Production)
        for text in _RULES:
            self.assertIsNotNone(_evaluate(parser_, text), msg=text)
        self.assertEqual(_evaluate(parser_, 'a + b * 2'), 7)

    def test_debug_parser_writes_no_files(self):
        stderr = io.StringIO()
        with unittest.mock.patch.object(_tables, 'load', return_value=None), _no_writes() as writes, \
                contextlib.redirect_stderr(stderr):
            parser_ = parser.Parser(debug=True)
        self.assertEqual(writes, [])
        self.assertIn('Generating LALR tables', stderr.getvalue())
        self.assertNotIn("Couldn't", stderr.getvalue())
        self.assertEqual(_evaluate(parser_, 'a + b * 2'), 7)

class ParserTablesGrammarTests(unittest.TestCase):
    def test_subclass_grammar(self):
        with tempfile.TemporaryDirectory() as directory:
            tables = _tables.load(_dump(directory))
        stderr = io.StringIO()
        # rule_engine's tables don't match so ply builds the tables for this grammar
        with unittest.mock.patch.object(_tables, 'load', return_value=tables), _no_writes() as writes, \
                contextlib.redirect_stderr(stderr):
            parser_ = _CalculatorParser()
            dedented_parser = _DedentedCalculatorParser()
        self.assertEqual(writes, [])
        self.assertEqual(stderr.getvalue(), '')
        self.assertIsInstance(parser_._parser.productions[0], yacc.Production)
        self.assertEqual(parser_.parse('1 + 2 * 3', engine.Context()), 7)
        self.assertEqual(dedented_parser.parse('2 * 3 + 1', engine.Context()), 7)
        with self.assertRaises(errors.RuleSyntaxError):
            parser_.parse('1 +', engine.Context())

    def test_package_parsetab(self):
        name = '_rule_engine_tests_grammar'
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        package = os.path.join(directory.name, name)
        os.mkdir(package)
        with open(os.path.join(package, '__init__.py'), 'w', encoding='utf-8') as file_h:
            file_h.write(_PACKAGE_SOURCE.format(module=__name__))
        sys.path.insert(0, directory.name)
        self.addCleanup(sys.path.remove, directory.name)
        for module_name in (name, name + '.parsetab'):
            self.addCleanup(sys.modules.pop, module_name, None)
        with unittest.mock.patch.object(sys, 'dont_write_bytecode', True):
            module = importlib.import_module(name)
        # other grammars aren't normalized so their signatures and the tables they already ship don't change
        raw_docstrings = module.Calculator.raw_docstrings
        self.assertEqual(len(raw_docstrings), 2)
        self.assertEqual({name: getattr(module.Calculator, name).__doc__ for name in raw_docstrings}, raw_docstrings)
        self.assertTrue(any(line != line.strip() for doc in raw_docstrings.values() for line in doc.splitlines()))
        signature = _tables.signature(module.Calculator)
        self.assertTrue(all(doc in signature for doc in raw_docstrings.values()))
        # write the package's parsetab.py the way ply does by default
        yacc.yacc(
            module=module.Calculator.__new__(module.Calculator),
            debug=False,
            outputdir=package,
            debuglog=yacc.NullLogger(),
            errorlog=yacc.NullLogger()
        )
        importlib.invalidate_caches()
        files = sorted(os.listdir(package))
        self.assertEqual(files, ['__init__.py', 'parsetab.py'])

        stderr = io.StringIO()
        with unittest.mock.patch.object(yacc, 'LRGeneratedTable', side_effect=AssertionError('generated tables')), \
                _no_writes() as writes, contextlib.redirect_stderr(stderr):
            parser_ = module.Calculator()
            debug_parser = module.Calculator(debug=True)
        self.assertEqual(writes, [])
        self.assertNotIn('WARNING', stderr.getvalue())
        self.assertEqual(sorted(os.listdir(package)), files)
        for calculator in (parser_, debug_parser):
            self.assertIs(calculator._parser.action, sys.modules[name + '.parsetab']._lr_action)
            self.assertEqual(calculator.parse('1 + 2 * 3', engine.Context()), 9)

class ParserTablesNormalizationTests(unittest.TestCase):
    def _grammar_functions(self, cls):
        for name in dir(cls):
            function = getattr(getattr(cls, name), '__func__', getattr(cls, name))
            if name.startswith('p_') and name != 'p_error' and isinstance(function, types.FunctionType):
                yield function

    def test_docstrings_are_normalized(self):
        for cls in (parser.Parser, _CalculatorParser, _DedentedCalculatorParser):
            functions = tuple(self._grammar_functions(cls))
            self.assertEqual(len(functions), len([name for name in dir(cls) if name.startswith('p_')]) - 1)
            for function in functions:
                self.assertEqual(function.__doc__, function.__doc__.rstrip(), msg=function.__qualname__)
                for line in function.__doc__.splitlines():
                    self.assertEqual(line, line.strip(), msg=function.__qualname__)

    def test_docstring_literals(self):
        self.assertEqual(parser.Parser.p_statement_expr.__doc__, '\nstatement : expression\n| expression COMMENT')
        self.assertEqual(parser.Parser.p_expression_group.__doc__, 'object : LPAREN expression RPAREN')
        self.assertEqual(_CalculatorParser.p_statement.__doc__, '\nstatement : expression')
        self.assertEqual(_CalculatorParser.p_expression_number.__doc__, '\nexpression : NUMBER')

    def test_normalization_is_inherited(self):
        self.assertEqual(
            _ExtendedParser.p_expression_extended.__doc__,
            '\nobject : LPAREN LPAREN expression RPAREN RPAREN\n| LBRACKET LBRACKET expression RBRACKET RBRACKET'
        )
        self.assertNotEqual(_tables.signature(_ExtendedParser), _tables.signature(parser.Parser))

    def test_normalization_is_idempotent(self):
        docstrings = {function: function.__doc__ for function in self._grammar_functions(parser.Parser)}
        parser.Parser.__init_subclass__()
        self.assertEqual({function: function.__doc__ for function in docstrings}, docstrings)

    def test_normalization_ignores_indentation(self):
        self.assertEqual(_tables.signature(_CalculatorParser), _tables.signature(_DedentedCalculatorParser))

    def test_production_line_numbers(self):
        productions = _generated_parser()._parser.productions[1:]
        self.assertTrue(productions)
        for production in productions:
            lines, first_line = inspect.getsourcelines(getattr(parser.Parser, production.func))
            source = lines[production.line - first_line].strip().strip('\'"').split()
            self.assertTrue(source, msg=production.str)
            if source[0] == '|':
                symbols = source[1:]
            else:
                self.assertEqual(source[:2], [production.name, ':'])
                symbols = source[2:]
            if '%prec' in symbols:
                symbols = symbols[:symbols.index('%prec')]
            self.assertEqual(' '.join(symbols), production.str.split(' -> ', 1)[1], msg=production.str)

class ParserTablesCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._directory = tempfile.TemporaryDirectory()
        cls.path = _dump(cls._directory.name)
        with open(cls.path, 'r', encoding='utf-8') as file_h:
            cls.document = json.load(file_h)
        with unittest.mock.patch.object(_tables, 'load', return_value=_tables.load(cls.path)):
            cls.loaded_parser = parser.Parser()

    @classmethod
    def tearDownClass(cls):
        cls._directory.cleanup()

    def _main(self, *argv):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = _tables.main(list(argv))
        return result, stderr.getvalue()

    def _write(self, name, **changes):
        document = json.loads(json.dumps(self.document))
        document.update(changes)
        path = os.path.join(self._directory.name, name)
        with open(path, 'w', encoding='utf-8') as file_h:
            json.dump(document, file_h)
        return path

    def test_main_write(self):
        path = os.path.join(self._directory.name, 'written.json')
        # the tables of the rule parser are written without building them again
        with unittest.mock.patch.object(engine.Rule, 'parser', _generated_parser()), \
                unittest.mock.patch.object(yacc, 'yacc', side_effect=AssertionError('built a parser')):
            self.assertEqual(self._main(path), (0, ''))
        with open(self.path, 'rb') as file_h, open(path, 'rb') as written_h:
            self.assertEqual(file_h.read(), written_h.read())

    def test_main_check(self):
        self.assertEqual(self._main('--check', self.path), (0, ''))

    def test_main_check_packaged(self):
        with open(self.path, 'rb') as file_h:
            content = file_h.read()
        with unittest.mock.patch('pkgutil.get_data', return_value=content), \
                unittest.mock.patch.object(engine.Rule, 'parser', self.loaded_parser):
            self.assertEqual(self._main('--check'), (0, ''))
        with unittest.mock.patch('pkgutil.get_data', side_effect=FileNotFoundError):
            result, stderr = self._main('--check')
        self.assertEqual(result, 1)
        self.assertEqual(stderr, 'the parser tables could not be loaded from {}\n'.format(_PACKAGED_PATH))

    def test_main_check_packaged_unused(self):
        # the packaged tables can be used but the rule parser built its own
        with open(self.path, 'rb') as file_h:
            content = file_h.read()
        with unittest.mock.patch('pkgutil.get_data', return_value=content), \
                unittest.mock.patch.object(engine.Rule, 'parser', _generated_parser()):
            result, stderr = self._main('--check')
        self.assertEqual(result, 1)
        self.assertEqual(stderr, 'the rule parser did not use the parser tables in {}\n'.format(_PACKAGED_PATH))

    def test_main_check_stale(self):
        path = self._write('stale.json', signature='stale')
        result, stderr = self._main('--check', path)
        self.assertEqual(result, 1)
        self.assertEqual(stderr, 'the parser tables in {} do not match the grammar\n'.format(path))

    def test_main_check_missing(self):
        path = os.path.join(self._directory.name, 'missing.json')
        result, stderr = self._main('--check', path)
        self.assertEqual(result, 1)
        self.assertEqual(stderr, 'the parser tables could not be loaded from {}\n'.format(path))

    def test_main_check_tabversion(self):
        path = self._write('tabversion.json', tabversion='3.8')
        result, stderr = self._main('--check', path)
        self.assertEqual(result, 1)
        self.assertEqual(stderr, 'the parser tables could not be loaded from {}\n'.format(path))

    def test_main_check_renamed_function(self):
        # the signature only covers the grammar so renaming a rule's function doesn't change it
        text = json.dumps(self.document['productions'])
        productions = json.loads(text.replace('"p_expression_add"', '"p_expression_plus"'))
        path = self._write('renamed.json', productions=productions)
        result, stderr = self._main('--check', path)
        self.assertEqual(result, 1)
        self.assertEqual(
            stderr,
            'the parser tables in {} can not be used (WARNING: There was a problem loading the table file: '
            "KeyError('p_expression_plus'))\n".format(path)
        )

    def test_main_usage_error(self):
        for argv in ((), ('--bogus',), ('one.json', 'two.json')):
            with self.assertRaises(SystemExit) as context:
                self._main(*argv)
            self.assertEqual(context.exception.code, 2, msg=argv)

    def test_main_module(self):
        for path, code in ((self.path, 0), (self._write('stale.json', signature='stale'), 1)):
            with unittest.mock.patch.object(sys, 'argv', ['rule_engine.parser', '--check', path]), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as context:
                    runpy.run_module('rule_engine.parser', run_name='__main__')
            self.assertEqual(context.exception.code, code)

if __name__ == '__main__':
    unittest.main()
