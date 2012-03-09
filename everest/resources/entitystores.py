"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Entity stores and helper classes.

Created on Jan 31, 2012.
"""

from collections import defaultdict
from copy import deepcopy
from everest.db import Session as SaSessionFactory
from everest.db import get_engine
from everest.db import get_metadata
from everest.db import is_engine_initialized
from everest.db import is_metadata_initialized
from everest.db import set_engine
from everest.db import set_metadata
from everest.mime import CsvMime
from everest.resources.interfaces import IEntityStore
from everest.resources.io import dump_resource
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_repository_manager
from everest.utils import id_generator
from sqlalchemy.engine import create_engine
from threading import RLock
from threading import local
from transaction.interfaces import IDataManager
from weakref import WeakValueDictionary
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401
import os
import transaction
import weakref

__docformat__ = 'reStructuredText en'
__all__ = ['CachingEntityStore',
           'DataManager',
           'EntityStore',
           'FileSystemEntityStore',
           'OrmEntityStore',
           ]


class EntityStore(object):
    """
    Base class for all entity stores.
    
    An entity store is responsible for configuration and initialization of a
    storage backend for entities. It also creates and holds a session factory.
    """
    implements(IEntityStore)

    _configurables = None

    def __init__(self, name, join_transaction=False):
        self.__name = name
        #: Flag indicating that the sessions using this entity store should
        #: join the zope transaction.
        self._join_transaction = join_transaction
        self._config = {}
        self.__session_factory = None
        self.__is_initialized = False

    def configure(self, **config):
        for key, val in config.items():
            if not key in self._configurables:
                raise ValueError('Invalid configuration key "%s".' % key)
            self._config[key] = val

    def initialize(self):
        # Perform initialization specific to the derived class.
        self._initialize()
        #
        self.__is_initialized = True

    @property
    def session_factory(self):
        if self.__session_factory is None:
            # Create a session factory. The call to _initialize may depend on 
            # the session factory being instantiated.
            self.__session_factory = self._make_session_factory()
        return self.__session_factory

    @property
    def name(self):
        return self.__name

    @property
    def is_initialized(self):
        return self.__is_initialized

    def _initialize(self):
        """
        Performs initialization of the entity store.
        """
        raise NotImplementedError('Abstract method.')

    def _make_session_factory(self):
        """
        Create the session factory for this entity store.
        """
        raise NotImplementedError('Abstract method.')


class SessionFactory(object):
    def __init__(self, join_transaction):
        self._join_transaction = join_transaction

    def __call__(self):
        raise NotImplementedError('Abstract mehtod.')


class OrmSessionFactory(SessionFactory):
    def __call__(self):
        if self._join_transaction:
            # Enable the transaction extension.
            SaSessionFactory.configure(extension=ZopeTransactionExtension())
        return SaSessionFactory()


class OrmEntityStore(EntityStore):
    """
    EntityStore connected to an ORM backend.
    """
    _configurables = ['db_string', 'metadata_factory']

    def __init__(self, name, join_transaction=True):
        EntityStore.__init__(self, name, join_transaction=join_transaction)
        # Default to an in-memory sqlite DB.
        self.configure(db_string='sqlite://', metadata_factory=None)

    def _initialize(self):
        # Manages an ORM engine and a metadata instance for this entity store.
        # Both are global objects that should only be created once per process
        # (for each ORM entity store), hence we use a global object manager. 
        if not is_engine_initialized(self.name):
            db_string = self._config['db_string']
            engine = create_engine(db_string)
            # Bind the session factory to the engine.
            SaSessionFactory.configure(bind=engine)
            set_engine(self.name, engine)
        else:
            engine = get_engine(self.name)
        if not is_metadata_initialized(self.name):
            metadata_factory = self._config['metadata_factory']
            metadata = metadata_factory(engine)
            set_metadata(self.name, metadata)
        else:
            metadata = get_metadata(self.name)
            metadata.bind = engine

    def _make_session_factory(self):
        return OrmSessionFactory(self._join_transaction)

    @property
    def engine(self):
        return get_engine(self.name)

    @property
    def metadata(self):
        return get_metadata(self.name)


class InMemorySessionFactory(SessionFactory):
    """
    Factory for :class:`InMemorySession` instances.
    
    The factory creates exactly one session per thread.
    """
    def __init__(self, entity_store, autoflush=False, join_transaction=False):
        SessionFactory.__init__(self, join_transaction)
        self.__entity_store = entity_store
        self.__autoflush = autoflush
        self.__join_transaction = join_transaction
        self.__session_registry = local()

    def __call__(self):
        session = getattr(self.__session_registry, 'session', None)
        if session is None:
            session = InMemorySession(self.__entity_store,
                                      autoflush=self.__autoflush,
                                      join_transaction=self._join_transaction)
            self.__session_registry.session = session
        return session


class CachingEntityStore(EntityStore):
    """
    An entity store that caches all entities in memory.
    """
    _configurables = []

    def __init__(self, name, join_transaction=False):
        EntityStore.__init__(self, name, join_transaction=join_transaction)
        self._id_generators = defaultdict(id_generator)
        self.__entities = defaultdict(EntityCache)
        self.__cache_lock = RLock()

    def commit(self, session):
        with self.__cache_lock:
            for (entity_cls, added_entities) in session.added.iteritems():
                cache = self.__entities[entity_cls]
                for added_entity in added_entities:
                    cache.add(added_entity)
            for (entity_cls, removed_entities) in session.removed.iteritems():
                cache = self.__entities[entity_cls]
                for rmvd_entity in removed_entities:
                    cache.remove(rmvd_entity)
            for (entity_cls, dirty_entities) in session.dirty.iteritems():
                cache = self.__entities[entity_cls]
                for drt_entity in dirty_entities:
                    cache.replace(drt_entity)

    def rollback(self, session):
        # FIXME: Is there anything we should do here? pylint: disable=W0511
        pass

    def _initialize(self):
        pass

    def _make_session_factory(self):
        return InMemorySessionFactory(self,
                                      join_transaction=self._join_transaction)

    def _load(self):
        pass

    def copy(self):
        """
        Returns a deep copy of the entire entity cache.
        """
        return deepcopy(self.__entities)

    def get_by_id(self, entity_cls, entity_id):
        cache = self.__entities[entity_cls]
        return cache.get_by_id(entity_id)

    def get_by_slug(self, entity_cls, entity_slug):
        cache = self.__entities[entity_cls]
        return cache.get_by_slug(entity_slug)

    def get_all(self, entity_cls):
        cache = self.__entities[entity_cls]
        return cache.get_all()

    def get_id(self, entity_cls):
        id_gen = self._id_generators[entity_cls]
        return id_gen.next()


class FileSystemEntityStore(CachingEntityStore):
    """
    EntityStore using the file system as storage.
    
    On initialization, this entity store loads resource representations from
    files into the root repository. Each commit operation writes the specified
    resource back to file.
    """
    _configurables = ['directory', 'content_type']

    def __init__(self, name, join_transaction=True):
        CachingEntityStore.__init__(self, name,
                                    join_transaction=join_transaction)
        self.configure(directory=os.getcwd(), content_type=CsvMime)

    def commit(self, session):
        """
        Dump all resources that were modified by the given session back into
        the store.
        """
        CachingEntityStore.commit(self, session)
        repo = self.__get_repo()
        for entity_cls in session.dirty.keys():
            coll = repo.get(entity_cls)
            self.__dump_collection(coll)

    def _make_session_factory(self):
        return InMemorySessionFactory(self,
                                      autoflush=True,
                                      join_transaction=self._join_transaction)

    def _initialize(self):
        repo = self.__get_repo()
        for mb_cls in repo.managed_collections:
            coll_cls = get_collection_class(mb_cls)
            self.__load_collection(repo, coll_cls)

    def __dump_collection(self, collection):
        fn = self.__get_filename(collection, False)
        stream = file(fn, 'w')
        with stream:
            dump_resource(collection, stream,
                          content_type=self._config['content_type'])

    def __load_collection(self, repo, coll_cls):
        fn = self.__get_filename(coll_cls, True)
        if not fn is None:
            url = 'file://%s' % fn
            repo.load_representation(coll_cls, url,
                                     content_type=
                                            self._config['content_type'],
                                     resolve_urls=False)

    def __get_filename(self, collection_class, check_existing):
        directory = self._config['directory']
        ext = self._config['content_type'].file_extensions[0]
        collection_name = collection_class.relation.split('/')[-1]
        fn = os.path.join(directory, "%s%s" % (collection_name, ext))
        if check_existing and not os.path.isfile(fn):
            fn = None
        return fn

    def __get_repo(self):
        # FIXME: assuming repo has same name as store. pylint: disable=W0511
        repo_mgr = get_repository_manager()
        return repo_mgr.get(self.name)


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
        self.__needs_rebuild = False

    def clear(self):
        """
        Clears the cache.
        """
        self.__entities = []
        self.__id_map.clear()
        self.__slug_map.clear()

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
        Performs a lookup of an entity by its sluyg.
        
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
        # Perform checks first.
        ent_id = entity.id
        if not ent_id is None and ent_id in self.__id_map:
            raise ValueError('Duplicate entity ID "%s".' % ent_id)
        ent_slug = entity.slug
        if not ent_slug is None and ent_slug in self.__slug_map:
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
        if self.__needs_rebuild:
            self.__rebuild()
        self.__entities.remove(entity)
        if not entity.id is None:
            del self.__id_map[entity.id]
        if not entity.slug is None:
            del self.__slug_map[entity.slug]

    def __rebuild(self):
        self.__id_map.clear()
        self.__slug_map.clear()
        for entity in self.__entities:
            ent_id = entity.id
            if not ent_id is None:
                self.__id_map[ent_id] = entity
            ent_slug = entity.slug
            if not ent_slug is None:
                self.__slug_map[ent_slug] = entity
        self.__needs_rebuild = False


class InMemorySession(object):
    """
    Session that uses a map of :class:`EntityCache` instances to
    manage a "unit of work" on entities.
    
    Commit and rollback operations trigger the corresponding call on the
    underlying caching entity store.
    """
    def __init__(self, entity_store, autoflush=True, join_transaction=False):
        self.__entity_store = entity_store
        #: Flag controlling if a flush should be performed automatically
        #: at the time any of the get_* methods is executed.
        self.autoflush = autoflush
        #: Flag controlling if this session should join the zope transaction
        #: 
        self.join_transaction = join_transaction
        # Session state: modified entities (by entity class)
        self.__dirty = defaultdict(weakref.WeakSet)
        # Session state: added entities (by entity class)
        self.__added = defaultdict(weakref.WeakSet)
        # Session state: removed entities (by entity class)
        self.__removed = defaultdict(weakref.WeakSet)
        # Session state: entities in the session (net of add and remove ops).
        self.__entities = defaultdict(EntityCache)
        # Internal flag indicating that a flush is needed.
        self.__needs_flush = False
        # Internal flag indicating that the session needs to be synced with the
        # store.
        self.__needs_sync = True
        #
        self.__transaction = None

    def commit(self):
        # Always flush before a commit.
        self.flush()
        # Tell the entity store to do a commit.
        self.__entity_store.commit(self)
        # Reset state.
        self.reset()

    def rollback(self):
        # Tell the entity store to do a rollback.
        self.__entity_store.rollback(self)
        # Reset state.
        self.reset()

    def reset(self):
        self.__dirty.clear()
        self.__added.clear()
        self.__removed.clear()
        self.__entities.clear()
        #
        self.__needs_flush = False
        self.__needs_sync = True

    def add(self, entity_cls, entity):
        if self.__needs_sync:
            self.__sync_with_store()
        # Avoid conflicting operations.
        removed = self.__removed[entity_cls]
        if entity in removed:
            removed.remove(entity)
        else:
            added = self.__added[entity_cls]
            added.add(entity)
        # Update session cache.
        cache = self.__entities[entity_cls]
        cache.add(entity)
        # If the removed entity was marked as dirty, discard. 
        self.__dirty[entity_cls].discard(entity)
        # Mark for flush.
        self.__needs_flush = True

    def remove(self, entity_cls, entity):
        if self.__needs_sync:
            self.__sync_with_store()
        # Avoid conflicting operations.
        added = self.__added[entity_cls]
        if entity in added:
            added.remove(entity)
        else:
            removed = self.__removed[entity_cls]
            removed.add(entity)
        # Update session cache.
        self.__entities[entity_cls].remove(entity)

    def get_by_id(self, entity_cls, entity_id):
        if self.__needs_sync:
            self.__sync_with_store()
        if self.__needs_flush and self.autoflush:
            self.flush()
        entity = self.__entities[entity_cls].get_by_id(entity_id)
        if not entity is None:
            self.__dirty[entity_cls].add(entity)
        return entity

    def get_by_slug(self, entity_cls, entity_slug):
        if self.__needs_sync:
            self.__sync_with_store()
        if self.__needs_flush and self.autoflush:
            self.flush()
        entity = self.__entities[entity_cls].get_by_slug(entity_slug)
        if not entity is None:
            self.__dirty[entity_cls].add(entity)
        return entity

    def get_all(self, entity_cls):
        if self.__needs_sync:
            self.__sync_with_store()
        if self.__needs_flush and self.autoflush:
            self.flush()
        entities = self.__entities[entity_cls].get_all()
        self.__dirty[entity_cls].union(entities)
        return entities

    def flush(self):
        self.__needs_flush = False
        # Iterate over added entities and obtain new IDs from the store for 
        # entities that do not have one.
        rebuild_cache = False
        for (entity_cls, added_entities) in self.__added.iteritems():
            cache = self.__entities[entity_cls]
            for ad_ent in added_entities:
                if ad_ent.id is None:
                    new_id = self.__entity_store.get_id(entity_cls)
                    if not rebuild_cache:
                        rebuild_cache = True
                    ad_ent.id = new_id
        if rebuild_cache:
            for cache in self.__entities.itervalues():
                cache.rebuild()

    @property
    def is_dirty(self):
        return len(self.__dirty) > 0

    @property
    def added(self):
        return self.__added

    @property
    def removed(self):
        return self.__removed

    @property
    def dirty(self):
        return self.__dirty

    def __sync_with_store(self):
        if self.join_transaction:
            # If we have not already done so, create a data manager and join 
            # the zope transaction.
            trx = transaction.get()
            if not trx is self.__transaction:
                dm = DataManager(self)
                trx.join(dm)
                self.__transaction = trx
        self.__needs_sync = False
        self.__entities = self.__entity_store.copy()


class DataManager(object):
    """
    Data manager to plug an :class:`InMemorySession` into a zope transaction.
    """
    # TODO: implement safepoints. pylint: disable=W0511
    implements(IDataManager)

    def __init__(self, session):
        self.session = session

    def abort(self, trans): # pylint: disable=W0613
        self.session.rollback()

    def tpc_begin(self, trans): # pylint: disable=W0613
        self.session.flush()

    def commit(self, trans): # pylint: disable=W0613
        self.session.commit()

    def tpc_vote(self, trans): # pylint: disable=W0613
        self.session.commit()

    def tpc_finish(self, trans):
        pass

    def tpc_abort(self, trans): # pylint: disable=W0613
        self.session.rollback()

    def sortKey(self):
        return "everest:%d" % id(self.session)
