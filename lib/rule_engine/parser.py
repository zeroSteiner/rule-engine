#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/parser.py
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

import ast as ast_
import threading

from . import ast
from . import errors

import ply.lex as lex
import ply.yacc as yacc

literal_eval = ast_.literal_eval

class ParserBase(object):
	"""
	A base class for parser objects to inherit from. This does not provide any
	grammar related definitions.
	"""
	precedence = ()
	"""The precedence for operators."""
	tokens = ()
	reserved_words = {}
	"""
	A mapping of literal words which are reserved to their corresponding grammar
	names.
	"""
	__mutex = threading.Lock()
	def __init__(self, debug=False):
		"""
		:param bool debug: Whether or not to enable debugging features when
			using the ply API.
		"""
		self.debug = debug
		self.context = None
		# Build the lexer and parser
		self._lexer = lex.lex(module=self, debug=self.debug)
		self._parser = yacc.yacc(module=self, debug=self.debug, write_tables=self.debug)

	def parse(self, text, context, **kwargs):
		"""
		Parse the specified text in an abstract syntax tree of nodes that can
		later be evaluated.

		:param str text: The grammar text to parse into an AST.
		:param context: A context for specifying parsing and evaluation options.
		:type context: :py:class:`~rule_engine.engine.Context`
		:return: The parsed AST statement.
		:rtype: :py:class:`~rule_engine.ast.Statement`
		"""
		kwargs['lexer'] = kwargs.pop('lexer', self._lexer)
		with self.__mutex:
			self.context = context
			result = self._parser.parse(text, **kwargs)
			self.context = None
		return result

