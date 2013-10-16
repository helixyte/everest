"""
In-memory repository.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.entities.utils import new_entity_id
from everest.repositories.base import Repository
from everest.repositories.memory.aggregate import MemoryAggregate
from everest.repositories.memory.cache import EntityCache
from everest.repositories.memory.session import MemorySessionFactory
from everest.repositories.state import ENTITY_STATES
from threading import Lock

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
                 join_transaction=False, autocommit=False):
        if aggregate_class is None:
            aggregate_class = MemoryAggregate
        Repository.__init__(self, name, aggregate_class,
                            join_transaction=join_transaction,
                            autocommit=autocommit)
        self.__entity_cache_map = {}
        # By default, we do not use a cache loader.
        self.configure(cache_loader=None)

    def retrieve(self, entity_class, filter_expression=None,
                 order_expression=None, slice_expression=None):
        cache = self.__get_cache(entity_class)
        return cache.retrieve(filter_expression=filter_expression,
                              order_expression=order_expression,
                              slice_expression=slice_expression)

    def commit(self, unit_of_work):
        for ent_cls, ent, state in unit_of_work.iterator():
            cache = self.__get_cache(ent_cls)
            if state == ENTITY_STATES.DELETED:
                cache.remove(ent)
            else:
                if state == ENTITY_STATES.DIRTY:
                    cache.replace(ent)
                elif state == ENTITY_STATES.NEW:
                    # Autogenerate new ID.
                    if ent.id is None:
                        ent.id = self.new_entity_id()
                    cache.add(ent)

    def new_entity_id(self):
        return new_entity_id()

    def _initialize(self):
        pass

    def _make_session_factory(self):
        return MemorySessionFactory(self)

    def __get_cache(self, entity_class):
        cache = self.__entity_cache_map.get(entity_class)
        if cache is None:
            cache = self.__entity_cache_map[entity_class] = EntityCache()
            # Check if we have an entity loader configured.
            loader = self.configuration['cache_loader']
            if not loader is None:
                for ent in loader(entity_class):
                    if ent.id is None:
                        ent.id = self.new_entity_id()
                    cache.add(ent)
        return cache

