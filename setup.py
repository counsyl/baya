from setuptools import find_packages
from setuptools import setup


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

setup(
    name='baya',
    version=version,
    description="Nested LDAP Groups authorization.",
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
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    install_requires=[
        'django-auth-ldap>=1.2.8',
        'Django>=2.2',
        'six>=1.3',
    ],
    packages=find_packages(exclude=[
        'tests', 'tests.*']),
    include_package_data=True,
    extras_require={
        'development': [
            'mockldap>=0.2.0',
        ],
    },
)
