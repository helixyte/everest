"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Oct 11, 2011.
"""

from everest.resources.service import Service
from zope.component import createObject as create_object, IFactory # pylint: disable=E0611,F0401
from zope.interface import implementedBy as implemented_by, implements # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['RootBuilder',
           'ServiceFactory',
           ]


class RootBuilder(object):

    __root = None

    def __call__(self, environ):
        if self.__root is None:
            self.__root = self._build_root()
        return self.__root

    def _build_root(self):
        root = create_object('service')
        return root


class ServiceFactory(object):
    """
    """

    implements(IFactory)

    name = ''
    title = 'Service'
    description = 'Offered Services'

    def __call__(self):
        service = Service(self.name)
        service.title = self.title
        service.description = self.description
        return service

    def getInterfaces(self):
        return implemented_by(Service)
