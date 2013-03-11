"""
Staging collections.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 27, 2013.
"""
from collections import defaultdict
from everest.entities.utils import get_entity_class
from everest.repositories.memory.aggregate import MemoryAggregate
from everest.repositories.memory.cache import EntityCache
from everest.resources.utils import get_collection_class

__docformat__ = 'reStructuredText en'
__all__ = ['create_staging_collection',
           ]


class StagingSession(object):
    """
    Staging (transient) session.
    
    A staging session serves as a temporary container for entities. Unlike
    a "real" session, it does not maintain a unit of work and is not
    connected to a repository backend.
    """
    def __init__(self):
        self.__cache_map = \
                        defaultdict(lambda: EntityCache(allow_none_id=True))

    def add(self, entity_class, entity):
        self.__cache_map[entity_class].add(entity)

    def iterator(self, entity_class):
        return self.__cache_map[entity_class].iterator()


def create_staging_collection(resource):
    """
    Helper function to create a staging session for the given registered
    resource. 

    :param resource: registered resource
    :type resource: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    ent_cls = get_entity_class(resource)
    coll_cls = get_collection_class(resource)
    session = StagingSession()
    fac = lambda : session
    agg = MemoryAggregate.create(ent_cls, fac)
    return coll_cls.create_from_aggregate(agg)
