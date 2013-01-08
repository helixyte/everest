"""
In-memory data store.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from copy import deepcopy
from everest.datastores.base import DataStore
from everest.datastores.memory.session import MemorySessionFactory
from everest.utils import id_generator
from threading import RLock
from weakref import WeakValueDictionary

__docformat__ = 'reStructuredText en'
__all__ = ['MemoryDataStore',
           ]


class EntityCache(object):
    """
    Cache for entities.
    
    Supports add, remove, and replace operations as well as lookup by ID and 
    by slug.
    """
    def __init__(self):
        # List of cached entities. This is the only place we are holding a
        # real reference to the entity.
        self.__entities = []
        # Dictionary mapping entity IDs to entities for fast lookup by ID.
        self.__id_map = WeakValueDictionary()
        # Dictionary mapping entity slugs to entities for fast lookup by slug.
        self.__slug_map = WeakValueDictionary()
        # Internal flag indicating that the cache has to be rebuilt (i.e.,
        # the id and slug maps have to be updated).
        self.__needs_rebuild = True

    def rebuild(self):
        """
        Rebuilds the cache (i.e., rebuilds the ID -> entity and slug -> 
        entity mappings).
        """
        if self.__needs_rebuild:
            self.__rebuild()

    def get_by_id(self, entity_id):
        """
        Performs a lookup of an entity by its ID.
        
        :param int entity_id: entity ID
        """
        if self.__needs_rebuild:
            self.__rebuild()
        return self.__id_map.get(entity_id)

    def get_by_slug(self, entity_slug):
        """
        Performs a lookup of an entity by its slug.
        
        :param str entity_id: entity slug
        """
        if self.__needs_rebuild:
            self.__rebuild()
        return self.__slug_map.get(entity_slug)

    def get_all(self):
        """
        Returns (a copy of) the list of all entities in this cache.
        """
        return self.__entities[:]

    def replace(self, entity):
        """
        Replaces the entity in the cache that has the same ID as the given
        entity with the latter.
        
        :param entity: entity to replace the cached entity with (must have
            a not-None ID).
        :type entity: object implementing :class:`everest.interfaces.IEntity`.
        """
        if self.__needs_rebuild:
            self.__rebuild()
        if entity.id is None:
            raise ValueError('Can only replace entities that have an ID.')
        old_entity = self.__id_map[entity.id]
        if entity.slug != old_entity.slug:
            del self.__slug_map[old_entity.slug]
#            if not entity.slug is None:
            self.__slug_map[entity.slug] = entity
        self.__entities.remove(old_entity)
        self.__entities.append(entity)
        self.__id_map[entity.id] = entity

    def add(self, entity):
        """
        Adds the given entity to this cache.
        
        At the point an entity is added, it must not have an ID or a slug
        of another entity that is already in the cache. However, both the ID
        and the slug may be *None* values.

        :param entity: entity to add.
        :type entity: object implementing :class:`everest.interfaces.IEntity`.
        """
        if self.__needs_rebuild:
            self.__rebuild()
        ent_id = entity.id
        if not ent_id is None:
            if ent_id in self.__id_map:
                raise ValueError('Duplicate entity ID "%s".' % ent_id)
        ent_slug = entity.slug
        if not ent_slug is None:
            if ent_slug in self.__slug_map:
                raise ValueError('Duplicate entity slug "%s".' % ent_slug)
        self.__entities.append(entity)
        # Sometimes, the slug is a lazy attribute; we *always* have to rebuild
        # when an entity was added.
        self.__needs_rebuild = True

    def remove(self, entity):
        """
        Removes the given entity to this cache.
        
        :param entity: entity to remove.
        :type entity: object implementing :class:`everest.interfaces.IEntity`.
        """
        self.__entities.remove(entity)
        self.__needs_rebuild = True

    def copy(self):
        """
        Returns a (deep) copy of this entity cache.
        
        :note: deep copying is necessary to ensure that changes on session
            entities do not propagate to the reference entities in the store.
        """
        new_cache = self.__class__()
        for ent in self.__entities:
            new_cache.add(deepcopy(ent))
        return new_cache

    def __rebuild(self):
        self.__id_map.clear()
        self.__slug_map.clear()
        rebuild_flag = False
        for entity in self.__entities:
            ent_id = entity.id
            if not ent_id is None:
                if ent_id in self.__id_map:
                    raise ValueError('Duplicate entity ID "%s".' % ent_id)
                self.__id_map[ent_id] = entity
            else:
                rebuild_flag = True
            ent_slug = entity.slug
            if not ent_slug is None:
                if ent_slug in self.__slug_map:
                    raise ValueError('Duplicate entity slug "%s".' % ent_slug)
                self.__slug_map[ent_slug] = entity
            else:
                rebuild_flag = True
        self.__needs_rebuild = rebuild_flag


# class EntityCacheMap(dict):
#    """
#    A map of entity caches.
#    """
#    def __init__(self, cache_loader=None):
#        dict.__init__(self)
#        self.__cache_loader = cache_loader
#
#    def __getitem__(self, entity_class):
#        cache = dict.get(self, entity_class)
#        if cache is None:
#            if self.__cache_loader is None:
#                ents = []
#            else:
#                ents = self.__cache_loader(entity_class)
#            cache = EntityCache()
#            for ent in ents:
#                cache.add(ent)
#            self.__setitem__(entity_class, cache)
#        return cache
#
#    def copy(self):
#        new_cache_map = self.__class__(self.__cache_loader)
#        for ent_cls, cache in self.iteritems():
#            new_cache_map[ent_cls] = cache.copy()
#        return new_cache_map


