"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

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
    """
    implements(IRepository)

    __repo_cache = None

    def __init__(self):
        # The accessor cache (keys are registered resource classes, values
        # are accessors).
        self.__obj_cache = {}

    def set(self, rc, obj):
        key = self._make_key(rc)
        self.__obj_cache[key] = obj

    def get(self, rc):
        key = self._make_key(rc)
        obj = self.__obj_cache.get(key)
        if obj is None:
            obj = self._make_new(rc)
            self.__obj_cache[key] = obj
        obj_clone = obj.clone()
        self.__get_repo_cache()[obj_clone] = self
        return obj_clone

    def clear(self, rc):
        key = self._make_key(rc)
        self.__obj_cache.pop(key, None)

    def clear_all(self):
        self.__obj_cache.clear()

    def load_representation(self, rc, url):
#        key = self._make_key(rc)
        pass

    @classmethod
    def get_repository(cls, obj):
        """
        Returns the repository instance that was used to create the given
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

    def _make_new(self, rc):
        raise NotImplementedError('Abstract method.')
