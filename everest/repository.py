"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The repository base class.

Created on Jan 17, 2012.
"""

from everest.interfaces import IRepository
from zope.interface import implements # pylint: disable=E0611,F0401
from weakref import WeakKeyDictionary

__docformat__ = 'reStructuredText en'
__all__ = ['Repository',
           ]


class REPOSITORY_DOMAINS(object):
    ROOT = 'ROOT'
    STAGE = 'STAGE'


class Repository(object):
    """
    Abstract base class for repositories.
    
    The repository creates accessors on the fly, caches them, and returns
    a clone.
    """
    implements(IRepository)

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

    def set(self, rc, obj):
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
        key = self._make_key(rc)
        self.__obj_cache.pop(key, None)

    def clear_all(self):
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
