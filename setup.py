import os

from pip.download import PipSession
from pip.req import parse_requirements
from setuptools import find_packages
from setuptools import setup


def load_readme():
    PROJECT_DIR = os.path.dirname(__file__)
    readme_file = "README.md"
    try:
        return open(os.path.join(PROJECT_DIR, readme_file), 'r').read()
    except Exception:
        raise RuntimeError("Cannot find readme file {fname}.".format(
            fname=readme_file))


def load_version():
    """Open and parse out the version number from the _version.py module.

    Inspired by http://stackoverflow.com/a/7071358
    """
    import re
    version_file = "baya/_version.py"
    version_line = open(version_file).read().rstrip()
    vre = re.compile(r'__version__ = "([^"]+)"')
    matches = vre.findall(version_line)
    if matches and len(matches) > 0:
        return matches[0]
    else:
        raise RuntimeError(
            "Cannot find version string in {version_file}.".format(
                version_file=version_file))

version = load_version()
long_description = load_readme()

# Build description from README and build metadata from Go pipeline.
long_description += "\n"
long_description += "build_revision: {}\n".format(os.getenv('GO_REVISION'))
long_description += "build_pipeline: {}\n".format(os.getenv('GO_PIPELINE_NAME'))
long_description += "build_label:    {}\n".format(os.getenv('GO_PIPELINE_LABEL'))

requirements = ['Django'] + [
    str(ir.req)
    for ir in parse_requirements('./requirements.txt', session=PipSession())]

test_requirements = [
    str(ir.req)
    for ir in parse_requirements('./requirements-dev.txt', session=PipSession())]

setup(
    name='baya',
    version=version,
    description="Nested LDAP Groups authorization.",
    long_description=long_description,
    author='Steven Buss',
    author_email='steven.buss@gmail.com',
    maintainer='Counsyl Platform Team',
    maintainer_email='platform@counsyl.com',
    license='MIT',
    url='https://github.com/counsyl/baya',
    download_url=(
        'https://github.com/counsyl/baya/tarball/v%s' %
        version),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],
    packages=find_packages(exclude=[
        'tests', 'tests.*']),
    include_package_data=True,
    install_requires=requirements,
    tests_require=test_requirements,
    extras_require={
        'development': [
            'mockldap>=0.2.0',
        ],
    },
)
