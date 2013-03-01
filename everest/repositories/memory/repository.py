"""
In-memory repository.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.repositories.base import Repository
from everest.repositories.memory.aggregate import MemoryAggregate
from everest.repositories.memory.cache import EntityCacheManager
from everest.repositories.memory.session import MemorySessionFactory
from everest.repositories.memory.uow import OBJECT_STATES
from threading import Lock
import uuid

__docformat__ = 'reStructuredText en'
__all__ = ['MemoryRepository',
           ]


class MemoryRepository(Repository):
    """
    A repository that caches entities in memory.
    """
    _configurables = Repository._configurables \
                     + ['cache_loader']

    lock = Lock()

    def __init__(self, name, aggregate_class=None,
                 autoflush=False, join_transaction=False, autocommit=False):
        if aggregate_class is None:
            aggregate_class = MemoryAggregate
        Repository.__init__(self, name, aggregate_class,
                            autoflush=autoflush,
                            join_transaction=join_transaction,
                            autocommit=autocommit)
        self.__cache_mgr = EntityCacheManager(self)
        # By default, we do not use a cache loader.
        self.configure(cache_loader=None)

    def new_id(self):
        """
        Generates a new (global) ID.
        
        Uses the :func:`uuid.uuid1` function to generate unique string IDs 
        which are sortable by creation time.
        
        :return: UUID string.
        """
        return str(uuid.uuid1())

    def get_by_id(self, entity_class, entity_id):
        cache = self.__cache_mgr[entity_class]
        return cache.get_by_id(entity_id)

    def get_by_slug(self, entity_class, entity_slug):
        cache = self.__cache_mgr[entity_class]
        return cache.get_by_slug(entity_slug)

    def iterator(self, entity_class):
        cache = self.__cache_mgr[entity_class]
        return cache.iterator()

    def commit(self, unit_of_work):
        # FIXME: There is no dependency tracking; objects are committed in
        #        random order.
        for ent_cls, ent, state in unit_of_work.iterator():
            cache = self.__cache_mgr[ent_cls]
            if state == OBJECT_STATES.DELETED:
                cache.remove(ent)
            else:
                if state == OBJECT_STATES.DIRTY:
                    cache.replace(ent)
                    unit_of_work.mark_clean(ent_cls, ent)
                elif state == OBJECT_STATES.NEW:
                    cache.add(ent)
                    unit_of_work.mark_clean(ent_cls, ent)

    def _initialize(self):
        pass

    def _make_session_factory(self):
        return MemorySessionFactory(self)

    def _get_cache(self, entity_class):
        return self.__cache_mgr[entity_class]
