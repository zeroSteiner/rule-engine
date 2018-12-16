#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/errors.py
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

class EngineError(Exception):
	"""
	The base exception class from which other exceptions within this package
	inherit.
	"""
	def __init__(self, message=''):
		"""
		:param str message: A text description of what error occurred.
		"""
		self.message = message
		"""The message describing the error that occurred."""

class EvaluationError(EngineError):
	"""
	An error raised for issues which occur while the rule is being evaluated.
	This can occur at parse time while AST nodes are being evaluated during
	the reduction phase.
	"""
	pass

class SyntaxError(EngineError):
	"""A base error for syntax related issues."""

class DatetimeSyntaxError(SyntaxError):
	"""
	An error raised for issues regarding the use of improperly formatted
	datetime expressions.
	"""
	def __init__(self, message, value):
		super(DatetimeSyntaxError, self).__init__(message)
		self.value = value
		"""
		The datetime value which contains the syntax error which caused this
		exception to be raised.
		"""

class RuleSyntaxError(SyntaxError):
	"""
	An error raised for issues identified in while parsing the grammar of the
	rule text.
	"""
	def __init__(self, message, token=None):
		if token is None:
			position = 'EOF'
		else:
			position = "line {0}:{1}".format(token.lineno, token.lexpos)
		message = message + ' at: ' + position
		super(RuleSyntaxError, self).__init__(message)
		self.token = token
		"""The PLY token (if available) which is related to the syntax error."""

class RegexSyntaxError(SyntaxError):
	"""
	An error raised for issues regarding the use of improper regular expression
	syntax.
	"""
	def __init__(self, message, error):
		super(RegexSyntaxError, self).__init__(message)
		self.error = error
		"""The :py:exc:`re.error` exception from which this error was triggered."""

	@property
	def value(self):
		"""
		The regular expression value which contains the syntax error which
		caused this exception to be raised.
		"""
		return self.error.pattern

class SymbolResolutionError(EvaluationError):
	"""
	An error raised when a symbol name is not able to be resolved to a value.
	"""
	def __init__(self, symbol_name, symbol_scope=None):
		"""
		:param str symbol_name: The name of the symbol that can not be resolved.
		:param str symbol_scope: The scope of where the symbol should be valid for resolution.
		"""
		self.symbol_name = symbol_name
		"""The name of the symbol that can not be resolved."""
		self.symbol_scope = symbol_scope
		"""The scope of where the symbol should be valid for resolution."""
		super(SymbolResolutionError, self).__init__("unknown symbol: {0!r}".format(symbol_name))

class SymbolTypeError(EvaluationError):
	"""
	An error raised when a symbol with type information is resolved to a python
	value that is not of that type.
	"""
	def __init__(self, symbol_name, is_value, is_type, expected_type):
		self.symbol_name = symbol_name
		"""The name of the symbol that is of an incompatible type."""
		self.is_value = is_value
		"""The native Python value of the incompatible symbol."""
		self.is_type = is_type
		"""The :py:class:`rule-engine type<rule_engine.ast.DataType>` of the incompatible symbol."""
		self.expected_type = expected_type
		"""The :py:class:`rule-engine type<rule_engine.ast.DataType>` that was expected for this symbol."""
		message = "symbol {0!r} resolved to incorrect datatype (is: {1}, expected: {2})".format(symbol_name, is_type.name, expected_type.name)
		super(SymbolTypeError, self).__init__(message)

