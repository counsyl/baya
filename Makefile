PACKAGE_NAME?=baya
VENV_DIR?=.venv
VENV_ACTIVATE=$(VENV_DIR)/bin/activate
WITH_VENV=. $(VENV_ACTIVATE);

ifdef TRAVIS_PYTHON_VERSION
    PYTHON=python$(TRAVIS_PYTHON_VERSION)
else
    PYTHON=python3.9
endif

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
	pip install virtualenv==20.8.1
	test -f $@ || python3 -m venv $(VENV_DIR) || virtualenv --python=$(PYTHON) $(VENV_DIR)
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
	find $(PACKAGE_NAME) -type f -name '*.pyc' -delete

.PHONY: teardown
teardown:
	rm -rf .tox $(VENV_DIR)/

.PHONY: lint
lint: venv
	$(WITH_VENV) tox -e lint

.PHONY: test
test: venv
	$(WITH_VENV) \
	coverage erase ; \
	tox -v $(TOX_ENV_FLAG); \
	status=$$?; \
	coverage report; \
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
