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
README = open(os.path.join(here, 'README.txt')).read()

setup_requirements = []

install_requirements = [
    'Paste',
    'PasteDeploy',
    'PasteScript',
    'WSGIFilter',
    'iso8601',
    'lxml>=2.3,<=2.3.99',
    'pyOpenSSL==0.10',
    'pyparsing>=1.5.5,<=1.5.99',
    'pyramid>=1.3b2,<=1.3.99',
    'pyramid_tm',
    'pyramid_zcml',
    'python-graph-core',
    'python-ldap>=2.3.11,<=2.3.99',
    'rfc3339',
    'sqlalchemy>=0.7.4,<=0.7.99',
    'transaction>=1.2.0,<=1.2.99',
    'zope.sqlalchemy>=0.4,<=0.4.99',
    ]

tests_requirements = install_requirements + [
    'coverage',
    'nose',
    'nosexcover',
    'webtest',
    ]

setup(name='everest',
      version='1.0b1',
      description='everest',
      long_description=README,
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Pyramid",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        ],
      author='F. Oliver Gathmann',
      author_email='gathmann@cenix.com',
      license="MIT",
      url='https://github.com/cenix/everest',
      keywords='web wsgi pyramid',
      packages=find_packages(),
      package_data={'': ["*.zcml", "*.xsd"]},
      include_package_data=True,
      zip_safe=False,
      setup_requires=setup_requirements,
      install_requires=install_requirements,
      tests_require=tests_requirements,
      test_suite="everest",
      entry_points="""\
      [nose.plugins.0.10]
      everest = everest.testing:EverestNosePlugin
      """
      )