class MemoryDataStore(DataStore):
    """
    A data store that caches entities in memory.
    """
    _configurables = DataStore._configurables \
                     + ['cache_loader']

    def __init__(self, name,
                 autoflush=False, join_transaction=False, autocommit=False):
        DataStore.__init__(self, name, autoflush=autoflush,
                           join_transaction=join_transaction,
                           autocommit=autocommit)
        # A map of (global) ID generators.
        self.__id_generators = {}
        self.__next_id_map = {}
        # Maps entity classes to lists of entities.
        self.__entity_cache_map = {}
        # Lock for cache operations.
        self._cache_lock = RLock()
        # By default, we do not use a cache loader.
        self.configure(cache_loader=None)

    def lock(self):
        self._cache_lock.acquire()

    def unlock(self):
        self._cache_lock.release()

    def commit(self, session):
        """
        Perform a commit using the given session's state.
        """
        with self._cache_lock:
            for (entity_cls, added_entities) in session.added.iteritems():
                cache = self._get_cache(entity_cls)
                for added_entity in added_entities:
                    cache.add(added_entity)
            for (entity_cls, removed_entities) in session.removed.iteritems():
                cache = self._get_cache(entity_cls)
                for rmvd_entity in removed_entities:
                    cache.remove(rmvd_entity)
            for (entity_cls, dirty_entities) in session.dirty.iteritems():
                cache = self._get_cache(entity_cls)
                for drt_entity in dirty_entities:
                    cache.replace(drt_entity)

    def rollback(self, session):
        """
        Perform a rollback using the given session's state.
        """
        # FIXME: Is there anything we should do here? pylint: disable=W0511
        pass

    def get_copy(self, entity_class):
        """
        Returns a deep copy of the cache for the given entity class.
        
        :returns: :class:`everest.resources.entitystores.EntityCache`
        """
        with self._cache_lock:
            return self._get_cache(entity_class).copy()

    def new_id(self, entity_cls):
        """
        Generates a new (global) ID for the given entity class.
        """
        with self._cache_lock:
            id_gen = self.__get_id_generator(entity_cls)
            next_id = id_gen.next()
            self.__next_id_map[entity_cls] = next_id
            return next_id - 1

    def _initialize(self):
        self.__entity_cache_map = dict([(ent_cls, self._get_cache(ent_cls))
                                        for ent_cls in self.registered_types])

    def _make_session_factory(self):
        return MemorySessionFactory(self)

    def _get_cache(self, ent_cls):
        """
        Returns the entity cache for the given entity class. The cache will
        be initialized on the fly if necessary.
        
        :returns: :class:`everest.resources.entitystores.EntityCache` 
        """
        cache = self.__entity_cache_map.get(ent_cls)
        if cache is None:
            cache = self.__initialize_cache(ent_cls)
        return cache

    def __get_id_generator(self, ent_cls):
        id_gen = self.__id_generators.get(ent_cls)
        if id_gen is None:
            # Initialize the global ID generator for the given entity class.
            id_gen = self.__id_generators[ent_cls] = id_generator()
            self.__next_id_map[ent_cls] = id_gen.next()
        return id_gen

    def __initialize_cache(self, ent_cls):
        cache = self.__entity_cache_map[ent_cls] = EntityCache()
        cache_loader = self._config['cache_loader']
        if not cache_loader is None:
            max_id = -1
            for ent in cache_loader(ent_cls):
                if ent.id is None:
                    ent.id = self.new_id(ent_cls)
                elif isinstance(ent.id, int) and ent.id >= max_id:
                    # If the loaded entity already has an ID, record the
                    # highest ID so we can adjust the ID generator.
                    max_id = ent.id + 1
                cache.add(ent)
            if max_id != -1 and max_id > self.__next_id_map.get(ent_cls, 0):
                id_gen = self.__get_id_generator(ent_cls)
                id_gen.send(max_id)
        return cache
