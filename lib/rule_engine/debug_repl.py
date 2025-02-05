#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/debug_repl.py
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
import code
import pprint
import re
import textwrap
import traceback

from . import __version__
from . import engine
from . import errors

try:
	from IPython import embed
	from prompt_toolkit import PromptSession
except ImportError:
	has_development_dependencies = False
else:
	has_development_dependencies = True

def main():
	parser = argparse.ArgumentParser(description='Rule Engine: Debug REPL', conflict_handler='resolve')
	parser.add_argument(
		'--debug',
		action='store_true',
		default=False,
		help='enable debugging output'
	)
	parser.add_argument(
		'--edit-console',
		action='store_true',
		default=False,
		help='edit the environment (via an interactive console)'
	)
	parser.add_argument(
		'--edit-file',
		metavar='<path>',
		type=argparse.FileType('r'),
		help='edit the environment (via a file)'
	)
	parser.add_argument('-v', '--version', action='version', version=parser.prog + ' Version: ' + __version__)
	arguments = parser.parse_args()

	if not has_development_dependencies:
		parser.error('development dependencies are not installed, install them with: pipenv install --dev')

	context = engine.Context()
	thing = None
	if arguments.edit_console or arguments.edit_file:
		console = code.InteractiveConsole({
			'context': context,
			'thing': thing
		})
		if arguments.edit_file:
			print('executing: ' + arguments.edit_file.name)
			console.runcode(code.compile_command(
				arguments.edit_file.read(),
				filename=arguments.edit_file.name,
				symbol='exec'
			))
			context = console.locals['context']
			thing = console.locals['thing']
		if arguments.edit_console:
			namespace = {'context': context, 'thing': thing}
			print("Starting IPython shell...")
			print("Edit the \'context\' and \'thing\' objects as necessary")
			embed(colors="neutral", user_ns=namespace)
			context = namespace.get('context', context)
			thing = namespace.get('thing', thing)
	debugging = arguments.debug
	session = PromptSession()

	while True:
		try:
			rule_text = session.prompt('rule > ')
		except (EOFError, KeyboardInterrupt):
			break

		match = re.match(r'\s*#!\s*debug\s*=\s*(\w+)', rule_text)
		if match:
			debugging = match.group(1).lower() != 'false'
			print('# debugging = ' + str(debugging).lower())
			continue

		try:
			rule = engine.Rule(rule_text, context=context)
			result = rule.evaluate(thing)
		except errors.EngineError as error:
			print("{}: {}".format(error.__class__.__name__, error.message))
			if isinstance(error, (errors.AttributeResolutionError, errors.SymbolResolutionError)) and error.suggestion:
				print("Did you mean '{}'?".format(error.suggestion))
			elif isinstance(error, errors.RegexSyntaxError):
				print("  Regex:   {!r}".format(error.error.pattern))
				print("  Details: {} at position {}".format(error.error.msg, error.error.pos))
			elif isinstance(error, errors.FunctionCallError):
				print("  Function:  {!r}".format(error.function_name))
				if debugging and error.error:
					inner_exception = ''.join(traceback.format_exception(
						error.error,
						error.error,
						error.error.__traceback__
					))
					print(textwrap.indent(inner_exception, ' ' * 4))
			if debugging:
				traceback.print_exc()
		except Exception as error:
			traceback.print_exc()
		else:
			print('result: ')
			pprint.pprint(result, indent=4)

if __name__ == '__main__':
	main()
