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
    'repoze.bfg>=1.3,<=1.3.99',
    'repoze.tm2>=1.0a5,<=1.0.99',
    'sqlalchemy>=0.7.2,<=0.7.99',
    'zope.sqlalchemy>=0.4,<=0.4.99',
    'z3c.batching>=1.1.0,<=1.1.99',
    'transaction>=1.0.0,<=1.0.99',
    'odict>=1.2.6,<=1.2.99',
    'pyparsing>=1.5.5,<=1.5.99',
    'repoze.who>=2.0a2,<=2.0.99',
    'python-ldap>=2.3.11,<=2.3.99',
    'Paste>=1.7.3,<=1.7.99',
    'gunicorn',
    'pyOpenSSL==0.10',
    'eventlet',
    'greenlet',
    'PasteDeploy',
    'PasteScript',
    'rfc3339',
    'lxml>=2.3,<=2.3.99',
    'WSGIFilter',
    'iso8601',
    'WebOb>=1.2b1'
    ]

tests_requirements = install_requirements + [
    'nose>=1.1.0,<=1.1.99',
    'nosexcover>=1.0.4,<=1.0.99',
    'coverage==3.4',
    'webtest>=1.3.1,<=1.3.99',
    'pytz',
    ]

setup(name='everest',
      version='0.1',
      description='everest',
      long_description=README,
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: BFG",
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
      keywords='web wsgi pyramids',
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
      everest = everest.testing:EverestTestAppNosePlugin
      """
      )
