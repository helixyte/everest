"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The repose repository class.

Created on Jan 13, 2012.
"""

from everest.repository import Repository
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IResourceRepository
from everest.resources.utils import get_collection_class
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceRepository',
           ]


class ResourceRepository(Repository):
    """
    The resource repository manages resource accessors (collections).
    """
    implements(IResourceRepository)

    def __init__(self, entity_repository):
        Repository.__init__(self)
        self.__entity_repository = entity_repository

    def clear(self, rc):
        Repository.clear(self, rc)
        self.__entity_repository.clear(rc)

    def clear_all(self):
        Repository.clear_all(self)
        self.__entity_repository.clear_all()

    def _make_key(self, rc):
        return get_collection_class(rc)

    def _make_new(self, rc):
        agg = self.__entity_repository.get(rc)
        return get_adapter(agg, ICollectionResource)
