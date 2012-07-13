"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The repository base class.

Created on Jan 17, 2012.
"""
from everest.interfaces import IRepository
from pyramid.threadlocal import get_current_registry
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['REPOSITORIES',
           'Repository',
           'as_repository',
           ]


class REPOSITORIES(object):
    MEMORY = 'MEMORY'
    ORM = 'ORM'
    FILE_SYSTEM = 'FILE_SYSTEM'


class Repository(object):
    """
    Abstract base class for repositories.
    
    The repository creates accessors on the fly, caches them, and returns
    a clone.
    """
    implements(IRepository)

    is_initialized = None

    def __init__(self):
        # The accessor cache (keys are registered resource classes, values
        # are accessors).
        self.__obj_cache = {}
        self.__is_initializing = False

    def new(self, rc):
        """
        Returns a new accessor for the given registered resource.
        """
        if not (self.is_initialized or self.__is_initializing):
            raise RuntimeError('Repository has not been initialized yet.')
        return self._new(rc)

    def configure(self, **config):
        """
        Configures this repository.
        """
        raise NotImplementedError('Abstract method.')

    def initialize(self):
        """
        Initializes this repository.
        """
        self.__is_initializing = True
        self._initialize()
        self.__is_initializing = False

    def set(self, rc, obj):
        """
        Makes the given accessor the one to use for the given registered
        resource.
        """
        key = self._make_key(rc)
        self.__obj_cache[key] = obj

    def get(self, rc):
        """
        Returns an accessor for the given registered resource. 
        
        If this is the first request, an instance is created on the fly using 
        the :meth:`new` method and cached. The method always returns a clone
        of the cached accessor; this clone can later be used to look up
        the repository it was obtained from using the :meth:`get_repository`
        class method.
        """
        key = self._make_key(rc)
        obj = self.__obj_cache.get(key)
        if obj is None:
            obj = self.new(rc)
            self.__obj_cache[key] = obj
        obj_clone = obj.clone()
        obj_clone.__repository__ = self
        return obj_clone

    def clear(self, rc):
        """
        Clears the accessor for the given registered resource.
        """
        key = self._make_key(rc)
        self.__obj_cache.pop(key, None)

    def clear_all(self):
        """
        Clears all accessors.
        """
        self.__obj_cache.clear()

    def _initialize(self):
        """
        Implements initialization of this repository.
        """
        raise NotImplementedError('Abstract method.')

    def _new(self, rc):
        """
        Implements creation of a new accessor for the given resource.
        """
        raise NotImplementedError('Abstract method.')

    def _make_key(self, rc):
        raise NotImplementedError('Abstract method.')


def as_repository(rc):
    """
    Adapts the given registered resource to its configured repository.
    
    :return: object implementing 
      :class:`everest.resources.interfaces.IRepository`.
    """
    reg = get_current_registry()
    if IInterface in provided_by(rc):
        rc = reg.getUtility(rc, name='collection-class')
    return reg.getAdapter(rc, IRepository)
