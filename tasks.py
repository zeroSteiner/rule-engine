import pathlib
import shutil

from invoke import task

PARSER_TABLES = 'lib/rule_engine/parser/parsetab.json'
# the generated tables and the parsetab.py that older versions wrote
PARSER_FILES = (PARSER_TABLES, 'lib/rule_engine/parser/parsetab.py')
# ply's description of the grammar, nothing reads it
PARSER_DEBUG = 'lib/rule_engine/parser/parser.out'


@task
def clean(c):
    """Remove build artifacts."""
    # a stale SOURCES.txt in the egg-info can add leftover files to the sdist
    for path in ('build', 'dist', 'lib/rule_engine.egg-info'):
        shutil.rmtree(path, ignore_errors=True)
    for path in PARSER_FILES + (PARSER_DEBUG,):
        pathlib.Path(path).unlink(missing_ok=True)


@task(pre=[clean])
def build(c):
    """Build the distribution packages."""
    c.run('uv build')


@task
def docs(c):
    """Build the HTML documentation."""
    c.run('uv sync --group dev')
    c.run('uv run sphinx-build -b html -a -E -v docs/source docs/html')


@task(help={'debug': 'Also write the grammar debug output to parser.out.'})
def tables(c, debug=False):
    """Generate the parser tables."""
    # existing tables would be loaded and dumped again with stale line numbers, and the parser would still import the
    # parsetab.py older versions left behind, the debug output is kept because the tests task runs this one again
    # without --debug
    for path in PARSER_FILES:
        pathlib.Path(path).unlink(missing_ok=True)
    c.run('uv run python -m rule_engine.parser ' + ('--debug ' if debug else '') + PARSER_TABLES)


@task(pre=[tables], help={'coverage': 'Measure test coverage and print a report.'})
def tests(c, coverage=False):
    """Run unit tests."""
    if coverage:
        c.run('uv run python -m coverage run -m unittest -v tests', pty=True)
        c.run('uv run python -m coverage report')
    else:
        c.run('uv run python -m unittest -v tests', pty=True)

@task(aliases=['checktypes'])
def typechecks(c):
    """Run mypy static type checks."""
    c.run('uv run mypy')


@task(pre=[build])
def release(c):
    """Tag and push the current version as a release."""
    version = c.run(
        'uv run python -c "import rule_engine; print(rule_engine.__version__)"',
        dry=False,
        hide=True
    ).stdout.strip()
    release_tag = 'v' + version
    c.run('git tag -sm "Version {0}" {1}'.format(version, release_tag))
    c.run('git push --tags')

