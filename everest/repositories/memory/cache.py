"""
Entity cache and cache map.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 26, 2013.
"""
from collections import defaultdict
from everest.repositories.memory.querying import MemoryQuery
from everest.repositories.state import EntityStateManager
from itertools import islice
from weakref import WeakValueDictionary

__docformat__ = 'reStructuredText en'
__all__ = ['EntityCache',
           'EntityCacheMap',
           ]


class EntityCache(object):
    """
    Cache for entities.

    Supports add and remove operations as well as lookup by ID and
    by slug.
    """
    def __init__(self, entities=None, allow_none_id=True):
        """
        :param bool allow_none_id: Flag specifying if calling :meth:`add`
            with an entity that does not have an ID is allowed.
        """
        #
        self.__allow_none_id = allow_none_id
        # List of cached entities. This is the only place we are holding a
        # real reference to the entity.
        if entities is None:
            entities = []
        self.__entities = entities
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
        """
        Checks if this entity cache holds an entity with the given ID.

        :return: Boolean result of the check.
        """
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
        # For certain use cases (e.g., staging), we do not want the entity to
        # be added to have an ID yet.
        if not entity.id is None:
            if entity.id in self.__id_map:
                raise ValueError('Duplicate entity ID "%s".' % entity.id)
            self.__id_map[entity.id] = entity
        elif not self.__allow_none_id:
            raise ValueError('Entity ID must not be None.')
        # The slug can be a lazy attribute depending on the
        # value of other (possibly not yet initialized) attributes which is
        # why we can not always assume it is available at this point.
        if hasattr(entity, 'slug') and not entity.slug is None:
            if entity.slug in self.__slug_map:
                raise ValueError('Duplicate entity slug "%s".' % entity.slug)
            self.__slug_map[entity.slug] = entity
        self.__entities.append(entity)

    def remove(self, entity):
        """
        Removes the given entity from this cache.

        :param entity: Entity to remove.
        :type entity: Object implementing :class:`everest.interfaces.IEntity`.
        :raises KeyError: If the given entity is not in this cache.
        :raises ValueError: If the ID of the given entity is `None`.
        """
        self.__id_map.pop(entity.id, None)
        self.__slug_map.pop(entity.slug, None)
        self.__entities.remove(entity)

    def replace(self, entity):
        """
        Replaces the current entity that has the same ID as the given new
        entity with the latter.

        :param entity: Entity to replace.
        :type entity: Object implementing :class:`everest.interfaces.IEntity`.
        :raises KeyError: If the given entity is not in this cache.
        :raises ValueError: If the ID of the given entity is `None`.
        """
        if entity.id is None:
            raise ValueError('Entity ID must not be None.')
        old_entity = self.__id_map[entity.id]
        self.remove(old_entity)
        self.add(entity)

    def get_all(self):
        """
        Returns the list of all entities in this cache in the order they
        were added.
        """
        return self.__entities

    def retrieve(self, filter_expression=None,
                 order_expression=None, slice_expression=None):
        """
        Retrieve entities from this cache, possibly after filtering, ordering
        and slicing.
        """
        ents = iter(self.__entities)
        if not filter_expression is None:
            ents = filter_expression(ents)
        if not order_expression is None:
            # Ordering always involves a copy and conversion to a list, so
            # we have to wrap in an iterator.
            ents = iter(order_expression(ents))
        if not slice_expression is None:
            ents = islice(ents, slice_expression.start, slice_expression.stop)
        return ents

    def __contains__(self, entity):
        if not entity.id is None:
            is_contained = entity.id in self.__id_map
        else:
            is_contained = entity in self.__entities
        return is_contained


class EntityCacheMap(object):
    """
    Map for entity caches.
    """
    def __init__(self):
        self.__cache_map = defaultdict(EntityCache)

    def __getitem__(self, entity_class):
        return self.__cache_map[entity_class]

    def get_by_id(self, entity_class, entity_id):
        cache = self.__cache_map[entity_class]
        return cache.get_by_id(entity_id)

    def get_by_slug(self, entity_class, slug):
        cache = self.__cache_map[entity_class]
        return cache.get_by_slug(slug)

    def add(self, entity_class, entity):
        cache = self.__cache_map[entity_class]
        cache.add(entity)

    def remove(self, entity_class, entity):
        cache = self.__cache_map[entity_class]
        cache.remove(entity)

    def update(self, entity_class, source_data, target_entity):
        EntityStateManager.set_state_data(entity_class,
                                          source_data, target_entity)

    def query(self, entity_class):
        return MemoryQuery(entity_class,
                           self.__cache_map[entity_class].get_all())

    def __contains__(self, entity):
        cache = self.__cache_map[type(entity)]
        return entity in cache

    def keys(self):
        return self.__cache_map.keys()
