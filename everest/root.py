"""
Root factory.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 21, 2011.
"""
from everest.resources.utils import get_service

__docformat__ = 'reStructuredText en'
__all__ = ['RootFactory',
           ]


class RootFactory(object):
    """
    Factory for the object tree root (i.e., the service object).
    """
    def __init__(self):
        self.__root = None

    def __call__(self, request):
        if self.__root is None:
            # Start the service.
            self.__root = get_service()
            self.__root.start()
        return self.__root

