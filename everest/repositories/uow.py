"""
Unit of work.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 16, 2013.
"""
from collections import defaultdict
from everest.repositories.state import ENTITY_STATUS
from everest.repositories.state import EntityState
from everest.utils import WeakOrderedSet

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
        self.__entity_set_map = defaultdict(WeakOrderedSet)

    def register_new(self, entity_class, entity):
        """
        Registers the given entity for the given class as NEW.

        :raises ValueError: If the given entity already holds state that was
          created by another Unit Of Work.
        """
        EntityState.manage(entity, self)
        EntityState.get_state(entity).status = ENTITY_STATUS.NEW
        self.__entity_set_map[entity_class].add(entity)

    def register_clean(self, entity_class, entity):
        """
        Registers the given entity for the given class as CLEAN.

        :returns: Cloned entity.
        """
        EntityState.manage(entity, self)
        EntityState.get_state(entity).status = ENTITY_STATUS.CLEAN
        self.__entity_set_map[entity_class].add(entity)

    def register_deleted(self, entity_class, entity):
        """
        Registers the given entity for the given class as DELETED.

        :raises ValueError: If the given entity already holds state that was
          created by another Unit Of Work.
        """
        EntityState.manage(entity, self)
        EntityState.get_state(entity).status = ENTITY_STATUS.DELETED
        self.__entity_set_map[entity_class].add(entity)

    def unregister(self, entity_class, entity):
        """
        Unregisters the given entity for the given class and discards its
        state information.
        """
        EntityState.release(entity, self)
        self.__entity_set_map[entity_class].remove(entity)

    def is_registered(self, entity):
        """
        Checks if the given entity is registered with this Unit Of Work.
        """
        return hasattr(entity, '__everest__') \
               and entity.__everest__.unit_of_work is self

    def is_marked_new(self, entity):
        """
        Checks if the given entity is marked with status NEW. Returns `False`
        if the entity has no state information.
        """
        try:
            result = EntityState.get_state(entity).status == ENTITY_STATUS.NEW
        except ValueError:
            result = False
        return result

    def is_marked_deleted(self, entity):
        """
        Checks if the given entity is marked with status DELETED. Returns
        `False` if the entity has no state information.
        """
        try:
            result = EntityState.get_state(entity).status \
                                                    == ENTITY_STATUS.DELETED
        except ValueError:
            result = False
        return result

    def is_marked_persisted(self, entity):
        """
        Checks if the flag indicating that the state for the given entity
        has been persisted is `True`. Returns `False` if the entity has no
        state information.
        """
        try:
            result = EntityState.get_state(entity).is_persisted
        except ValueError:
            result = False
        return result

    def is_marked_pending(self, entity):
        """
        Checks if the flag indicating that the state for the given entity
        has been persisted is `False`. Returns `False` if the entity has no
        state information.
        """
        try:
            result = not EntityState.get_state(entity).is_persisted
        except ValueError:
            result = False
        return result

    def mark_new(self, entity):
        """
        Marks the given entity as NEW.

        This is done when an entity is re-associated with a session after
        having been removed before.
        """
        EntityState.get_state(entity).status = ENTITY_STATUS.NEW

    def mark_clean(self, entity):
        """
        Marks the given entity as CLEAN.

        This is done when an entity is loaded fresh from the repository or
        after a commit.
        """
        state = EntityState.get_state(entity)
        state.status = ENTITY_STATUS.CLEAN
        state.is_persisted = True

    def mark_deleted(self, entity):
        """
        Marks the given entity as DELETED.

        :raises ValueError: If the given entity does not hold state.
        """
        EntityState.get_state(entity).status = ENTITY_STATUS.DELETED

    def mark_dirty(self, entity):
        """
        Marks the given entity for the given class as DIRTY.

        :raises ValueError: If the given entity does not hold state.
        """
        EntityState.get_state(entity).status = ENTITY_STATUS.DIRTY

    def mark_persisted(self, entity):
        """
        Sets the flag indicating if the state of the given entity has been
        persisted to `True`.

        :note: The persistency flag is orthogonal to the status flag.
        """
        EntityState.get_state(entity).is_persisted = True

    def mark_pending(self, entity):
        """
        Sets the flag indicating if the state of the given entity has been
        persisted to `False`.

        :note: The persistency flag is orthogonal to the status flag.
        """
        EntityState.get_state(entity).is_persisted = False

    def get_clean(self, entity_class=None):
        """
        Returns an iterator over all CLEAN entities in this Unit Of Work
        (optionally restricted to entities of the given class).
        """
        return self.__object_iterator(ENTITY_STATUS.CLEAN, entity_class)

    def get_new(self, entity_class=None):
        """
        Returns an iterator over all NEW entities in this Unit Of Work
        (optionally restricted to entities of the given class).
        """
        return self.__object_iterator(ENTITY_STATUS.NEW, entity_class)

    def get_deleted(self, entity_class=None):
        """
        Returns an iterator over all DELETED entities in this Unit Of Work
        (optionally restricted to entities of the given class).
        """
        return self.__object_iterator(ENTITY_STATUS.DELETED, entity_class)

    def get_dirty(self, entity_class=None):
        """
        Returns an iterator over all DIRTY entities in this Unit Of Work
        (optionally restricted to entities of the given class).
        """
        return self.__object_iterator(ENTITY_STATUS.DIRTY, entity_class)

    def iterator(self):
        """
        Returns an iterator over all entity states held by this Unit Of Work.
        """
        # FIXME: There is no dependency tracking; objects are iterated in
        #        random order.
        for ent_cls in list(self.__entity_set_map.keys()):
            for ent in self.__entity_set_map[ent_cls]:
                yield EntityState.get_state(ent)

    def reset(self):
        """
        Releases all entities held by this Unit Of Work (i.e., removes state
        information from all registered entities and clears the entity map).
        """
        for ents in self.__entity_set_map.values():
            for ent in ents:
                EntityState.release(ent, self)
        self.__entity_set_map.clear()

    def __object_iterator(self, status, ent_cls):
        if ent_cls is None:
            ent_clss = self.__entity_set_map.keys()
        else:
            ent_clss = [ent_cls]
        for ent_cls in ent_clss:
            for ent in self.__entity_set_map[ent_cls]:
                if EntityState.get_state(ent).status == status:
                    yield ent
