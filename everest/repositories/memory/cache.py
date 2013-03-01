"""
Entity cache and manager.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 26, 2013.
"""
from weakref import WeakValueDictionary

__docformat__ = 'reStructuredText en'
__all__ = ['EntityCache',
           'EntityCacheManager',
           ]


class EntityCache(object):
    """
    Cache for entities.
    
    Supports add and remove operations as well as lookup by ID and 
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

    def get_by_id(self, entity_id):
        """
        Performs a lookup of an entity by its ID.
        
        :param int entity_id: entity ID.
        :return: entity found or ``None``.
        """
        return self.__id_map.get(entity_id)

    def has_id(self, entity_id):
        return entity_id in self.__id_map

    def get_by_slug(self, entity_slug):
        """
        Performs a lookup of an entity by its slug.
        
        :param str entity_id: entity slug.
        :return: entity found or ``None``.
        """
        return self.__slug_map.get(entity_slug)

    def has_slug(self, entity_slug):
        return entity_slug in self.__slug_map

    def add(self, entity):
        """
        Adds the given entity to this cache.
        
        :param entity: Entity to add.
        :type entity: Object implementing :class:`everest.interfaces.IEntity`.
        :raises ValueError: If the ID of the entity to add is ``None``.
        """
        if entity.id is None:
            raise ValueError('Entity ID must not be None.')
        self.__id_map[entity.id] = entity
        # Unlike the ID, the slug can be a lazy attribute depending on the
        # value of other (possibly not yet initialized) attributes which is
        # why we can not always assume it is available at this point.
        if not entity.slug is None:
            self.__slug_map[entity.slug] = entity
        self.__entities.append(entity)

    def remove(self, entity):
        """
        Removes the given entity from this cache.
        
        :param entity: Entity to remove.
        :type entity: Object implementing :class:`everest.interfaces.IEntity`.
        :raises KeyError: If the given entity is not in this cache.
        """
        del self.__id_map[entity.id]
        # We may not have the slug in the slug map because it might not have
        # been available by the time the entity was added.
        self.__slug_map.pop(entity.slug, None)
        self.__entities.remove(entity)

    def replace(self, entity):
        """
        Replaces the current entity that has the same ID as the given new
        entity with the latter.
        
        :param entity: Entity to replace.
        :type entity: Object implementing :class:`everest.interfaces.IEntity`.
        """
        old_entity = self.__id_map[entity.id]
        self.remove(old_entity)
        self.add(entity)

    def iterator(self):
        """
        Returns an iterator over all entities in this cache in the order they
        were added.
        """
        return iter(self.__entities)


class EntityCacheManager(object):
    """
    Manager for entity caches.
    """
    def __init__(self, repository, loader=None):
        self.__repository = repository
        self.__loader = loader
        self.__cache_map = {}

    def __getitem__(self, entity_class):
        cache = self.__cache_map.get(entity_class)
        if cache is None:
            cache = self._initialize_cache(entity_class)
        return cache

    def _initialize_cache(self, ent_cls):
        cache = self.__cache_map[ent_cls] = EntityCache()
        # If we did not receive a cache loader at initialization, we use the
        # one the repository provides as a default.
        loader = \
            self.__loader or self.__repository.configuration['cache_loader']
        if not loader is None:
            for ent in loader(ent_cls):
                if ent.id is None:
                    ent.id = self.__repository.new_id()
                cache.add(ent)
        return cache
