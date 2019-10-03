#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  examples/github_filter.py
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
import getpass
import os
import sys

try:
	import github
except ImportError:
	print('this script requires PyGithub', file=sys.stderr)
	sys.exit(os.EX_UNAVAILABLE)

DESCRIPTION = 'Apply a rule to filter pull requests or issues from GitHub.'
EPILOG = """\
example rules:
  * Show all merged pull requests by user zeroSteiner
    "user.login == 'zeroSteiner' and merged"
  * Show open issues assigned to user zeroSteiner
    "state != 'open' and assignee and assignee.login == 'zeroSteiner'"
"""

get_path = functools.partial(os.path.join, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(get_path('lib'))

import rule_engine
import rule_engine.engine

def _get_github(arguments):
	if arguments.auth_token:
		gh = github.Github(arguments.auth_token)
	elif arguments.auth_user:
		password = getpass.getpass("{0}@github.com: ".format(arguments.auth_user))
		gh = github.Github(arguments.auth_user, password)
	else:
		gh = github.Github()
	return gh

def main():
	parser = argparse.ArgumentParser(
		conflict_handler='resolve',
		description=DESCRIPTION,
		formatter_class=argparse.RawDescriptionHelpFormatter
	)
	auth_type_parser_group = parser.add_mutually_exclusive_group()
	auth_type_parser_group.add_argument('--auth-token', dest='auth_token', help='authenticate to github with a token')
	auth_type_parser_group.add_argument('--auth-user', dest='auth_user', help='authenticate to github with credentials')
	parser.add_argument('repo_slug', help='the repository to filter')
	parser.add_argument('type', choices=('issues', 'pulls'), help='thing to filter')
	parser.add_argument('rule', help='the rule to apply')
	parser.epilog = EPILOG
	arguments = parser.parse_args()

	# need to define a custom context to use a custom resolver function
	context = rule_engine.Context(resolver=rule_engine.engine.resolve_attribute)
	try:
		rule = rule_engine.Rule(arguments.rule, context=context)
	except rule_engine.RuleSyntaxError as error:
		print(error.message)
		return 0

	gh = _get_github(arguments)
	repo = gh.get_repo(arguments.repo_slug)
	things = tuple(getattr(repo, 'get_' + arguments.type)(state='all'))
	for thing in rule.filter(things):
		print("{0}#{1: <4} - {2}".format(arguments.repo_slug, thing.number, thing.title))
	return 0

if __name__ == '__main__':
	sys.exit(main())
