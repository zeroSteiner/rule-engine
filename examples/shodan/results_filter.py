#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  examples/shodan/results_filter.py
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

import argparse
import functools
import gzip
import json
import os
import pprint
import re
import sys

get_path = functools.partial(os.path.join, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(get_path('lib'))

import rule_engine

BLACKLIST = ('_shodan', 'asn', 'hash', 'ip')
DESCRIPTION = 'Apply a rule to filter results exported from Shodan.'
EPILOG = """\
example rules:
  * Find all HTTPS servers missing the Strict-Transport-Security header
    "http and ssl and data !~~ '^Strict-Transport-Security:\s'"
  * Find OpenSSH servers on non-default ports
    "product == 'OpenSSH' and port != 22"
"""

def result_to_url(result):
	protocol = result['transport']
	if 'http' in result:
		protocol = 'https' if 'ssl' in result else 'http'
	return "{protocol}://{ip_str}:{port}".format(protocol=protocol, **result)

def main():
	parser = argparse.ArgumentParser(
		conflict_handler='resolve',
		description=DESCRIPTION,
		formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument('-d', '--depth', default=2, type=int, help='the depth to pretty print')
	parser.add_argument('--gzip', action='store_true', default=False, help='decompress the file')
	parser.add_argument('--regex-case-sensitive', default=False, action='store_true', help='use case-sensitive regular expressions')
	parser.add_argument('json_file', type=argparse.FileType('rb'), help='the JSON file to filter')
	parser.add_argument('rule', help='the rule to apply')
	parser.epilog = EPILOG
	arguments = parser.parse_args()

	re_flags = re.MULTILINE
	if arguments.regex_case_sensitive:
		re_flags &= re.IGNORECASE

	context = rule_engine.Context(default_value=None, regex_flags=re_flags)
	try:
		rule = rule_engine.Rule(arguments.rule, context=context)
	except rule_engine.RuleSyntaxError as error:
		print(error.message)
		return 0

	file_object = arguments.json_file
	if arguments.gzip:
		file_object = gzip.GzipFile(fileobj=file_object)

	total = 0
	matches = 0
	for line in file_object:
		result = json.loads(line.decode('utf-8'))
		total += 1
		if not rule.matches(result):
			continue
		matches += 1
		print(result_to_url(result))
		if arguments.depth > 0:
			for key in BLACKLIST:
				result.pop(key, None)
			pprint.pprint(result, depth=arguments.depth)
	print("rule matched {:,} of {:,} results ({:.2f}%)".format(matches, total, ((matches / total) * 100)))
	return 0

if __name__ == '__main__':
	sys.exit(main())
