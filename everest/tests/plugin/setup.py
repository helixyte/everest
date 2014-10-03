"""

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 1, 2014.
"""

__docformat__ = 'reStructuredText en'
__all__ = []

from setuptools import setup
setup(name='everest_myplugin',
      version='0.1',
      install_requires='everest',
      entry_points="""
      [everest.plugins]
      everest_myplugin = everest_myplugin:load_plugin
      """
      )