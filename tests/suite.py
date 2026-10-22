#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tests/suite.py
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
import os
import sys
import unittest
import unittest.mock

import tests

__all__ = ('SuiteTests',)

def _test_ids(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from _test_ids(test)
        else:
            yield test.id()

class SuiteTests(unittest.TestCase):
    def test_discovery_collects_each_test_once(self):
        test_ids = list(_test_ids(unittest.TestLoader().loadTestsFromName('tests')))
        duplicates = sorted(test_id for test_id, count in collections.Counter(test_ids).items() if count > 1)
        self.assertEqual(duplicates, [])
        # discovering from the package directory runs the same load_tests hook as python -m unittest without importing
        # anything else that is in the directory above it
        package_dir = os.path.dirname(os.path.abspath(tests.__file__))
        # discovery adds the top level directory to the import path
        with unittest.mock.patch.object(sys, 'path', list(sys.path)):
            discovered = unittest.TestLoader().discover(package_dir, top_level_dir=os.path.dirname(package_dir))
        self.assertCountEqual(_test_ids(discovered), test_ids)

if __name__ == '__main__':
    unittest.main()
