PACKAGE_NAME?=baya
VENV_DIR?=.venv
VENV_ACTIVATE=$(VENV_DIR)/bin/activate
WITH_VENV=. $(VENV_ACTIVATE);
TEST_OUTPUT?=nosetests.xml

ifdef TOX_ENV
	TOX_ENV_FLAG := -e $(TOX_ENV)
else
	TOX_ENV_FLAG :=
endif

.PHONY: default
default:
	python setup.py check build

.PHONY: venv
venv: $(VENV_ACTIVATE)

$(VENV_ACTIVATE): requirements*.txt setup.py
	test -f $@ || virtualenv --python=python2.7 $(VENV_DIR)
	$(WITH_VENV) pip install --no-deps -r requirements-setup.txt
	$(WITH_VENV) pip install -e .
	$(WITH_VENV) pip install --no-deps -r requirements-dev.txt

develop: venv
	$(WITH_VENV) python setup.py develop

.PHONY: setup
setup: venv

.PHONY: clean
clean:
	python setup.py clean
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg*/
	rm -rf __pycache__/
	rm -f MANIFEST
	rm -f $(TEST_OUTPUT)
	find $(PACKAGE_NAME) -type f -name '*.pyc' -delete

.PHONY: teardown
teardown:
	rm -rf .tox $(VENV_DIR)/

.PHONY: lint
lint: venv
	$(WITH_VENV) flake8 -v $(PACKAGE_NAME)/

.PHONY: test
test: venv
	$(WITH_VENV) \
	coverage erase ; \
	tox -v $(TOX_ENV_FLAG); \
	status=$$?; \
	coverage combine; \
	coverage html --directory=coverage --omit="tests*"; \
	coverage report; \
	xunitmerge nosetests-*.xml $(TEST_OUTPUT); \
	exit $$status;

# Distribution
VERSION=`$(WITH_VENV) python setup.py --version`

.PHONY: version
version: venv
version:
	@echo ${VERSION}

.PHONY: tag
tag: ##[distribution] Tag the release.
tag: venv
	echo "Tagging version as ${VERSION}"
	git tag -a ${VERSION} -m 'Version ${VERSION}'
	# We won't push changes or tags here allowing the pipeline to do that, so we don't accidentally do that locally.

.PHONY: dist
dist: venv
	$(WITH_VENV) python setup.py sdist

.PHONY: sdist
sdist: dist
	@echo "runs dist"
