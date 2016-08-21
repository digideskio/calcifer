#!/usr/bin/env python
import codecs

from setuptools import setup, find_packages

exec(open("calcifer/_version.py").read())

def read_requirements_file(filename):
    """Read pip-formatted requirements from a file."""
    with open(filename, 'r') as f:
        return [line.strip() for line in f.readlines()
                if not line.startswith('#')]

setup(
    name='calcifer',
    description='A Python based policy framework.',
    version=__version__,
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    long_description=codecs.open('README.rst', encoding='utf-8').read(),
    install_requires=read_requirements_file('requirements.txt'),
    tests_require=read_requirements_file('requirements-tests.txt'),
    test_suite='nose.collector',
    author='DramaFever',
    author_email='admin@dramafever.com',
    url='https://github.com/DramaFever/calcifer',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
)
