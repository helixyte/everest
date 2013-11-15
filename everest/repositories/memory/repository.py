"""
In-memory repository.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.entities.utils import new_entity_id
from everest.repositories.base import Repository
from everest.repositories.memory.aggregate import MemoryAggregate
from everest.repositories.memory.cache import EntityCacheMap
from everest.repositories.memory.session import MemorySessionFactory
from everest.repositories.state import ENTITY_STATUS
from threading import RLock

__docformat__ = 'reStructuredText en'
__all__ = ['MemoryRepository',
           ]


class MemoryRepository(Repository):
    """
    A repository that caches entities in memory.
    """
    _configurables = Repository._configurables \
                     + ['cache_loader']

    lock = RLock()

    def __init__(self, name, aggregate_class=None,
                 join_transaction=False, autocommit=False):
        if aggregate_class is None:
            aggregate_class = MemoryAggregate
        Repository.__init__(self, name, aggregate_class,
                            join_transaction=join_transaction,
                            autocommit=autocommit)
        self.__cache_map = EntityCacheMap()
        # By default, we do not use a cache loader.
        self.configure(cache_loader=None)

    def retrieve(self, entity_class, filter_expression=None,
                 order_expression=None, slice_key=None):
        cache = self.__get_cache(entity_class)
        return cache.retrieve(filter_expression=filter_expression,
                              order_expression=order_expression,
                              slice_key=slice_key)

    def flush(self, unit_of_work):
        for state in unit_of_work.iterator():
            if state.is_persisted:
                continue
            else:
                self.__persist(state)
                unit_of_work.mark_persisted(state.entity)

    def commit(self, unit_of_work):
        self.flush(unit_of_work)

    def rollback(self, unit_of_work):
        for state in unit_of_work.iterator():
            if state.is_persisted:
                self.__rollback(state)

    def __persist(self, state):
        source_entity = state.entity
        cache = self.__get_cache(type(source_entity))
        status = state.status
        if status == ENTITY_STATUS.NEW:
            # Autogenerate new ID.
            if source_entity.id is None:
                source_entity.id = new_entity_id()
            cache.add(source_entity)
        else:
            target_entity = cache.get_by_id(source_entity.id)
            if target_entity is None:
                raise ValueError('Could not persist data - target entity not '
                                 'found (ID used for lookup: %s).'
                                 % source_entity.id)
            if status == ENTITY_STATUS.DELETED:
                cache.remove(target_entity)
            elif status == ENTITY_STATUS.DIRTY:
                cache.update(state.data, target_entity)

    def __rollback(self, state):
        source_entity = state.entity
        cache = self.__get_cache(type(source_entity))
        if state.status == ENTITY_STATUS.DELETED:
            cache.add(source_entity)
        else:
            if state.status == ENTITY_STATUS.NEW:
                cache.remove(source_entity)
            elif state.status == ENTITY_STATUS.DIRTY:
                target_entity = cache.get_by_id(source_entity.id)
                cache.update(state.clean_data, target_entity)

    def _initialize(self):
        pass

    def _make_session_factory(self):
        return MemorySessionFactory(self)

    def __get_cache(self, entity_class):
        run_loader = not self.__cache_map.has_key(entity_class)
        cache = self.__cache_map[entity_class]
        if run_loader:
            # Check if we have an entity loader configured.
            loader = self.configuration['cache_loader']
            if not loader is None:
                for ent in loader(entity_class):
                    if ent.id is None:
                        ent.id = new_entity_id()
                    cache.add(ent)
        return cache
