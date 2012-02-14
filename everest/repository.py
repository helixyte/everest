"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The repository base class.

Created on Jan 17, 2012.
"""

from everest.interfaces import IRepository
from weakref import WeakKeyDictionary
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['Repository',
           'as_repository',
           'get_repository',
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

    __repo_cache = None

    def __init__(self):
        # The accessor cache (keys are registered resource classes, values
        # are accessors).
        self.__obj_cache = {}

    def new(self, rc):
        """
        Returns a new accessor for the given registered resource.
        """
        raise NotImplementedError('Abstract method.')

    def configure(self, **config):
        """
        Configures this repository.
        """
        raise NotImplementedError('Abstract method.')

    def initialize(self):
        """
        Initializes this repository.
        """
        raise NotImplementedError('Abstract method.')

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
        self.__get_repo_cache()[obj_clone] = self
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

    @classmethod
    def get_repository(cls, obj):
        """
        Returns the repository instance that was used to obtain the given
        accessor object, or None if it was not created through a repository.
        """
        return cls.__get_repo_cache().get(obj)

    @classmethod
    def __get_repo_cache(cls):
        if cls.__repo_cache is None:
            cls.__repo_cache = WeakKeyDictionary()
        return cls.__repo_cache

    def _make_key(self, rc):
        raise NotImplementedError('Abstract method.')


def get_repository(name):
    """
    Get the resource repository registered under the given name.
    """
    return get_utility(IRepository, name)


def as_repository(rc):
    """
    Adapts the given registered resource to its configured repository.
    
    :return: object implementing 
      :class:`everest.resources.interfaces.IRepository`.
    """
    if IInterface in provided_by(rc):
        rc = get_utility(rc, name='collection-class')
    return get_adapter(rc, IRepository)
