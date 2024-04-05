#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/parser/base.py
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

import threading

import ply.lex as lex
import ply.yacc as yacc

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
		Parse the specified text in an abstract syntax tree of nodes that can later be evaluated. This is done in two
		phases. First, the syntax is parsed and a tree of deferred / uninitialized AST nodes are constructed. Next each
		node is built recursively using it's respective :py:meth:`rule_engine.ast.ASTNodeBase.build`.

		:param str text: The grammar text to parse into an AST.
		:param context: A context for specifying parsing and evaluation options.
		:type context: :py:class:`~rule_engine.engine.Context`
		:return: The parsed AST statement.
		:rtype: :py:class:`~rule_engine.ast.Statement`
		"""
		kwargs['lexer'] = kwargs.pop('lexer', self._lexer)
		with self.__mutex:
			self.context = context
			# phase 1: parse the string into a tree of deferred nodes
			result = self._parser.parse(text, **kwargs)
			self.context = None
		# phase 2: initialize each AST node recursively, providing them with an opportunity to define assignments
		return result.build()
