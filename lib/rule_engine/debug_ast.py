#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  rule_engine/debug_ast.py
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
import os

from . import __version__
from . import engine

def _print_written(file_path):
	size = os.stat(file_path).st_size
	print("wrote {:,} bytes to {}".format(size, file_path))

def main():
	parser = argparse.ArgumentParser(description='Rule Engine: Debug AST', conflict_handler='resolve')
	parser.add_argument('output', help='output files')
	parser.add_argument('-t', '--text', dest='rule_text', help='the rule text to debug')
	parser.add_argument('-v', '--version', action='version', version=parser.prog + ' Version: ' + __version__)
	arguments = parser.parse_args()

	rule_text = arguments.rule_text
	if not rule_text:
		rule_text = input('rule > ')

	rule = engine.Rule(rule_text)
	digraph = rule.to_graphviz()

	digraph.save(arguments.output + '.gv')
	_print_written(arguments.output + '.gv')

	digraph.render(arguments.output)
	_print_written(arguments.output + '.pdf')


if __name__ == '__main__':
	main()
