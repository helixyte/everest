"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Service class.

Created on Jul 27, 2011.
"""
from everest.repository import as_repository
from everest.resources.base import Resource
from everest.resources.interfaces import IService
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['Service',
           ]


class Service(Resource):
    """
    The service resource class.

    The service resource is placed at the root of the resource tree and 
    provides traversal (=URL) access to all exposed collection resources. 
    """
    implements(IService)

    relation = 'service'

    def __init__(self):
        Resource.__init__(self)
        # Setting the __name__ to None ensures a leading slash in model paths.
        self.__name__ = None
        # Collects all interfaces managed by the service.
        self.__registered_interfaces = set()
        # Maps collection names to resource interfaces.
        self.__collections = {}
        self.__started = False

    def register(self, irc):
        """
        Registers the given resource interface with this service.
        """
        if self.__started:
            raise RuntimeError("Can not register new resource interfaces when "
                               "the service has been started.")
        self.__registered_interfaces.add(irc)

    def start(self):
        """
        Starts the service.
        
        This adds all registered resource interfaces to the service. Multiple
        calls to this method will only perform the startup once.
        """
        if not self.__started:
            self.__started = True
            for irc in self.__registered_interfaces:
                self.add(irc)

    def __getitem__(self, key):
        """
        Overrides __getitem__ to return a clone of the requested collection.

        :param key: collection name.
        :type key: str
        :returns: object implementing
          :class:`everest.resources.interfaces.ICollectionResource`.
        """
        irc = self.__collections[key]
        repo = as_repository(irc)
        return repo.get(irc)

    def __len__(self):
        return len(self.__collections)

    def __iter__(self):
        for key in self.__collections.iterkeys():
            yield self.__getitem__(key)

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           'started' if self.__started else 'not started')

    def add(self, irc):
        repo = as_repository(irc)
        coll = repo.get(irc)
        if coll.__name__ in self.__collections:
            raise ValueError('Root collection for collection name %s '
                             ' already exists.' % coll.__name__)
        # We replace the repository collection with a clone that has the
        # service as the parent so that URL generation works.
        coll.__parent__ = self
        repo.set(irc, coll)
        # 
        self.__collections[coll.__name__] = irc

    def remove(self, irc):
        repo = as_repository(irc)
        coll = repo.get(irc)
        del self.__collections[coll.__name__]

    def get(self, name, default=None):
        try:
            coll = self.__getitem__(name)
        except KeyError:
            coll = default
        return coll
