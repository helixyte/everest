"""
In-memory session.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from everest.entities.traversal import CrudVisitor
from everest.entities.traversal import SourceTargetDomainTraverser
from everest.exceptions import NoResultsException
from everest.repositories.base import AutocommittingSessionMixin
from everest.repositories.base import SessionFactory
from everest.repositories.memory.cache import EntityCache
from everest.repositories.memory.querying import MemorySessionQuery
from everest.repositories.state import EntityStateManager
from everest.repositories.uow import UnitOfWork
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


class MemorySession(object):
    """
    Session object.

    The session
     * Holds a Unit Of Work;
     * Serves as identity and slug map;
     * Performs synchronized commit on repository;
     * Sets up data manager to hook into transaction.
    """
    def __init__(self, repository):
        self.__repository = repository
        self.__unit_of_work = UnitOfWork()
        self.__cache_map = {}

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
                ent = self.__unit_of_work.register_clean(entity_class, entity)
                cache.add(ent)
        return ent

    def add(self, entity_class, entity):
        """
        Adds the given entity of the given entity class to the session.

        At the point an entity is added, it must not have an ID or a slug
        of another entity that is already in the session. However, both the ID
        and the slug may be ``None`` values.
        """
        self.__run_crud_operation(entity_class, entity, None)

    def remove(self, entity_class, entity):
        """
        Removes the given entity of the given entity class from the session.

        :raises ValueError: If the entity to remove does not have an ID
            (unless it is marked NEW).
        """
        self.__run_crud_operation(entity_class, None, entity)

    def update(self, entity_class, entity):
        """
        Updates the existing entity with the same ID as the given entity
        with the state of the latter.

        :raises ValueError: If the session does not contain an entity with
            the same ID as the ID of the given :param:`entity`.
        """
        target_entity = self.get_by_id(entity_class, entity)
        if target_entity is None:
            # Not loaded into the session; try reloading from repository.
            try:
                target_entity = \
                    self.query(entity_class).filter_by(id=entity.id).one()
            except NoResultsException:
                pass
            if target_entity is None:
                raise ValueError('Entity with ID %s to update not found.'
                                 % entity.id)
        self.__run_crud_operation(entity_class, entity, target_entity)

    def get_by_id(self, entity_class, entity_id):
        """
        Retrieves the entity for the specified entity class and ID.
        """
        cache = self.__get_cache(entity_class)
        return cache.get_by_id(entity_id)

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

    def query(self, entity_class):
        return MemorySessionQuery(entity_class, self, self.__repository)

    def __run_crud_operation(self, entity_class, source_entity, target_entity):
        trv = SourceTargetDomainTraverser(self, source_entity, target_entity)
        vst = CrudVisitor(entity_class,
                          self.__create,
                          self.__remove_single,
                          self.__update_single)
        trv.run(vst)

    def __create(self, entity_class, entity_data):
        entity = entity_class.create_from_data(entity_data)
        cache = self.__get_cache(entity_class)
        if not self.__unit_of_work.is_marked_deleted(entity):
            self.__unit_of_work.register_new(entity_class, entity)
            if not entity.id is None and cache.has_id(entity.id):
                raise ValueError('Duplicate entity ID "%s".' % entity.id)
            if not entity.slug is None and cache.has_slug(entity.slug):
                raise ValueError('Duplicate entity slug "%s".' % entity.slug)
        else:
            self.__unit_of_work.mark_clean(entity)
        cache.add(entity)

    def __remove_single(self, entity_class, entity):
        if not self.__unit_of_work.is_registered(entity):
            if entity.id is None:
                raise ValueError('Can not remove un-registered entity '
                                 'without an ID')
            else:
                self.__unit_of_work.register_deleted(entity_class, entity)
        else:
            if not self.__unit_of_work.is_marked_new(entity):
                self.__unit_of_work.mark_deleted(entity)
            else:
                self.__unit_of_work.mark_clean(entity)
            cache = self.__get_cache(entity_class)
            cache.remove(entity)

    def __update_single(self, entity_class, source_entity, target_entity):
        EntityStateManager.transfer_state_data(entity_class,
                                               source_entity, target_entity)
        return source_entity

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
