#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages

setup(name='orpyus',
      version='1.0',
      description='A python library for handling music theory concepts and assisting music analysis',
      author='Andrey Barsky',
      author_email='andrey.barsky@gmail.com',
      install_requires=['numpy', 'scipy', 'matplotlib', 'sounddevice'],
      extras_require={
        'dev': [ 'ipdb' ]
        'test': [ 'pytest' ]
      },
      package_dir = {'orpyus': 'src'}
     )
