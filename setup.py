"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Package setup file.

Created on Nov 3, 2011.
"""
import os
from distribute_setup import use_setuptools
use_setuptools()
from setuptools import setup
from setuptools import find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

setup_requirements = []

install_requirements = \
    open(os.path.join(here, 'requirements.txt'), 'rU').readlines()

tests_requirements = install_requirements + [
    'pytest',
    'nose-cov',
    'pytz',
    'webtest',
    'mock'
    ]

setup(name='everest',
      version='1.0',
      description='everest',
      long_description=README,
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Pyramid",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        ],
      author='F. Oliver Gathmann',
      author_email='fogathmann at gmail.com',
      license="MIT",
      url='https://github.com/cenix/everest',
      keywords='REST web wsgi pyramid',
      packages=find_packages(),
      package_data={'': ["*.zcml", "*.xsd"]},
      include_package_data=True,
      zip_safe=False,
      setup_requires=setup_requirements,
      install_requires=install_requirements,
      tests_require=tests_requirements,
      test_suite="everest,doc",
      entry_points="""\
      [nose.plugins.0.10]
      everest = everest.ini:EverestNosePlugin
      [pytest11]
      everest = everest.tests.fixtures
      """
      )
