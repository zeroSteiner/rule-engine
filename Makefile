VERSION := $(shell uv run python -c "import rule_engine; print(rule_engine.__version__)")

.PHONY: build
build:
	uv build

.PHONY: clean
clean:
	rm -rf build dist

.PHONY: docs
docs:
	uv sync --group dev
	uv run sphinx-build -b html -a -E -v docs/source docs/html

.PHONY: release
release: build
	$(eval RELEASE_TAG := v$(VERSION))
	git tag -sm "Version $(VERSION)" $(RELEASE_TAG)
	git push --tags

