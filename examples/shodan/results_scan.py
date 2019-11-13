#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  examples/shodan/results_scan.py
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
import re
import sys

get_path = functools.partial(os.path.join, os.path.abspath(os.path.join(os.path.dirname(__file__))))
sys.path.append(get_path())
sys.path.append(get_path('..', '..', 'lib'))

import results_filter
import rule_engine

import yaml

DESCRIPTION = 'Scan results exported from Shodan for vulnerabilities.'
RULES_FILE = get_path('rules.yml')

def _print_references(references):
	cves = references.get('cves')
	if cves and len(cves) == 1:
		print('CVE: CVE-' + cves[0])
	elif cves and len(cves) > 1:
		print('CVEs: ')
		for cve in cves:
			print('  * CVE-' + cve)

	msf_modules = references.get('metasploit-modules')
	if msf_modules and len(msf_modules) == 1:
		print('Metasploit Module: ' + msf_modules[0])
	elif msf_modules and len(msf_modules) > 1:
		print('Metasploit Modules:')
		for msf_module in msf_modules:
			print('  * ' + msf_module)

def main():
	parser = argparse.ArgumentParser(
		conflict_handler='resolve',
		description=DESCRIPTION,
		formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument('--gzip', action='store_true', default=False, help='decompress the file')
	parser.add_argument('json_file', type=argparse.FileType('rb'), help='the JSON file to filter')
	arguments = parser.parse_args()

	re_flags = re.IGNORECASE | re.MULTILINE
	context = rule_engine.Context(default_value=None, regex_flags=re_flags)

	file_object = arguments.json_file
	if arguments.gzip:
		file_object = gzip.GzipFile(fileobj=file_object)
	results = [json.loads(line.decode('utf-8')) for line in file_object]

	with open(RULES_FILE, 'r') as file_h:
		rules = yaml.load(file_h, Loader=yaml.FullLoader)

	for vulnerability in rules['rules']:
		try:
			rule = rule_engine.Rule(vulnerability['rule'], context=context)
		except rule_engine.RuleSyntaxError as error:
			print(error.message)
			return 0

		matches = tuple(rule.filter(results))
		if not matches:
			continue

		print(vulnerability['description'])
		references = vulnerability.get('references', {})
		_print_references(references)
		print('Hosts:')
		for match in matches:
			print("  * {}".format(results_filter.result_to_url(match)))
		print()
	return 0

if __name__ == '__main__':
	sys.exit(main())

