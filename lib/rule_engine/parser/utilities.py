#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/parser/utilities.py
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
import binascii
import datetime
import decimal
import re

from . import errors

import dateutil.parser

_sub_regex = r'[0-9]+([,.][0-9]+)?'
timedelta_regex = (
	r'P(?!\b)'
	r'(?P<weeks>' + _sub_regex + r'W)?'
	r'(?P<days>' + _sub_regex + r'D)?'
	r'(T'
	r'(?P<hours>' + _sub_regex + r'H)?'
	r'(?P<minutes>' + _sub_regex + r'M)?'
	r'(?P<seconds>' + _sub_regex + r'S)?'
	r')?'
)

def parse_datetime(string, default_timezone):
	"""
	Parse a timestamp string. If the timestamp does not specify a timezone, *default_timezone* is used.

	:param str string: The string to parse.
	:param datetime.tzinfo default_timezone: The default timezone to set.
	:rtype: datetime.datetime
	"""
	try:
		dt = dateutil.parser.isoparse(string)
	except ValueError:
		raise errors.DatetimeSyntaxError('invalid datetime literal', string) from None
	if dt.tzinfo is None:
		dt = dt.replace(tzinfo=default_timezone)
	return dt

def parse_float(string):
	"""
	Parse a literal string representing a floating point value.

	:param str string: The string to parse.
	:rtype: decimal.Decimal
	"""
	if re.match('^0[0-9]', string):
		raise errors.FloatSyntaxError('invalid floating point literal (leading zeros in decimal literals are not permitted)', string)
	try:
		if re.match('^0[box]', string):
			val = decimal.Decimal(pyast.literal_eval(string))
		else:
			val = decimal.Decimal(string)
	except Exception:
		raise errors.FloatSyntaxError('invalid floating point literal', string) from None
	return val

def parse_timedelta(string):
	"""
	Parse a literal string representing a time period in the ISO-8601 duration format.

	:param str string: The string to parse.
	:rtype: datetime.timedelta
	"""
	if string == "P":
		raise errors.TimedeltaSyntaxError('empty timedelta string', string)

	match = re.match("^" + timedelta_regex + "$", string)
	if not match:
		raise errors.TimedeltaSyntaxError('invalid timedelta string', string)

	groups = match.groupdict()
	for key, val in groups.items():
		if val is None:
			val = "0n"
		groups[key] = float(val[:-1].replace(',', '.'))

	return datetime.timedelta(
		weeks=groups['weeks'],
		days=groups['days'],
		hours=groups['hours'],
		minutes=groups['minutes'],
		seconds=groups['seconds'],
	)
