#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/parser/__init__.py
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

import ast as pyast
import collections
import types as pytypes

from .. import ast
from .. import errors
from .base import ParserBase
from .utilities import timedelta_regex

literal_eval = pyast.literal_eval

class _DeferredAstNode(object):
	__slots__ = ('cls', 'args', 'kwargs', 'method')
	def __init__(self, cls, *, args, kwargs=None, method='build'):
		if not issubclass(cls, ast.ASTNodeBase):
			raise TypeError('cls is not a subclass of AstNodeBase')
		self.cls = cls
		self.args = args
		self.kwargs = kwargs or {}
		self.method = method

	def build(self):
		constructor = getattr(self.cls, self.method)
		return constructor(*self.args, **self.kwargs)

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
		'and': 'AND',   'or': 'OR',     'not': 'NOT',
		'for': 'FOR',   'if': 'IF',
		# other operators
		'.':   'ATTR',
		'&.':  'ATTR_SAFE',
		'in':  'IN',
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
		'in': 'IN',
		'or': 'OR',
		'not': 'NOT',
		'for': 'FOR',
		'if': 'IF'
	}
	tokens = (
		'BYTES', 'DATETIME', 'TIMEDELTA', 'FLOAT', 'STRING', 'SYMBOL',
		'LPAREN', 'RPAREN', 'QMARK', 'COLON', 'COMMA',
		'LBRACKET', 'RBRACKET', 'LBRACE', 'RBRACE', 'COMMENT'
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
	t_COMMA            = r'\,'
	t_LBRACKET         = r'((?<=\S)&)?\['
	t_RBRACKET         = r'\]'
	t_LBRACE           = r'\{'
	t_RBRACE           = r'\}'
	t_FLOAT            = r'0(b[01]+|o[0-7]+|x[0-9a-fA-F]+)|[0-9]+(\.[0-9]*)?([eE][+-]?[0-9]+)?|\.[0-9]+([eE][+-]?[0-9]+)?'
	# attributes must be valid symbol names so the right side is more specific
	t_ATTR             = r'(?<=\S)\.(?=[a-zA-Z_][a-zA-Z0-9_]*)'
	t_ATTR_SAFE        = r'(?<=\S)&\.(?=[a-zA-Z_][a-zA-Z0-9_]*)'

	# Tokens are listed from highest to lowest precedence, ones that appear
	# later are effectively evaluated last
	# see:
	#   * https://en.wikipedia.org/wiki/Order_of_operations#Programming_languages
	#   * https://docs.python.org/3/reference/expressions.html
	precedence = tuple(
		# reverse the order to lowest to highest for ply
		reversed((
			('nonassoc', 'LPAREN', 'RPAREN'),
			('left',     'ATTR', 'ATTR_SAFE'),
			('right',    'UMINUS'),
			('left',     'POW'),
			('left',     'MUL', 'TDIV', 'FDIV', 'MOD'),
			('left',     'BWLSH', 'BWRSH'),
			('left',     'ADD', 'SUB'),
			('nonassoc', 'EQ', 'NE', 'EQ_FZM', 'EQ_FZS', 'NE_FZM', 'NE_FZS', 'GE', 'GT', 'LE', 'LT', 'IN'),  # Nonassociative operators
			('right',    'QMARK', 'COLON'),
			('left',     'BWAND'),
			('left',     'BWXOR'),
			('left',     'BWOR'),
			('right',    'NOT'),
			('left',     'AND'),
			('left',     'OR'),
		)
	))

	@classmethod
	def get_token_regex(cls, token_name):
		"""
		Return the regex that is used by the specified token.

		:param str token_name: The token for which to return the regex.
		:rtype: str
		"""
		obj = getattr(cls, 't_' + token_name, None)
		if isinstance(obj, str):
			return obj
		elif isinstance(obj, pytypes.FunctionType):
			return obj.__doc__
		raise ValueError('unknown token: ' + token_name)

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

	def t_BYTES(self, t):
		r'b(?P<quote>["\'])([^\\\n]|(\\.))*?(?P=quote)'
		t.value = t.value[1:]
		return t

	def t_DATETIME(self, t):
		r'd(?P<quote>["\'])([^\\\n]|(\\.))*?(?P=quote)'
		t.value = t.value[2:-1]
		return t

	def t_TIMEDELTA(self, t):
		r't(?P<quote>["\'])([^\\\n]|(\\.))*?(?P=quote)'
		t.value = t.value[2:-1]
		return t

	def t_STRING(self, t):
		r's?(?P<quote>["\'])([^\\\n]|(\\.))*?(?P=quote)'
		if t.value[0] == 's':
			t.value = t.value[1:]
		return t

	def t_SYMBOL(self, t):
		r'\$?[a-zA-Z_][a-zA-Z0-9_]*'
		if t.value in ('elif', 'else', 'while'):
			raise errors.RuleSyntaxError("syntax error (the {} keyword is reserved for future use)".format(t.value))
		t.type = self.reserved_words.get(t.value, 'SYMBOL')
		return t

	def t_COMMENT(self, t):
		r'\#.*$'
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
		"""
		statement : expression
		          | expression COMMENT
		"""
		kwargs = {}
		if len(p) == 3:
			kwargs['comment'] = ast.Comment(p[2][1:].strip())
		p[0] = _DeferredAstNode(ast.Statement, args=(self.context, p[1]), kwargs=kwargs)

	def p_expression_getattr(self, p):
		"""
		object : object ATTR SYMBOL
		       | object ATTR_SAFE SYMBOL
		"""
		op_name = self.op_names.get(p[2])
		p[0] = _DeferredAstNode(ast.GetAttributeExpression, args=(self.context, p[1], p[3]), kwargs={'safe': op_name == 'ATTR_SAFE'})

	def p_expression_object(self, p):
		"""
		expression : object
		"""
		p[0] = p[1]

	def p_expression_ternary(self, p):
		"""
		expression : expression QMARK expression COLON expression
		"""
		condition, _, case_true, _, case_false = p[1:6]
		p[0] = _DeferredAstNode(ast.TernaryExpression, args=(self.context, condition, case_true, case_false))

	def p_expression_arithmetic(self, p):
		"""
		expression : expression MOD    expression
				   | expression MUL    expression
				   | expression FDIV   expression
				   | expression TDIV   expression
				   | expression POW    expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = _DeferredAstNode(ast.ArithmeticExpression, args=(self.context, op_name, left, right))

	def p_expression_add(self, p):
		"""
		expression : expression ADD    expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = _DeferredAstNode(ast.AddExpression, args=(self.context, op_name, left, right))

	def p_expression_sub(self, p):
		"""
		expression : expression SUB    expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = _DeferredAstNode(ast.SubtractExpression, args=(self.context, op_name, left, right))

	def p_expression_bitwise(self, p):
		"""
		expression : expression BWAND  expression
				   | expression BWOR   expression
				   | expression BWXOR  expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = _DeferredAstNode(ast.BitwiseExpression, args=(self.context, op_name, left, right))

	def p_expression_bitwise_shift(self, p):
		"""
		expression : expression BWLSH  expression
				   | expression BWRSH  expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = _DeferredAstNode(ast.BitwiseShiftExpression, args=(self.context, op_name, left, right))

	def p_expression_contains(self, p):
		"""
		expression : expression IN     expression
				   | expression NOT IN expression
		"""
		if len(p) == 4:
			member, _, container = p[1:4]
			p[0] = _DeferredAstNode(ast.ContainsExpression, args=(self.context, container, member))
		else:
			member, _, _, container = p[1:5]
			p[0] = _DeferredAstNode(ast.ContainsExpression, args=(self.context, container, member))
			p[0] = _DeferredAstNode(ast.UnaryExpression, args=(self.context, 'NOT', p[0]))

	def p_expression_comparison(self, p):
		"""
		expression : expression EQ     expression
				   | expression NE     expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = _DeferredAstNode(ast.ComparisonExpression, args=(self.context, op_name, left, right))

	def p_expression_arithmetic_comparison(self, p):
		"""
		expression : expression GT     expression
				   | expression GE     expression
				   | expression LT     expression
				   | expression LE     expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = _DeferredAstNode(ast.ArithmeticComparisonExpression, args=(self.context, op_name, left, right))

	def p_expression_fuzzy_comparison(self, p):
		"""
		expression : expression EQ_FZM expression
				   | expression EQ_FZS expression
				   | expression NE_FZM expression
				   | expression NE_FZS expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = _DeferredAstNode(ast.FuzzyComparisonExpression, args=(self.context, op_name, left, right))

	def p_expression_logic(self, p):
		"""
		expression : expression AND    expression
				   | expression OR     expression
		"""
		left, op, right = p[1:4]
		op_name = self.op_names[op]
		p[0] = _DeferredAstNode(ast.LogicExpression, args=(self.context, op_name, left, right))

	def p_expression_group(self, p):
		'object : LPAREN expression RPAREN'
		p[0] = p[2]

	def p_expression_negate(self, p):
		'expression : NOT expression'
		p[0] = _DeferredAstNode(ast.UnaryExpression, args=(self.context, 'NOT', p[2]))

	def p_expression_symbol(self, p):
		'object : SYMBOL'
		name = p[1]
		scope = None
		if name[0] == '$':
			scope = 'built-in'
			name = name[1:]
		p[0] = _DeferredAstNode(ast.SymbolExpression, args=(self.context, name), kwargs={'scope': scope})

	def p_expression_uminus(self, p):
		'expression : SUB expression %prec UMINUS'
		names = {'-': 'UMINUS'}
		p[0] = _DeferredAstNode(ast.UnaryExpression, args=(self.context, names[p[1]], p[2]))

	# Literal expressions
	def p_expression_boolean(self, p):
		"""
		expression : TRUE
				   | FALSE
		"""
		p[0] = _DeferredAstNode(ast.BooleanExpression, args=(self.context, p[1] == 'true'))

	def p_expression_bytes(self, p):
		'object : BYTES'
		try:
			value = literal_eval('b' + p[1])
		except Exception:
			raise errors.BytesSyntaxError('invalid bytes literal', p[1][1:-1]) from None
		p[0] = _DeferredAstNode(ast.BytesExpression, args=(self.context, value))

	def p_expression_datetime(self, p):
		'object : DATETIME'
		p[0] = _DeferredAstNode(ast.DatetimeExpression, args=(self.context, p[1]), method='from_string')

	def p_expression_timedelta(self, p):
		'object : TIMEDELTA'
		p[0] = _DeferredAstNode(ast.TimedeltaExpression, args=(self.context, p[1]), method='from_string')

	def p_expression_float(self, p):
		"""
		expression : FLOAT
				   | FLOAT_NAN
				   | FLOAT_INF
		"""
		str_val = p[1]
		p[0] = _DeferredAstNode(ast.FloatExpression, args=(self.context, str_val), method='from_string')

	def p_expression_null(self, p):
		'object : NULL'
		# null is an object because of the safe operator
		p[0] = _DeferredAstNode(ast.NullExpression, args=(self.context,))

	def p_expression_set(self, p):
		"""
		object : LBRACE ary_members RBRACE
			   | LBRACE ary_members COMMA RBRACE
		"""
		p[0] = _DeferredAstNode(ast.SetExpression, args=(self.context, tuple(p[2])))

	def p_expression_string(self, p):
		'object : STRING'
		try:
			value = literal_eval(p[1])
		except Exception:
			raise errors.StringSyntaxError('invalid string literal', p[1][1:-1]) from None
		p[0] = _DeferredAstNode(ast.StringExpression, args=(self.context, value))

	def p_expression_array(self, p):
		"""
		object : LBRACKET RBRACKET
			   | LBRACKET ary_members RBRACKET
			   | LBRACKET ary_members COMMA RBRACKET
		"""
		if len(p) < 4:
			p[0] = _DeferredAstNode(ast.ArrayExpression, args=(self.context, tuple()))
		else:
			p[0] = _DeferredAstNode(ast.ArrayExpression, args=(self.context, tuple(p[2])))

	def p_expression_array_comprehension(self, p):
		"""
		object : LBRACKET expression FOR SYMBOL IN expression RBRACKET
			   | LBRACKET expression FOR SYMBOL IN expression IF expression RBRACKET
		"""
		condition = None
		if len(p) == 10:
			condition = p[8]
		p[0] = _DeferredAstNode(ast.ComprehensionExpression, args=(self.context, p[2], p[4], p[6]), kwargs={'condition': condition})

	def p_expression_array_members(self, p):
		"""
		ary_members : expression
					| ary_members COMMA expression
		"""
		if len(p) == 2:
			deque = collections.deque()
			deque.append(p[1])
		else:
			deque = p[1]
			deque.append(p[3])
		p[0] = deque

	def p_expression_mapping(self, p):
		"""
		object : LBRACE RBRACE
			   | LBRACE map_members RBRACE
			   | LBRACE map_members COMMA RBRACE
		"""
		if len(p) < 4:
			p[0] = _DeferredAstNode(ast.MappingExpression, args=(self.context, tuple()))
		else:
			p[0] = _DeferredAstNode(ast.MappingExpression, args=(self.context, tuple(p[2])))

	def p_expression_mapping_member(self, p):
		"""
		map_member : expression COLON expression
		"""
		p[0] = (p[1], p[3])

	def p_expression_mapping_members(self, p):
		"""
		map_members : map_member
					| map_members COMMA map_member
		"""
		return self.p_expression_array_members(p)

	def p_expression_getitem(self, p):
		"""
		object : object LBRACKET expression RBRACKET
		"""
		container, lbracket, item = p[1:4]
		p[0] = _DeferredAstNode(ast.GetItemExpression, args=(self.context, container, item), kwargs={'safe': lbracket == '&['})

	def p_expression_getslice(self, p):
		"""
		object : object LBRACKET COLON RBRACKET
		       | object LBRACKET COLON expression RBRACKET
		       | object LBRACKET expression COLON RBRACKET
		       | object LBRACKET expression COLON expression RBRACKET
		"""
		container = p[1]
		safe = p[2] == '&['
		colon_index = p[1:].index(':')
		if colon_index == 2 and len(p) == 5:
			start, stop = None, None
		elif colon_index == 2 and len(p) == 6:
			start, stop = None, p[4]
		elif colon_index == 3 and len(p) == 6:
			start, stop = p[3], None
		elif colon_index == 3 and len(p) == 7:
			start, _, stop = p[3:6]
		else:
			raise errors.RuleSyntaxError('invalid get slice expression')
		p[0] = _DeferredAstNode(ast.GetSliceExpression, args=(self.context, container, start, stop), kwargs={'safe': safe})

	def p_expression_function_call(self, p):
		"""
		object : expression LPAREN RPAREN
		       | expression LPAREN ary_members RPAREN
		"""
		function = p[1]
		if len(p) == 4:
			arguments = collections.deque()
		elif len(p) == 5:
			arguments = p[3]
		else:
			raise errors.RuleSyntaxError('invalid function call expression')
		p[0] = _DeferredAstNode(ast.FunctionCallExpression, args=(self.context, function, arguments))
