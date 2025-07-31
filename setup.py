#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages

__version__ = '0.2.0'

def _read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


install_requires = ['beautifulsoup4', 'requests']


setup(name='recursive_crawler',
      version=__version__,
      description='Recursive crawler',
      long_description = _read('./README.md'),
      author='Artem Sharifulin',
      maintainer='Artem Sharifulin',
      author_email='artem@susi.ltd',
      url='https://github.com/suzzukin/recursive_crawler',
      install_requires=install_requires,
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'recursive-crawler=recursive_crawler.recursive_crawler:main',
          ],
      },
      platforms=['linux', 'darwin'],
      include_package_data=True,
      zip_safe=False,
      python_requires='>=3.9',
      )
