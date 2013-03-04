"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 27, 2013.
"""
from everest.entities.utils import get_entity_class
from everest.repositories.memory.aggregate import MemoryAggregate
from everest.repositories.memory.cache import EntityCache
from everest.resources.utils import get_collection_class

__docformat__ = 'reStructuredText en'
__all__ = ['create_staging_collection',
           ]


class StagingSession(object):
    def __init__(self):
        self.__cache_map = {}

    def add(self, entity_class, entity):
        self.__cache_map[entity_class].add(entity)

    def remove(self, entity_class, entity):
        self.__cache_map[entity_class].remove(entity)

    def get_by_id(self, entity_class, entity_id):
        return self.__cache_map[entity_class].get_by_id(entity_id)

    def get_by_slug(self, entity_class, entity_slug):
        return self.__cache_map[entity_class].get_by_slug(entity_slug)

    def iterator(self, entity_class):
        return self.__cache_map[entity_class].iterator()

    def __getitem__(self, entity_class):
        cache = self.__cache_map.get(entity_class)
        if cache is None:
            cache = self.__cache_map[entity_class] = EntityCache()
        return cache


def create_staging_collection(resource):
    ent_cls = get_entity_class(resource)
    coll_cls = get_collection_class(resource)
    session = StagingSession()
    fac = lambda : session
    agg = MemoryAggregate.create(ent_cls, fac)
    return coll_cls.create_from_aggregate(agg)
