"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 21, 2011.
"""

from everest.resources.interfaces import IService
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['RootFactory',
           ]


class RootFactory(object):
    def __init__(self):
        self.__root = None

    def __call__(self, request):
        if self.__root is None:
            self.__root = get_utility(IService)
            self.__root.start()
        return self.__root

