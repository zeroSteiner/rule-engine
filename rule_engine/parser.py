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

from . import ast
from . import errors

import ply.lex as lex
import ply.yacc as yacc

literal_eval = ast_.literal_eval

class ParserBase(object):
	precedence = ()
	tokens = ()
	reserved = {}
	def __init__(self, debug=False):
		self.debug = debug
		# Build the lexer and parser
		self._lexer = lex.lex(module=self, debug=self.debug)
		self._parser = yacc.yacc(module=self, debug=self.debug, write_tables=self.debug)

	def parse(self, *args, **kwargs):
		kwargs['lexer'] = kwargs.pop('lexer', self._lexer)
		return self._parser.parse(*args, **kwargs)

class Parser(ParserBase):
	reserved = {
		'and':   'AND',
		'or':    'OR',
		'true':  'TRUE',
		'false': 'FALSE',
	}
	tokens = [
		'FLOAT', 'INTEGER', 'STRING',
		'LPAREN', 'RPAREN', 'SYMBOL',
		'EQ', 'EQ_RE', 'NE', 'NE_RE', 'QMARK', 'COLON'
	] + list(reserved.values())

	# Tokens
	t_LPAREN           = r'\('
	t_RPAREN           = r'\)'
	t_EQ               = r'=='
	t_EQ_RE            = r'=~'
	t_NE               = r'!='
	t_NE_RE            = r'!~'
	t_QMARK            = r'\?'
	t_COLON            = r'\:'
	t_STRING           = r'(?P<quote>["\'])([^\\\n]|(\\.))*?(?P=quote)'

	t_ignore = ' \t'
	precedence = (
		('left',     'AND', 'OR'),
		('right',    'QMARK', 'COLON'),
		('nonassoc', 'EQ', 'NE', 'EQ_RE', 'NE_RE'),  # Nonassociative operators
	)

	def t_INTEGER(self, t):
		r'0(b[01]+|o[0-7]+|x[0-9a-f]+)|[0-9]+(\.[0-9]*)?|\.[0-9]+'
		if '.' in t.value:
			t.type = 'FLOAT'
		return t

	def t_SYMBOL(self, t):
		r'[a-zA-Z_][a-zA-Z0-9_]*'
		t.type = self.reserved.get(t.value, 'SYMBOL')
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
		p[0] = ast.Statement(p[1])

	def p_expression_ternary(self, p):
		"""
		expression : expression QMARK expression COLON expression
		"""
		p[0] = ast.TernaryExpression(p[1], p[3], p[5])

	def p_expression_logic(self, p):
		"""
		expression : expression EQ    expression
				   | expression NE    expression
				   | expression AND   expression
				   | expression OR    expression
				   | expression EQ_RE expression
				   | expression NE_RE expression
		"""
		p[0] = ast.LogicExpression(p[2], p[1], p[3])

	def p_expression_boolean(self, p):
		"""
		expression : TRUE
				   | FALSE
		"""
		p[0] = ast.BooleanExpression(p[1] == 'true')

	def p_expression_float(self, p):
		'expression : FLOAT'
		p[0] = ast.FloatExpression(literal_eval(p[1]))

	def p_expression_integer(self, p):
		'expression : INTEGER'
		p[0] = ast.IntegerExpression(literal_eval(p[1]))

	def p_expression_group(self, p):
		'expression : LPAREN expression RPAREN'
		p[0] = p[2]

	def p_expression_string(self, p):
		'expression : STRING'
		p[0] = ast.StringExpression(literal_eval(p[1]))

	def p_expression_symbol(self, p):
		'expression : SYMBOL'
		p[0] = ast.SymbolExpression(p[1])
