"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Package setup file.

Created on Mar 6, 2012.
"""

from setuptools import setup
from setuptools import find_packages

setup(name='plantscribe',
      version='0.1',
      description='A faithful scribe for plant lists.',
      author='F. Oliver Gathmann',
      author_email='fogathmann at cenix.com',
      license="MIT",
      packages=find_packages(),
      package_data={'': ["*.zcml"]},
      include_package_data=True,
      zip_safe=False,
      install_requires=['distribute',
                        'everest'],
      dependency_links=['https://github.com/cenix/everest/tarball/master#egg=everest-dev',
                        ]
      )
