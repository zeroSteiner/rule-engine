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
import functools
import os
import pkgutil
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

def _module_names(path, prefix):
    # unlike pkgutil.walk_packages, this doesn't import the packages it finds
    for module_info in pkgutil.iter_modules(path, prefix):
        yield module_info.name
        if module_info.ispkg:
            package_dir = os.path.join(module_info.module_finder.path, module_info.name.rpartition('.')[2])
            yield from _module_names([package_dir], module_info.name + '.')

def _test_modules():
    return [(name, sys.modules[name]) for name in sorted(sys.modules) if name.startswith('tests.')]

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

    def test_every_test_class_is_collected(self):
        # a test class that is missing from its module's __all__ isn't imported by the package, so it never runs
        loader = unittest.TestLoader()
        collected = set(_test_ids(loader.loadTestsFromName('tests')))
        missing = []
        for name, module in _test_modules():
            for value in vars(module).values():
                if not (isinstance(value, type) and issubclass(value, unittest.TestCase) and value.__module__ == name):
                    continue
                # base classes run their tests through their subclasses
                if value.__name__.endswith('Base') and value.__subclasses__():
                    continue
                test_ids = _test_ids(loader.loadTestsFromTestCase(value))
                missing.extend(test_id for test_id in test_ids if test_id not in collected)
        self.assertEqual(missing, [])

    def test_every_test_module_is_imported(self):
        # the package imports every test module, a module that it doesn't import never runs
        package_dir = os.path.dirname(os.path.abspath(tests.__file__))
        self.assertEqual([name for name in _module_names([package_dir], 'tests.') if name not in sys.modules], [])

    def test_every_test_module_can_be_selected(self):
        # python -m unittest tests.engine looks the module up as an attribute of the package, so a star-imported alias
        # with the same name, such as rule_engine.engine, would replace it and no tests would be selected
        hidden = []
        for name, module in _test_modules():
            parts = name.split('.')[1:]
            resolved = functools.reduce(lambda parent, attribute: getattr(parent, attribute, None), parts, tests)
            if resolved is not module:
                hidden.append(name)
        self.assertEqual(hidden, [])

if __name__ == '__main__':
    unittest.main()
