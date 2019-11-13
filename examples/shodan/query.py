#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  examples/shodan/query.py
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
import gzip
import json
import os

import shodan

DESCRIPTION = 'Query results from Shodan'

def main():
	parser = argparse.ArgumentParser(
		conflict_handler='resolve',
		description=DESCRIPTION,
		formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument('--api-key', default=os.getenv('SHODAN_API_KEY'), help='the API key')
	parser.add_argument('--gzip', action='store_true', default=False, help='compress the file')
	parser.add_argument('json_file', type=argparse.FileType('wb'), help='the JSON file to write to')
	parser.add_argument('query', nargs='+', help='the search queries to retrieve')
	arguments = parser.parse_args()

	if arguments.api_key is None:
		print('[-] The --api-key must be specified or the SHODAN_API_KEY environment variable must be defined')
		return os.EX_CONFIG
	api = shodan.Shodan(arguments.api_key)

	all_results = []
	for query in arguments.query:
		print('[*] Querying: ' + query)

		search_results = api.search(query)
		all_results.extend(search_results['matches'])

	output = '\n'.join(json.dumps(result) for result in all_results)
	output = output.encode('utf-8')
	if arguments.gzip:
		output = gzip.compress(output)
	arguments.json_file.write(output)

if __name__ == '__main__':
	main()