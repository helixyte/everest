"""
In-memory session.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from collections import MutableSequence
from collections import MutableSet
from everest.constants import RELATION_OPERATIONS
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.entities.traversal import AruVisitor
from everest.entities.utils import get_entity_class
from everest.repositories.base import AutocommittingSessionMixin
from everest.repositories.base import Session
from everest.repositories.base import SessionFactory
from everest.repositories.memory.cache import EntityCache
from everest.repositories.memory.querying import MemoryRepositoryQuery
from everest.repositories.state import EntityState
from everest.repositories.uow import UnitOfWork
from everest.traversal import SourceTargetDataTreeTraverser
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

    def __init__(self, repository, query_class=None, clone_on_load=True):
        self.__repository = repository
        self.__unit_of_work = UnitOfWork()
        self.__cache_map = {}
        if query_class is None:
            query_class = MemoryRepositoryQuery
        self.__query_class = query_class
        self.__clone_on_load = clone_on_load
        self.__needs_flushing = False
        self.__is_flushing = False

    def get_by_id(self, entity_class, entity_id):
        if self.__needs_flushing:
            self.flush()
        cache = self.__get_cache(entity_class)
        return cache.get_by_id(entity_id)

    def get_by_slug(self, entity_class, entity_slug):
        # When the entity is not found in the cache, it may have been added
        # with an undefined slug; we therefore attempt to look it up in the
        # list of pending NEW entities.
        if self.__needs_flushing:
            self.flush()
        cache = self.__get_cache(entity_class)
        ent = cache.get_by_slug(entity_slug)
#        if ent is None:
#            for new_ent in self.__unit_of_work.get_new(entity_class):
#                if new_ent.slug == entity_slug:
#                    ent = new_ent
#                    break
        return ent

    def add(self, entity_class, data):
        self.__traverse(entity_class, data, None, RELATION_OPERATIONS.ADD)

    def remove(self, entity_class, data):
        self.__traverse(entity_class, None, data, RELATION_OPERATIONS.REMOVE)

    def update(self, entity_class, data, target=None):
        return self.__traverse(entity_class, data, target,
                               RELATION_OPERATIONS.UPDATE)

    def query(self, entity_class):
        if self.__needs_flushing:
            self.flush()
        return self.__query_class(entity_class, self, self.__repository)

    def flush(self):
        if self.__needs_flushing and not self.__is_flushing:
            self.__is_flushing = True
            with self.__repository.lock:
                self.__repository.flush(self.__unit_of_work)
            self.__is_flushing = False
            for ent_cls in self.__cache_map.keys():
                # The flush may have auto-generated IDs for NEW entities,
                # so we rebuild the cache.
                cache = self.__get_cache(ent_cls)
                cache.rebuild(self.__unit_of_work.get_new(ent_cls))
        self.__needs_flushing = False

    def begin(self):
        self.__unit_of_work.reset()

    def commit(self):
        with self.__repository.lock:
            self.__repository.commit(self.__unit_of_work)
        self.__unit_of_work.reset()
        self.__cache_map.clear()

    def rollback(self):
        with self.__repository.lock:
            self.__repository.rollback(self.__unit_of_work)
        self.__unit_of_work.reset()
        self.__cache_map.clear()

    def reset(self):
        self.rollback()

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
        if self.__needs_flushing:
            self.flush()
        if entity.id is None:
            raise ValueError('Can not load entity without an ID.')
        cache = self.__get_cache(entity_class)
        sess_ent = cache.get_by_id(entity.id)
        if sess_ent is None:
            if self.__clone_on_load:
                sess_ent = self.__clone(entity, cache)
            else: # Only needed by the nosql backend pragma: no cover
                cache.add(entity)
                sess_ent = entity
            self.__unit_of_work.register_clean(entity_class, sess_ent)
        return sess_ent

    @property
    def new(self):
        return self.__unit_of_work.get_new()

    @property
    def deleted(self):
        return self.__unit_of_work.get_deleted()

    def __contains__(self, entity):
        cache = self.__cache_map.get(type(entity))
        if not cache is None:
            found = entity in cache
        else:
            found = False
        return found

    def __traverse(self, entity_class, source_data, target_data, rel_op):
        agg = self.__repository.get_aggregate(entity_class)
        trv = SourceTargetDataTreeTraverser.make_traverser(source_data,
                                                           target_data,
                                                           rel_op,
                                                           accessor=agg)
        vst = AruVisitor(entity_class,
                         self.__add, self.__remove, self.__update)
        trv.run(vst)
        # Indicate that we need to flush the changes.
        self.__needs_flushing = True
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
                if self.__unit_of_work.is_marked_pending(entity):
                    # The changes were not flushed yet; just mark as clean.
                    self.__unit_of_work.mark_clean(entity)
                else:
                    self.__unit_of_work.mark_new(entity)
                    self.__unit_of_work.mark_pending(entity)
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
            if self.__unit_of_work.is_marked_pending(entity):
                # The changes were not flushed yet; just mark as clean.
                self.__unit_of_work.mark_clean(entity)
            else:
                self.__unit_of_work.mark_deleted(entity)
                self.__unit_of_work.mark_pending(entity)
        cache = self.__get_cache(entity_class)
        if entity in cache:
            cache.remove(entity)

    def __update(self, entity_class, source_data, target_entity): # pylint: disable=W0613
        EntityState.set_state_data(target_entity, source_data)
        if self.__unit_of_work.is_marked_persisted(target_entity):
            self.__unit_of_work.mark_pending(target_entity)

    def __get_cache(self, entity_class):
        cache = self.__cache_map.get(entity_class)
        if cache is None:
            cache = self.__cache_map[entity_class] = EntityCache()
        return cache

    def __clone(self, entity, cache):
        clone = object.__new__(entity.__class__)
        # We add the clone with its ID set to the cache *before* we load it
        # so that circular references will work.
        clone.id = entity.id
        cache.add(clone)
        state = EntityState.get_state_data(entity)
        id_attr = None
        for attr, value in iteritems_(state):
            if attr.entity_attr == 'id':
                id_attr = attr
                continue
            attr_type = attr.attr_type
            if attr.kind != RESOURCE_ATTRIBUTE_KINDS.TERMINAL \
               and not self.__repository.is_registered_resource(attr_type):
                # Prevent loading of entities from other repositories.
                # FIXME: Doing this here is inconsistent, since e.g. the RDB
                #        session does not perform this kind of check.
                continue
            elif attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER \
               and not value is None:
                ent_cls = get_entity_class(attr_type)
                new_value = self.load(ent_cls, value)
                state[attr] = new_value
            elif attr.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION \
                 and len(value) > 0:
                value_type = type(value)
                new_value = value_type.__new__(value_type)
                if issubclass(value_type, MutableSequence):
                    add_op = new_value.append
                elif issubclass(value_type, MutableSet):
                    add_op = new_value.add
                else:
                    raise ValueError('Do not know how to clone value of type '
                                     '%s for resource attribute %s.'
                                     % (type(new_value), attr))
                ent_cls = get_entity_class(attr_type)
                for child in value:
                    child_clone = self.load(ent_cls, child)
                    add_op(child_clone)
                state[attr] = new_value
        # We set the ID already above.
        if not id_attr is None:
            del state[id_attr]
        EntityState.set_state_data(clone, state)
        return clone


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
    def __init__(self, repository, query_class=None, clone_on_load=True):
        SessionFactory.__init__(self, repository)
        sess_reg = local()
        self.__session_registry = sess_reg
        self.__query_class = query_class
        self.__clone_on_load = clone_on_load

    def __call__(self):
        session = getattr(self.__session_registry, 'session', None)
        if session is None:
            if not self._repository.autocommit:
                session = MemorySession(self._repository,
                                        query_class=self.__query_class,
                                        clone_on_load=self.__clone_on_load)
            else:
                session = MemoryAutocommittingSession(
                                        self._repository,
                                        query_class=self.__query_class,
                                        clone_on_load=self.__clone_on_load)
            self.__session_registry.session = session
            if self._repository.join_transaction is True:
                self.__session_registry.data_manager = DataManager(session)
        if self._repository.join_transaction is True:
            trx = transaction.get()
            dm = self.__session_registry.data_manager
            # We have a new transaction that we need to join.
            if not dm.transaction is trx:
                trx.join(dm)
                dm.transaction = trx
        return session


@implementer(IDataManager)
class DataManager(object):
    """
    Data manager to plug a :class:`MemorySession` into a Zope transaction.
    """
    # TODO: implement safepoints.

    def __init__(self, session):
        self.__session = session
        self.transaction = None

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