class Parser(ParserBase):
	"""
	The parser class for the rule grammar. This class contains many ply specific
	members to define the various components of the grammar allowing it to be
	parsed and reduced into an abstract syntax tree (AST). Once the AST has been
	constructed it can then be evaluated multiple times. To make the evaluation
	more efficient, nodes within the AST that are able to be reduced are while
	the parsing is taking place. This reduction phase involves evaluation,
	causing :py:exc:`~rule_engine.errors.EvaluationError` exceptions to be
	raised during parsing.
	"""
	op_names = {
		# arithmetic operators
		'+':   'ADD',   '-':  'SUB',
		'**':  'POW',   '*':  'MUL',
		'/':   'TDIV',  '//': 'FDIV', '%': 'MOD',
		# bitwise operators
		'&':   'BWAND', '|':  'BWOR', '^': 'BWXOR',
		'<<':  'BWLSH', '>>': 'BWRSH',
		# comparison operators
		'==':  'EQ',    '=~': 'EQ_FZM', '=~~': 'EQ_FZS',
		'!=':  'NE',    '!~': 'NE_FZM', '!~~': 'NE_FZS',
		'>':   'GT',    '>=': 'GE',
		'<':   'LT',    '<=': 'LE',
		# logical operators
		'and': 'AND',   'or': 'OR',
	}
	reserved_words = {
		# booleans
		'true':  'TRUE',
		'false': 'FALSE',
		# float constants
		'inf': 'FLOAT_INF',
		'nan': 'FLOAT_NAN',
		# null
		'null': 'NULL',
		# operators
		'and': 'AND',
		'or': 'OR',
		'not': 'NOT',
	}
	tokens = (
		'DATETIME', 'FLOAT', 'STRING', 'SYMBOL',
		'LPAREN', 'RPAREN', 'QMARK', 'COLON'
	) + tuple(set(list(reserved_words.values()) + list(op_names.values())))

	t_ignore = ' \t'
	# Tokens
	t_BWAND            = r'\&'
	t_BWOR             = r'\|'
	t_BWXOR            = r'\^'
	t_LPAREN           = r'\('
	t_RPAREN           = r'\)'
	t_EQ               = r'=='
	t_NE               = r'!='
	t_QMARK            = r'\?'
	t_COLON            = r'\:'
	t_ADD              = r'\+'
	t_SUB              = r'\-'
	t_MOD              = r'\%'
	t_FLOAT            = r'0(b[01]+|o[0-7]+|x[0-9a-fA-F]+)|[0-9]+(\.[0-9]*)?([eE][+-]?[0-9]+)?|\.[0-9]+([eE][+-]?[0-9]+)?'

	# tokens are listed from lowest to highest precedence, ones that appear
	# later are effectively evaluated first
	# see: https://en.wikipedia.org/wiki/Order_of_operations#Programming_languages
	precedence = (
		('left',     'OR'),
		('left',     'AND'),
		('right',    'NOT'),
		('left',     'BWOR'),
		('left',     'BWXOR'),
		('left',     'BWAND'),
		('right',    'QMARK', 'COLON'),
		('nonassoc', 'EQ', 'NE', 'EQ_FZM', 'EQ_FZS', 'NE_FZM', 'NE_FZS', 'GE', 'GT', 'LE', 'LT'),  # Nonassociative operators
		('left',     'ADD', 'SUB'),
		('left',     'BWLSH', 'BWRSH'),
		('left',     'MUL', 'TDIV', 'FDIV', 'MOD'),
		('left',     'POW'),
		('right',    'UMINUS'),
	)

	def t_POW(self, t):
		r'\*\*?'
		if t.value == '*':
			t.type = 'MUL'
		return t

	def t_FDIV(self, t):
		r'\/\/?'
		if t.value == '/':
			t.type = 'TDIV'
		return t

	def t_LT(self, t):
		r'<([=<])?'
		t.type = {'<': 'LT', '<=': 'LE', '<<': 'BWLSH'}[t.value]
		return t

	def t_GT(self, t):
		r'>([=>])?'
		t.type = {'>': 'GT', '>=': 'GE', '>>': 'BWRSH'}[t.value]
		return t

	def t_EQ_FZS(self, t):
		r'=~~?'
		if t.value == '=~':
			t.type = 'EQ_FZM'
		return t

	def t_NE_FZS(self, t):
		r'!~~?'
		if t.value == '!~':
			t.type = 'NE_FZM'
		return t

	def t_DATETIME(self, t):
		r'd(?P<quote>["\'])([^\\\n]|(\\.))*?(?P=quote)'
		t.value = t.value[1:]
		return t

	def t_STRING(self, t):
		r's?(?P<quote>["\'])([^\\\n]|(\\.))*?(?P=quote)'
		if t.value[0] == 's':
			t.value = t.value[1:]
		return t

	def t_SYMBOL(self, t):
		r'\$?[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*'
		t.type = self.reserved_words.get(t.value, 'SYMBOL')
		return t

	def t_newline(self, t):
		r'\n+'
		t.lexer.lineno += t.value.count("\n")

	def t_error(self, t):
		raise errors.RuleSyntaxError("syntax error (illegal character {0!r})".format(t.value[0]), t)

	# Parsing Rules
	def p_error(self, token):
		raise errors.RuleSyntaxError('syntax error', token)

	def p_statement_expr(self, p):
		'statement : expression'
		p[0] = ast.Statement(self.context, p[1])

	def p_expression_ternary(self, p):
		"""
		expression : expression QMARK expression COLON expression
		"""
		condition, _, case_true, _, case_false = p[1:6]
		p[0] = ast.TernaryExpression(self.context, condition, case_true, case_false).reduce()

	def p_expression_arithmetic(self, p):
		"""
		expression : expression ADD    expression
				   | expression SUB    expression
				   | expression MOD    expression
				   | expression MUL    expression
				   | expression FDIV   expression
				   | expression TDIV   expression
				   | expression POW    expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = ast.ArithmeticExpression(self.context, op_name, left, right).reduce()

	def p_expression_bitwise(self, p):
		"""
		expression : expression BWAND  expression
				   | expression BWOR   expression
				   | expression BWXOR  expression
				   | expression BWLSH  expression
				   | expression BWRSH  expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = ast.BitwiseExpression(self.context, op_name, left, right).reduce()

	def p_expression_comparison(self, p):
		"""
		expression : expression EQ     expression
				   | expression NE     expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = ast.ComparisonExpression(self.context, op_name, left, right).reduce()

	def p_expression_arithmetic_comparison(self, p):
		"""
		expression : expression GT     expression
				   | expression GE     expression
				   | expression LT     expression
				   | expression LE     expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = ast.ArithmeticComparisonExpression(self.context, op_name, left, right).reduce()

	def p_expression_fuzzy_comparison(self, p):
		"""
		expression : expression EQ_FZM expression
				   | expression EQ_FZS expression
				   | expression NE_FZM expression
				   | expression NE_FZS expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = ast.FuzzyComparisonExpression(self.context, op_name, left, right).reduce()

	def p_expression_logic(self, p):
		"""
		expression : expression AND    expression
				   | expression OR     expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = ast.LogicExpression(self.context, op_name, left, right).reduce()

	def p_expression_group(self, p):
		'expression : LPAREN expression RPAREN'
		p[0] = p[2]

	def p_expression_negate(self, p):
		'expression : NOT expression'
		p[0] = ast.UnaryExpression(self.context, 'NOT', p[2]).reduce()

	def p_expression_symbol(self, p):
		'expression : SYMBOL'
		name = p[1]
		scope = None
		if name[0] == '$':
			scope = 'built-in'
			name = name[1:]
		p[0] = ast.SymbolExpression(self.context, name, scope=scope).reduce()

	def p_expression_uminus(self, p):
		'expression : SUB expression %prec UMINUS'
		names = {'-': 'UMINUS'}
		p[0] = ast.UnaryExpression(self.context, names[p[1]], p[2]).reduce()

	# Literal expressions
	def p_expression_boolean(self, p):
		"""
		expression : TRUE
				   | FALSE
		"""
		p[0] = ast.BooleanExpression(self.context, p[1] == 'true')

	def p_expression_datetime(self, p):
		'expression : DATETIME'
		p[0] = ast.DatetimeExpression.from_string(self.context, literal_eval(p[1]))

	def p_expression_float(self, p):
		'expression : FLOAT'
		p[0] = ast.FloatExpression(self.context, float(literal_eval(p[1])))

	def p_expression_float_nan(self, p):
		'expression : FLOAT_NAN'
		p[0] = ast.FloatExpression(self.context, float('nan'))

	def p_expression_float_inf(self, p):
		'expression : FLOAT_INF'
		p[0] = ast.FloatExpression(self.context, float('inf'))

	def p_expression_null(self, p):
		"""expression : NULL"""
		p[0] = ast.NullExpression(self.context)

	def p_expression_string(self, p):
		'expression : STRING'
		p[0] = ast.StringExpression(self.context, literal_eval(p[1]))
