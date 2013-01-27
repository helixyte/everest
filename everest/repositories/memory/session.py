"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from collections import defaultdict
from everest.repositories.base import SessionFactory
from threading import local
from transaction.interfaces import IDataManager
from weakref import WeakSet
from zope.interface import implements  # pylint: disable=E0611,F0401
import transaction

__docformat__ = 'reStructuredText en'
__all__ = ['MemorySession',
           'MemorySessionFactory',
           ]


class DataManager(object):
    """
    Data manager to plug an :class:`MemorySession` into a zope transaction.
    """
    # TODO: implement safepoints.
    implements(IDataManager)

    def __init__(self, session):
        self.session = session

    def abort(self, trans):  # pylint: disable=W0613
        self.session.rollback()

    def tpc_begin(self, trans):  # pylint: disable=W0613
        self.session.flush()

    def commit(self, trans):  # pylint: disable=W0613
        self.session.commit()

    def tpc_vote(self, trans):  # pylint: disable=W0613
        pass

    def tpc_finish(self, trans):
        pass

    def tpc_abort(self, trans):  # pylint: disable=W0613
        self.session.rollback()

    def sortKey(self):
        return "everest:%d" % id(self.session)


class MemorySession(object):
    """
    Session that uses a map of :class:`EntityCache` instances to
    manage a "unit of work" on entities.
    
    Commit and rollback operations trigger the corresponding call on the
    underlying caching entity store.
    """
    def __init__(self, entity_store):
        self.__entity_store = entity_store
        # Session state: (possibly) modified entities (by entity class)
        self.__dirty = defaultdict(WeakSet)
        # Session state: added entities (by entity class)
        self.__added = defaultdict(WeakSet)
        # Session state: removed entities (by entity class)
        self.__removed = defaultdict(WeakSet)
        # Session state: entities in the session (net of add and remove ops).
        # This is re-initialized when a sync with the store is performed.
        self.__entity_cache_map = {}
        # Internal flag indicating that a flush is needed.
        self.__needs_flush = False
        # Internal reference to the transaction (if joined).
        self.__transaction = None
        # Internal flag indicating if the store needs to be locked for
        # exclusive access.
        self.__store_needs_locking = True

    def commit(self):
        # Always flush before a commit.
        self.flush()
        # Tell the entity store to do a commit.
        self.__entity_store.commit(self)
        # Reset state.
        self.__reset()

    def rollback(self):
        # Tell the entity store to do a rollback.
        self.__entity_store.rollback(self)
        # Reset state.
        self.__reset()

    def add(self, entity_cls, entity):
        if self.__store_needs_locking:
            self.__lock_store()
        # Avoid conflicting operations.
        removed = self.__removed[entity_cls]
        if entity in removed:
            removed.remove(entity)
        else:
            added = self.__added[entity_cls]
            added.add(entity)
        # Update session cache.
        cache = self.__get_cache(entity_cls)
        cache.add(entity)
        # If the added entity was marked as dirty, discard.
        self.__dirty[entity_cls].discard(entity)
        # Mark for flush.
        self.__needs_flush = True
        if self.__entity_store.autocommit:
            # If we do not join the transaction, we commit immediately.
            self.commit()

    def remove(self, entity_cls, entity):
        if self.__store_needs_locking:
            self.__lock_store()
        # Avoid conflicting operations.
        added = self.__added[entity_cls]
        if entity in added:
            added.remove(entity)
        else:
            removed = self.__removed[entity_cls]
            removed.add(entity)
        # Update session cache.
        cache = self.__get_cache(entity_cls)
        cache.remove(entity)
        # If the removed entity was marked as dirty, discard.
        self.__dirty[entity_cls].discard(entity)
        if self.__entity_store.autocommit:
            # If we do not join the transaction, we commit immediately.
            self.commit()

    def get_by_id(self, entity_cls, entity_id):
        if self.__store_needs_locking:
            self.__lock_store()
        if self.__needs_flush and self.__entity_store.autoflush:
            self.flush()
        entity = self.__get_cache(entity_cls).get_by_id(entity_id)
        if not entity is None:
            self.__dirty[entity_cls].add(entity)
        return entity

    def get_by_slug(self, entity_cls, entity_slug):
        if self.__store_needs_locking:
            self.__lock_store()
        if self.__needs_flush and self.__entity_store.autoflush:
            self.flush()
        entity = self.__get_cache(entity_cls).get_by_slug(entity_slug)
        if not entity is None:
            self.__dirty[entity_cls].add(entity)
        return entity

    def get_all(self, entity_cls):
        if self.__store_needs_locking:
            self.__lock_store()
        if self.__needs_flush and self.__entity_store.autoflush:
            self.flush()
        entities = self.__get_cache(entity_cls).get_all()
        self.__dirty[entity_cls].update(entities)
        return entities

    def flush(self):
        self.__needs_flush = False
        # Iterate over added entities and obtain new IDs from the store for
        # entities that do not have one.
        caches_to_rebuild = set()
        for (entity_cls, added_entities) in self.__added.iteritems():
            cache = self.__get_cache(entity_cls)
            for ad_ent in added_entities:
                if ad_ent.id is None:
                    new_id = self.__entity_store.new_id(entity_cls)
                    if not cache in caches_to_rebuild:
                        caches_to_rebuild.add(cache)
                    ad_ent.id = new_id
        for cache_to_rebuild in caches_to_rebuild:
            cache_to_rebuild.rebuild()

    @property
    def added(self):
        return self.__added

    @property
    def removed(self):
        return self.__removed

    @property
    def dirty(self):
        return self.__dirty

    def __reset(self):
        self.__dirty.clear()
        self.__added.clear()
        self.__removed.clear()
        self.__needs_flush = False
        self.__entity_cache_map.clear()
        self.__unlock_store()

    def __lock_store(self):
        if self.__entity_store.join_transaction:
            # If we have not already done so, create a data manager and join
            # the zope transaction.
            trx = transaction.get()
            if not trx is self.__transaction:
                dm = DataManager(self)
                trx.join(dm)
            self.__transaction = trx
        self.__entity_store.lock()
        self.__store_needs_locking = False

    def __unlock_store(self):
        try:
            self.__entity_store.unlock()
        except RuntimeError:  # This happens e.g. on an explicit trx.abort()
            pass
        self.__store_needs_locking = True

    def __get_cache(self, ent_cls):
        cache = self.__entity_cache_map.get(ent_cls)
        if cache is None:
            cache = self.__entity_store.get_copy(ent_cls)
            self.__entity_cache_map[ent_cls] = cache
        return cache


class MemorySessionFactory(SessionFactory):
    """
    Factory for :class:`MemorySession` instances.
    
    The factory creates exactly one session per thread.
    """
    def __init__(self, entity_store):
        SessionFactory.__init__(self, entity_store)
        self.__session_registry = local()

    def __call__(self):
        session = getattr(self.__session_registry, 'session', None)
        if session is None:
            session = MemorySession(self._entity_store)
            self.__session_registry.session = session
        return session
