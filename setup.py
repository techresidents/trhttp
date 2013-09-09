import os
from setuptools import setup, find_packages, Extension

import ez_setup
ez_setup.use_setuptools()

setup(
    name='trhttp',
    version = '0.6-SNAPSHOT',
    author = 'Tech Residents, Inc.',
    packages = find_packages(),
    license = open('LICENSE').read(),
    description = 'Tech Residents Http Library',
    long_description = open('README').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Distributed Computing',
        ],
    install_requires=[
        'trpycore>=0.11.0'
    ],
    dependency_links=[
        'git+ssh://dev.techresidents.com/tr/repos/techresidents/lib/python/trpycore.git@0.11.0#egg=trpycore-0.11.0'
    ],
)
