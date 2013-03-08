"""
In-memory session.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from everest.entities.utils import new_entity_id
from everest.repositories.base import SessionFactory
from everest.repositories.memory.cache import EntityCacheManager
from everest.repositories.memory.uow import UnitOfWork
from threading import local
from transaction.interfaces import IDataManager
from zope.interface import implements # pylint: disable=E0611,F0401
import transaction

__docformat__ = 'reStructuredText en'
__all__ = ['MemorySession',
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
        self.__cache_mgr = EntityCacheManager(repository,
                                              self.__load_from_repository)
        self.__need_datamanager_setup = repository.join_transaction is True

    def commit(self):
        with self.__repository.lock:
            self.__repository.commit(self.__unit_of_work)
        self.__unit_of_work.reset()
        self.__cache_mgr.reset()

    def rollback(self):
#        for ent_cls, ent, state in self.__unit_of_work.iterator():
#            if state == OBJECT_STATES.DIRTY:
#                cache = self.__cache_mgr[ent_cls]
#                cache.replace(self.__repository.get_by_id(ent_cls, ent.id))
        self.__unit_of_work.reset()
        self.__cache_mgr.reset()

    def add(self, entity_class, entity):
        """
        Adds the given entity of the given entity class to the session.
        
        At the point an entity is added, it must not have an ID or a slug
        of another entity that is already in the session. However, both the ID
        and the slug may be ``None`` values.
        """
        cache = self.__cache_mgr[entity_class]
        if not entity.id is None and cache.has_id(entity.id):
            raise ValueError('Duplicate entity ID "%s".' % entity.id)
        if not entity.slug is None and cache.has_slug(entity.slug):
            raise ValueError('Duplicate entity slug "%s".' % entity.slug)
        if self.__need_datamanager_setup:
            self.__setup_datamanager()
        if entity.id is None:
            entity.id = new_entity_id()
        self.__unit_of_work.register_new(entity_class, entity)
        cache.add(entity)

    def remove(self, entity_class, entity):
        """
        Removes the given entity of the given entity class from the session.
        """
        if self.__need_datamanager_setup:
            self.__setup_datamanager()
        self.__unit_of_work.mark_deleted(entity_class, entity)
        cache = self.__cache_mgr[entity_class]
        cache.remove(entity)

    def replace(self, entity_class, entity):
        """
        Replaces the entity in the session with the same ID as the given 
        entity with the latter.
        
        :raises ValueError: If the session does not contain an entity with 
            the same ID as the ID of the given :param:`entity`.
        """
        if self.__need_datamanager_setup:
            self.__setup_datamanager()
        found_ent = self.get_by_id(entity_class, entity.id)
        if found_ent is None:
            raise ValueError('Entity with ID %s to replace not found.'
                             % entity.id)
        self.__unit_of_work.unregister(entity_class, found_ent)
        self.__unit_of_work.register_new(entity_class, entity)
        cache = self.__cache_mgr[entity_class]
        cache.replace(entity_class, entity)

    def get_by_id(self, entity_class, entity_id):
        """
        Retrieves the entity for the specified entity class and ID.
        """
        if self.__need_datamanager_setup:
            self.__setup_datamanager()
        return self.__cache_mgr[entity_class].get_by_id(entity_id)

    def get_by_slug(self, entity_class, entity_slug):
        """
        Retrieves the entity for the specified entity class and slug.
        
        When the entity is not found in the cache, it is looked up in the
        list of pending NEW entities.
        """
        if self.__need_datamanager_setup:
            self.__setup_datamanager()
        ent = self.__cache_mgr[entity_class].get_by_slug(entity_slug)
        if ent is None:
            for new_ent in self.__unit_of_work.get_new(entity_class):
                if new_ent.slug == entity_slug:
                    ent = new_ent
                    break
        return ent

    def iterator(self, entity_class):
        """
        Iterates over all entities of the given class in the repository,
        adding all entities that are not in the session.
        """
        if self.__need_datamanager_setup:
            self.__setup_datamanager()
        cache = self.__cache_mgr[entity_class]
        return cache.iterator()

    def get_all(self, entity_class):
        """
        Returns a list of all entities of the given class in the repository.
        """
        return list(self.iterator(entity_class))

    def __setup_datamanager(self):
        dm = DataManager(self)
        trx = transaction.get()
        trx.join(dm)
        self.__need_datamanager_setup = False

    def __load_from_repository(self, entity_class):
        ents = []
        for repo_ent in self.__repository.iterator(entity_class):
            ent = self.__unit_of_work.register_clean(entity_class,
                                                     repo_ent)
            ents.append(ent)
        return ents


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
            session = MemorySession(self._repository)
            self.__session_registry.session = session
        return session


class DataManager(object):
    """
    Data manager to plug a :class:`MemorySession` into a zope transaction.
    """
    # TODO: implement safepoints.
    implements(IDataManager)

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
