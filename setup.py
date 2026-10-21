"""
Generate the parser tables when the package is built, so the wheel ships them and importing rule_engine doesn't need
to build them. All other metadata is in pyproject.toml.
"""
import os
import subprocess
import sys

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

# run the command line from the built package, its path is an argument because it can contain os.pathsep
GENERATE = (
    'import runpy, sys; '
    'sys.path.insert(0, sys.argv.pop(1)); '
    'runpy.run_module("rule_engine.parser", run_name="__main__")'
)


class build_py(_build_py):
    def _tables_path(self):
        return os.path.join(self.build_lib, 'rule_engine', 'parser', 'parsetab.json')

    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        # parsetab.py is left in source trees by older versions and isn't part of the package
        return [module for module in modules if module[:2] != ('rule_engine.parser', 'parsetab')]

    def run(self):
        super().run()
        # editable installs don't get the tables, `invoke tables` generates them in the source tree that lenient
        # editable installs use
        if self.editable_mode:
            return
        path = self._tables_path()
        # tables left in a reused build directory would be loaded and dumped again with stale line numbers
        if os.path.exists(path):
            os.remove(path)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        # the grammar is in docstrings, so they can't be removed
        env.pop('PYTHONOPTIMIZE', None)
        # -B keeps bytecode out of the wheel
        command = [sys.executable, '-B', '-c', GENERATE, os.path.abspath(self.build_lib), path]
        subprocess.run(command, env=env, check=True)

    def get_outputs(self, include_bytecode=True):
        outputs = super().get_outputs(include_bytecode)
        if not self.editable_mode:
            outputs.append(self._tables_path())
        return outputs


setup(cmdclass={'build_py': build_py})
