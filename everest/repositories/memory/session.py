"""
In-memory session.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from everest.constants import RELATION_OPERATIONS
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.entities.traversal import AruVisitor
from everest.entities.utils import get_entity_class
from everest.repositories.base import AutocommittingSessionMixin
from everest.repositories.base import Session
from everest.repositories.base import SessionFactory
from everest.repositories.memory.cache import EntityCache
from everest.repositories.memory.querying import MemorySessionQuery
from everest.repositories.state import EntityStateManager
from everest.repositories.uow import UnitOfWork
from everest.traversers import SourceTargetDataTreeTraverser
from pyramid.compat import iteritems_
from threading import local
from transaction.interfaces import IDataManager
from zope.interface import implementer # pylint: disable=E0611,F0401
import transaction

__docformat__ = 'reStructuredText en'
__all__ = ['DataManager',
           'MemoryAutocommittingSession',
           'MemorySession',
           'MemorySessionFactory',
           ]


class MemorySession(Session):
    """
    Session object.

    The session
     * Holds a Unit Of Work;
     * Serves as identity and slug map;
     * Performs synchronized commit on repository;
     * Sets up data manager to hook into transaction.
    """
    IS_MANAGING_BACKREFERENCES = True

    def __init__(self, repository):
        self.__repository = repository
        self.__unit_of_work = UnitOfWork()
        self.__cache_map = {}

    def get_by_id(self, entity_class, entity_id):
        """
        Retrieves the entity for the specified entity class and ID.
        """
        cache = self.__get_cache(entity_class)
        return cache.get_by_id(entity_id)

    def add(self, entity_class, data):
        """
        Adds the given entity of the given entity class to the session.

        At the point an entity is added, it must not have an ID or a slug
        of another entity that is already in the session. However, both the ID
        and the slug may be ``None`` values.
        """
        self.__traverse(entity_class, data, RELATION_OPERATIONS.ADD)

    def remove(self, entity_class, data):
        """
        Removes the given entity of the given entity class from the session.

        :raises ValueError: If the entity to remove does not have an ID
            (unless it is marked NEW).
        """
        self.__traverse(entity_class, data, RELATION_OPERATIONS.REMOVE)

    def update(self, entity_class, data):
        """
        Updates the existing entity with the same ID as the given entity
        with the state of the latter.

        :raises ValueError: If the session does not contain an entity with
            the same ID as the ID of the given :param:`entity`.
        """
        return self.__traverse(entity_class, data, RELATION_OPERATIONS.UPDATE)

    def query(self, entity_class):
        return MemorySessionQuery(entity_class, self, self.__repository)

    def begin(self):
        self.__unit_of_work.reset()

    def commit(self):
        with self.__repository.lock:
            self.__repository.commit(self.__unit_of_work)
        self.__unit_of_work.reset()
        self.__cache_map.clear()

    def rollback(self):
        self.__unit_of_work.reset()
        self.__cache_map.clear()

    def load(self, entity_class, entity):
        """
        Load the given repository entity into the session and return a
        clone. If it was already loaded before, look up the loaded entity
        and return it.

        All entities referenced by the loaded entity will also be loaded
        (and cloned) recursively.

        :raises ValueError: When an attempt is made to load an entity that
          has no ID
        """
        if entity in self.__unit_of_work.get_new(entity_class):
            # NEW entities may not have an ID, so we have to treat this case
            # separately.
            ent = entity
        else:
            if entity.id is None:
                raise ValueError('Can not load entity without an ID.')
            cache = self.__get_cache(entity_class)
            ent = cache.get_by_id(entity.id)
            if ent is None:
                ent = self.__clone(entity_class, entity, cache)
                self.__unit_of_work.register_clean(entity_class, ent)
        return ent

    def __clone(self, entity_class, entity, cache):
        clone = object.__new__(entity.__class__)
        # We add the clone to the cache *before* we load it so that
        # circular references will work. We need to set the ID
        clone.id = entity.id
        cache.add(clone)
        state = EntityStateManager.get_state_data(entity_class, entity)
        id_attr = None
        for attr, value in iteritems_(state):
            if attr.entity_attr == 'id':
                id_attr = attr
            elif attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER \
               and not value is None:
                ent_cls = get_entity_class(attr.attr_type)
                new_value = self.load(ent_cls, value)
                state[attr] = new_value
            elif attr.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION \
                 and len(value) > 0:
                # FIXME: Assuming list-like here.
                if isinstance(value, list):
                    new_value = []
                    add_op = new_value.append
                elif isinstance(value, set):
                    new_value = set()
                    add_op = new_value.add
                else:
                    raise ValueError('Do not know how to clone value of type '
                                     '%s for resource attribute %s.'
                                     % (type(new_value), attr))
                ent_cls = get_entity_class(attr.attr_type)
                for child in value:
                    child_clone = self.load(ent_cls, child)
                    add_op(child_clone)
                state[attr] = new_value
        # We set the ID already above.
        if not id_attr is None:
            del state[id_attr]
        EntityStateManager.set_state_data(entity_class, clone, state)
        return clone

    def get_by_slug(self, entity_class, entity_slug):
        """
        Retrieves the entity for the specified entity class and slug.

        When the entity is not found in the cache, it may have been added
        with an undefined slug and is looked up in the list of pending NEW
        entities.
        """
        cache = self.__get_cache(entity_class)
        ent = cache.get_by_slug(entity_slug)
        if ent is None:
            for new_ent in self.__unit_of_work.get_new(entity_class):
                if new_ent.slug == entity_slug:
                    ent = new_ent
                    break
        return ent

    @property
    def new(self):
        return self.__unit_of_work.get_new()

    @property
    def deleted(self):
        return self.__unit_of_work.get_deleted()

    def __traverse(self, entity_class, data, rel_op):
        agg = self.__repository.get_aggregate(entity_class)
        trv = SourceTargetDataTreeTraverser.make_traverser(data, rel_op, agg)
        vst = AruVisitor(entity_class,
                         self.__add, self.__remove, self.__update)
        trv.run(vst)
        return vst.root

    def __add(self, entity_class, entity):
        cache = self.__get_cache(entity_class)
        # We allow adding the same entity multiple times.
        if not (not entity.id is None
                and cache.get_by_id(entity.id) is entity):
            if not self.__unit_of_work.is_marked_deleted(entity):
                self.__unit_of_work.register_new(entity_class, entity)
                if not entity.id is None and cache.has_id(entity.id):
                    raise ValueError('Duplicate entity ID "%s".' % entity.id)
                if not entity.slug is None and cache.has_slug(entity.slug):
                    raise ValueError('Duplicate entity slug "%s".'
                                     % entity.slug)
            else:
                self.__unit_of_work.mark_clean(entity)
            cache.add(entity)

    def __remove(self, entity_class, entity):
        if not self.__unit_of_work.is_registered(entity):
            if entity.id is None:
                raise ValueError('Can not remove un-registered entity '
                                 'without an ID')
            self.__unit_of_work.register_deleted(entity_class, entity)
        elif not self.__unit_of_work.is_marked_new(entity):
            self.__unit_of_work.mark_deleted(entity)
        else:
            self.__unit_of_work.mark_clean(entity)
        cache = self.__get_cache(entity_class)
        if entity in cache:
            cache.remove(entity)

    def __update(self, entity_class, target_entity, source_data):
        EntityStateManager.set_state_data(entity_class,
                                          target_entity, source_data)

    def __contains__(self, entity):
        cache = self.__cache_map.get(type(entity))
        if not cache is None:
            found = entity in cache
        else:
            found = False
        return found

    def __get_cache(self, entity_class):
        cache = self.__cache_map.get(entity_class)
        if cache is None:
            cache = self.__cache_map[entity_class] = EntityCache()
        return cache


class MemoryAutocommittingSession(AutocommittingSessionMixin, MemorySession):
    """
    Autocommitting session in memory.
    """
    pass


class MemorySessionFactory(SessionFactory):
    """
    Factory for :class:`MemorySession` instances.

    The factory creates exactly one session per thread.
    """
    def __init__(self, repository):
        SessionFactory.__init__(self, repository)
        self.__session_registry = local()

    def __call__(self):
        session = getattr(self.__session_registry, 'session', None)
        if session is None:
            if not self._repository.autocommit:
                session = MemorySession(self._repository)
            else:
                session = MemoryAutocommittingSession(self._repository)
            if self._repository.join_transaction is True:
                dm = DataManager(session)
                trx = transaction.get()
                trx.join(dm)
            self.__session_registry.session = session
        return session


@implementer(IDataManager)
class DataManager(object):
    """
    Data manager to plug a :class:`MemorySession` into a Zope transaction.
    """
    # TODO: implement safepoints.

    def __init__(self, session):
        self.__session = session

    def abort(self, trans): # pylint: disable=W0613
        self.__session.rollback()

    def tpc_begin(self, trans): # pylint: disable=W0613
        pass

    def commit(self, trans): # pylint: disable=W0613
        self.__session.commit()

    def tpc_vote(self, trans): # pylint: disable=W0613
        pass

    def tpc_finish(self, trans):
        pass

    def tpc_abort(self, trans): # pylint: disable=W0613
        self.__session.rollback()

    def sortKey(self):
        return "everest:%d" % id(self.__session)
