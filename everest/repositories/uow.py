"""
Unit of work.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 16, 2013.
"""
from collections import defaultdict
from everest.repositories.state import ENTITY_STATES
from everest.repositories.state import EntityStateManager
from weakref import WeakSet

__docformat__ = 'reStructuredText en'
__all__ = ['UnitOfWork',
           ]


class UnitOfWork(object):
    """
    The Unit Of Work records object state changes for subsequent commit
    to a repository.

    Responsibilities:
     * Clone CLEAN entities upon registration;
     * Record entity state changes.
    """
    def __init__(self):
        self.__entity_set_map = defaultdict(WeakSet)

    def register_new(self, entity_class, entity):
        """
        Registers the given entity for the given class as NEW.

        :raises ValueError: If the given entity already holds state that was
          created by another Unit Of Work.
        """
        EntityStateManager.manage(entity_class, entity, self)
        EntityStateManager.set_state(entity, ENTITY_STATES.NEW)
        self.__entity_set_map[entity_class].add(entity)

    def register_clean(self, entity_class, entity):
        """
        Registers the given entity for the given class as CLEAN.

        :returns: Cloned entity.
        """
        EntityStateManager.manage(entity_class, entity, self)
        EntityStateManager.set_state(entity, ENTITY_STATES.CLEAN)
        self.__entity_set_map[entity_class].add(entity)

    def register_deleted(self, entity_class, entity):
        """
        Registers the given entity for the given class as DELETED.

        :raises ValueError: If the given entity already holds state that was
          created by another Unit Of Work.
        """
        EntityStateManager.manage(entity_class, entity, self)
        EntityStateManager.set_state(entity, ENTITY_STATES.DELETED)
        self.__entity_set_map[entity_class].add(entity)

    def unregister(self, entity_class, entity):
        """
        Unregisters the given entity for the given class and discards its
        state information.
        """
        EntityStateManager.release(entity, self)
        self.__entity_set_map[entity_class].remove(entity)

    def is_registered(self, entity):
        return hasattr(entity, '__everest__') \
               and entity.__everest__.unit_of_work is self

    def is_marked_new(self, entity):
        try:
            result = EntityStateManager.get_state(entity) == ENTITY_STATES.NEW
        except ValueError:
            result = False
        return result

    def is_marked_deleted(self, entity):
        try:
            result = EntityStateManager.get_state(entity) \
                                                    == ENTITY_STATES.DELETED
        except ValueError:
            result = False
        return result

    def mark_new(self, entity):
        """
        Marks the given entity for the given class as NEW.

        This is done when an entity is re-associated with a session after
        having been removed before.
        """
        EntityStateManager.set_state(entity, ENTITY_STATES.NEW)

    def mark_clean(self, entity):
        """
        Marks the given entity for the given class as CLEAN.

        This is done when an entity is loaded fresh from the repository or
        after a commit.
        """
        EntityStateManager.set_state(entity, ENTITY_STATES.CLEAN)

    def mark_deleted(self, entity):
        """
        Marks the given entity for the given class as DELETED.

        :raises ValueError: If the given entity does not hold state.
        """
        EntityStateManager.set_state(entity, ENTITY_STATES.DELETED)

    def mark_dirty(self, entity):
        """
        Marks the given entity for the given class as DIRTY.

        :raises ValueError: If the given entity does not hold state.
        """
        EntityStateManager.set_state(entity, ENTITY_STATES.DIRTY)

    def get_clean(self, entity_class=None):
        """
        Returns an iterator over all CLEAN entities in this unit of work
        (optionally restricted to entities of the given class).
        """
        return self.__object_iterator(ENTITY_STATES.CLEAN, entity_class)

    def get_new(self, entity_class=None):
        """
        Returns an iterator over all NEW entities in this unit of work
        (optionally restricted to entities of the given class).
        """
        return self.__object_iterator(ENTITY_STATES.NEW, entity_class)

    def get_deleted(self, entity_class=None):
        """
        Returns an iterator over all DELETED entities in this unit of work
        (optionally restricted to entities of the given class).
        """
        return self.__object_iterator(ENTITY_STATES.DELETED, entity_class)

    def get_dirty(self, entity_class=None):
        """
        Returns an iterator over all DIRTY entities in this unit of work
        (optionally restricted to entities of the given class).
        """
        return self.__object_iterator(ENTITY_STATES.DIRTY, entity_class)

    def iterator(self):
        # FIXME: There is no dependency tracking; objects are iterated in
        #        random order.
        for ent_cls in self.__entity_set_map.keys():
            for ent in self.__entity_set_map[ent_cls]:
                yield ent_cls, ent, EntityStateManager.get_state(ent)

    def reset(self):
        for ents in self.__entity_set_map.values():
            for ent in ents:
                EntityStateManager.release(ent, self)
        self.__entity_set_map.clear()

    def __object_iterator(self, state, ent_cls):
        if ent_cls is None:
            ent_clss = self.__entity_set_map.keys()
        else:
            ent_clss = [ent_cls]
        for ent_cls in ent_clss:
            for ent in self.__entity_set_map[ent_cls]:
                if EntityStateManager.get_state(ent) == state:
                    yield ent
