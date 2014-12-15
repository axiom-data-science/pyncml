from __future__ import with_statement
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

version = "0.0.6"


def readme():
    with open('README.md') as f:
        return f.read()

reqs = [line.strip() for line in open('requirements.txt')]


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

setup(
    name                = "pyncml",
    version             = version,
    description         = "A simple python library to apply NcML logic to NetCDF files",
    long_description    = readme(),
    license             = 'LGPLv3',
    author              = "Kyle Wilcox",
    author_email        = "kyle@axiomalaska.com",
    url                 = "https://github.com/axiomalaska/pyncml",
    packages            = find_packages(),
    install_requires    = reqs,
    tests_require       = ['pytest'],
    cmdclass            = {'test': PyTest},
    classifiers         = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
    ],
    include_package_data = True,
)
