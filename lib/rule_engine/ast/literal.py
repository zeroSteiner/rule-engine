#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/ast/literal.py
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

import collections

from .. import errors
from ..parser.utilities import parse_datetime, parse_float, parse_timedelta
from ..types import DataType, coerce_value

from .base import LiteralExpressionBase, _is_reduced, _iterable_member_value_type

################################################################################
# Literal Expressions
################################################################################
class _CollectionMixin(object):
	def evaluate(self, thing):
		return self.result_type.python_type(member.evaluate(thing) for member in self.value)

	@property
	def is_reduced(self):
		return _is_reduced(*self.value)

	def to_graphviz(self, digraph, *args, **kwargs):
		super(_CollectionMixin, self).to_graphviz(digraph, *args, **kwargs)
		for member in self.value:
			member.to_graphviz(digraph, *args, **kwargs)
			digraph.edge(str(id(self)), str(id(member)))

class ArrayExpression(_CollectionMixin, LiteralExpressionBase):
	"""Literal array expressions containing 0 or more sub-expressions."""
	result_type = DataType.ARRAY
	def __init__(self, *args, **kwargs):
		super(ArrayExpression, self).__init__(*args, **kwargs)
		self.result_type = DataType.ARRAY(value_type=_iterable_member_value_type(self.value))

	@classmethod
	def build(cls, context, value):
		return cls(context, [member.build() for member in value])

class BooleanExpression(LiteralExpressionBase):
	"""Literal boolean expressions representing True or False."""
	result_type = DataType.BOOLEAN

class BytesExpression(LiteralExpressionBase):
	"""
	Literal bytes expressions representing a binary string. This expression type always evaluates to true when not empty.
	"""
	result_type = DataType.BYTES

class DatetimeExpression(LiteralExpressionBase):
	"""
	Literal datetime expressions representing a specific point in time. This expression type always evaluates to true.
	"""
	result_type = DataType.DATETIME
	@classmethod
	def from_string(cls, context, string):
		dt = parse_datetime(string, default_timezone=context.default_timezone)
		return cls(context, dt)

class TimedeltaExpression(LiteralExpressionBase):
	"""
	Literal timedelta expressions representing an offset from a specific point in time.

	.. versionadded:: 3.5.0
	"""
	result_type = DataType.TIMEDELTA
	@classmethod
	def from_string(cls, context, string):
		return cls(context, parse_timedelta(string))

class FloatExpression(LiteralExpressionBase):
	"""Literal float expressions representing numerical values."""
	result_type = DataType.FLOAT
	def __init__(self, context, value, **kwargs):
		value = coerce_value(value)
		super(FloatExpression, self).__init__(context, value, **kwargs)

	@classmethod
	def from_string(cls, context, string):
		return cls(context, parse_float(string))

class FunctionExpression(LiteralExpressionBase):
	"""Literal mapping expression representing a function."""
	# there's no syntax for defining functions, but this is required by the parser when a method is referred to on a
	# literal value, e.g. `b"41".decode('utf-8')`
	result_type = DataType.FUNCTION

class MappingExpression(LiteralExpressionBase):
	"""Literal mapping expression representing a set of associations between keys and values."""
	result_type = DataType.MAPPING
	def __init__(self, context, value, **kwargs):
		if isinstance(value, dict):
			value = tuple(value.items())
		super(MappingExpression, self).__init__(context, value, **kwargs)
		self.result_type = DataType.MAPPING(
			key_type=_iterable_member_value_type(key for key, _ in self.value),
			value_type=_iterable_member_value_type(value for _, value in self.value)
		)

	@classmethod
	def build(cls, context, value):
		value = collections.OrderedDict(value)
		value = collections.OrderedDict((k.build(), v.build()) for k, v in value.items())
		return cls(context, value)

	def evaluate(self, thing):
		mapping = collections.OrderedDict()
		for key, value in self.value:
			key = key.evaluate(thing)
			key_type = DataType.from_value(key)
			if key_type.is_compound and not isinstance(key_type, DataType.ARRAY.__class__):
				raise errors.EngineError("the {} data type may not be used for mapping keys".format(key_type.name))
			mapping[key] = value
		# defer value evaluation to avoid evaluating values of duplicate keys
		for key, value in mapping.items():
			mapping[key] = value.evaluate(thing)
		return mapping

	@property
	def is_reduced(self):
		return all(_is_reduced(key, value) for key, value in self.value)

class NullExpression(LiteralExpressionBase):
	"""Literal null expressions representing null values. This expression type always evaluates to false."""
	result_type = DataType.NULL
	def __init__(self, context, value=None):
		# all of the literal expressions take a value
		if value is not None:
			raise TypeError('value must be None')
		super(NullExpression, self).__init__(context, value=None)

class SetExpression(_CollectionMixin, LiteralExpressionBase):
	"""Literal set expressions containing 0 or more sub-expressions."""
	result_type = DataType.SET
	def __init__(self, *args, **kwargs):
		super(SetExpression, self).__init__(*args, **kwargs)
		self.result_type = DataType.SET(value_type=_iterable_member_value_type(self.value))

	@classmethod
	def build(cls, context, value):
		value = set(member.build() for member in value)
		return cls(context, value)

class StringExpression(LiteralExpressionBase):
	"""Literal string expressions representing an array of characters."""
	result_type = DataType.STRING
