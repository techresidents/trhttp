import os
#import setuptools

from setuptools import setup
#from distutils.core import setup

def find_packages():
    packages = []
    for dir,subdirs,files in os.walk('trhttp'):
        package = dir.replace(os.path.sep, '.')
        if '__init__.py' not in files:
            # not a package
            continue
        packages.append(package)
    return packages

setup(
    name='trhttp',
    version = '0.2.0',
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
    ]
)
