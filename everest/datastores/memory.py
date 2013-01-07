"""
In-memory data store.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from collections import defaultdict
from copy import deepcopy
from everest.datastores.base import DataStore
from everest.datastores.base import SessionFactory
from everest.entities.base import Aggregate
from everest.exceptions import DuplicateException
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.filtering import FilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.ordering import OrderSpecificationVisitor
from everest.utils import get_filter_specification_visitor
from everest.utils import get_order_specification_visitor
from everest.utils import id_generator
from functools import partial
from threading import RLock
from threading import local
from transaction.interfaces import IDataManager
from weakref import WeakSet
from weakref import WeakValueDictionary
from zope.interface import implements  # pylint: disable=E0611,F0401
import transaction

__docformat__ = 'reStructuredText en'
__all__ = ['InMemoryDataStore',
           'InMemorySessionFactory',
           'MemoryAggregate',
           'ObjectFilterSpecificationVisitor',
           'ObjectOrderSpecificationVisitor',
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


class DataManager(object):
    """
    Data manager to plug an :class:`InMemorySession` into a zope transaction.
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


class InMemorySession(object):
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


class InMemorySessionFactory(SessionFactory):
    """
    Factory for :class:`InMemorySession` instances.
    
    The factory creates exactly one session per thread.
    """
    def __init__(self, entity_store):
        SessionFactory.__init__(self, entity_store)
        self.__session_registry = local()

    def __call__(self):
        session = getattr(self.__session_registry, 'session', None)
        if session is None:
            session = InMemorySession(self._entity_store)
            self.__session_registry.session = session
        return session


class InMemoryDataStore(DataStore):
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
        return InMemorySessionFactory(self)

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


class MemoryAggregate(Aggregate):
    """
    Aggregate implementation for the in-memory data store. 

    :note: When "blank" entities without an ID and a slug are added to a
        memory aggregate, they can not be retrieved using the
        :meth:`get_by_id` or :meth:`get_by_slug` methods since there 
        is no mechanism to autogenerate IDs or slugs.
    """

    def count(self):
        return len(self.__get_entities())

    def get_by_id(self, id_key):
        if self._relationship is None or self._relationship.children is None:
            ent = self._session.get_by_id(self.entity_class, id_key)
            if not self._filter_spec is None \
               and not self._filter_spec.is_satisfied_by(ent):
                ent = None
        else:
            ent = self.__filter_by_attr(self._relationship.children,
                                        'id', id_key)
        return ent

    def get_by_slug(self, slug):
        if self._relationship is None or self._relationship.children is None:
            ent = self._session.get_by_slug(self.entity_class, slug)
            if not self._filter_spec is None \
               and not self._filter_spec.is_satisfied_by(ent):
                ent = None
        else:
            ent = self.__filter_by_attr(self._relationship.children,
                                        'slug', slug)
        return ent

    def iterator(self):
        for ent in self.__get_entities():
            yield ent

    def add(self, entity):
        if not isinstance(entity, self.entity_class):
            raise ValueError('Can only add entities of type "%s" to this '
                             'aggregate.' % self.entity_class)
        if self._relationship is None:
            self._session.add(self.entity_class, entity)
        else:
            if not entity.id is None \
               and self.__check_existing(self._relationship.children, entity):
                raise ValueError('Duplicate ID or slug.')
            self._relationship.children.append(entity)

    def remove(self, entity):
        if self._relationship is None:
            self._session.remove(self.entity_class, entity)
        else:
            self._relationship.children.remove(entity)

    def update(self, entity, source_entity):
        # FIXME: We need a proper __getstate__ method here.
        entity.__dict__.update(
                    dict([(k, v)
                          for (k, v) in source_entity.__dict__.iteritems()
                          if not k.startswith('_')]))

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass

    def __get_entities(self):
        if self._relationship is None:
            ents = self._session.get_all(self.entity_class)
        else:
            if self._relationship.children is None:
                ents = self._session.get_all(self.entity_class)
                visitor = \
                    get_filter_specification_visitor(EXPRESSION_KINDS.EVAL)()
                self._relationship.specification.accept(visitor)
                ents = visitor.expression(ents)
            else:
                ents = self._relationship.children
        if not self._filter_spec is None:
            visitor = get_filter_specification_visitor(EXPRESSION_KINDS.EVAL)()
            self._filter_spec.accept(visitor)
            ents = visitor.expression(ents)
        if not self._order_spec is None:
            visitor = get_order_specification_visitor(EXPRESSION_KINDS.EVAL)()
            self._order_spec.accept(visitor)
            ents = visitor.expression(ents)
        if not self._slice_key is None:
            ents = ents[self._slice_key]
        return ents

    def __check_existing(self, ents, entity):
        found = [ent for ent in ents
                 if ent.id == entity.id or ent.slug == entity.slug]
        return len(found) > 0

    def __filter_by_attr(self, ents, attr, value):
        if self._filter_spec is None:
            matching_ents = \
                [ent for ent in ents if getattr(ent, attr) == value]
        else:
            matching_ents = \
                [ent for ent in ents
                 if (getattr(ent, attr) == value
                     and self._filter_spec.is_satisfied_by(ent))]
        if len(matching_ents) == 1:
            ent = matching_ents[0]
        elif len(matching_ents) == 0:
            ent = None
        else:
            raise DuplicateException('Duplicates found for "%s" value of '  # pragma: no cover
                                     '"%s" attribue.' % (value, attr))
        return ent


class ObjectFilterSpecificationVisitor(FilterSpecificationVisitor):
    """
    Filter specification visitor building an evaluator for in-memory 
    filtering.
    """

    implements(IFilterSpecificationVisitor)

    @staticmethod
    def __evaluator(spec, entities):
        return [ent for ent in entities if spec.is_satisfied_by(ent)]

    def _conjunction_op(self, spec, *expressions):
        return partial(self.__evaluator, spec)

    def _disjunction_op(self, spec, *expressions):
        return partial(self.__evaluator, spec)

    def _negation_op(self, spec, expression):
        return partial(self.__evaluator, spec)

    def _starts_with_op(self, spec):
        return partial(self.__evaluator, spec)

    def _ends_with_op(self, spec):
        return partial(self.__evaluator, spec)

    def _contains_op(self, spec):
        return partial(self.__evaluator, spec)

    def _contained_op(self, spec):
        return partial(self.__evaluator, spec)

    def _equal_to_op(self, spec):
        return partial(self.__evaluator, spec)

    def _less_than_op(self, spec):
        return partial(self.__evaluator, spec)

    def _less_than_or_equal_to_op(self, spec):
        return partial(self.__evaluator, spec)

    def _greater_than_op(self, spec):
        return partial(self.__evaluator, spec)

    def _greater_than_or_equal_to_op(self, spec):
        return partial(self.__evaluator, spec)

    def _in_range_op(self, spec):
        return partial(self.__evaluator, spec)


class ObjectOrderSpecificationVisitor(OrderSpecificationVisitor):
    """
    Order specification visitor building an evaluator for in-memory 
    ordering.
    """

    implements(IOrderSpecificationVisitor)

    def _conjunction_op(self, spec, *expressions):
        return lambda entities: sorted(entities, cmp=spec.cmp)

    def _asc_op(self, spec):
        return lambda entities: sorted(entities, cmp=spec.cmp)

    def _desc_op(self, spec):
        return lambda entities: sorted(entities, cmp=spec.cmp)
