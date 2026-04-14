import shutil

from invoke import task


@task
def build(c):
    """Build the distribution packages."""
    c.run('uv build')


@task
def clean(c):
    """Remove build artifacts."""
    for path in ('build', 'dist'):
        shutil.rmtree(path, ignore_errors=True)


@task
def docs(c):
    """Build the HTML documentation."""
    c.run('uv sync --group dev')
    c.run('uv run sphinx-build -b html -a -E -v docs/source docs/html')


@task
def tests(c):
    """Run unit tests."""
    c.run('uv run python -m unittest -v', pty=True)

@task
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

