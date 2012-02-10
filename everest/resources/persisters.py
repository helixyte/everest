"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Persisters and helper classes.

Created on Jan 31, 2012.
"""

from everest.db import Session as OrmSession
from everest.db import get_engine
from everest.db import get_metadata
from everest.db import is_engine_initialized
from everest.db import is_metadata_initialized
from everest.db import set_engine
from everest.db import set_metadata
from everest.interfaces import IRepository
from everest.mime import CsvMime
from everest.resources.interfaces import IPersister
from everest.resources.io import dump_resource
from everest.resources.utils import get_collection_class
from everest.utils import id_generator
from sqlalchemy.engine import create_engine
from transaction.interfaces import IDataManager
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import implements
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401
import os
import threading
import transaction
import weakref

__docformat__ = 'reStructuredText en'
__all__ = ['DataManager',
           'DummyPersister',
           'FileSystemPersister',
           'OrmPersister',
           'Persister',
           ]


class Persister(object):
    """
    Base class for all persisters.
    """
    implements(IPersister)

    _configurables = None

    def __init__(self, name):
        self.__name = name
        self._config = {}
        self.__session = None
        self.__is_initialized = False

    def configure(self, **config):
        for key, val in config.items():
            if not key in self._configurables:
                raise ValueError('Invalid configuration key "%s".' % key)
            self._config[key] = val

    def initialize(self):
        # Perform initialization specific to the derived class.
        self._initialize()
        # Create a session.
        self.__session = self._make_session()
        self.__is_initialized = True

    @property
    def session(self):
        return self.__session

    @property
    def name(self):
        return self.__name

    @property
    def is_initialized(self):
        return self.__is_initialized

    def _initialize(self):
        """
        Performs initialization of the persister.
        """
        raise NotImplementedError('Abstract method.')

    def _make_session(self):
        """
        Create the session for this persister.
        """
        raise NotImplementedError('Abstract method.')


class OrmPersister(Persister):
    _configurables = ['db_string', 'metadata_factory']

    def __init__(self, name):
        Persister.__init__(self, name)
        # Default to an in-memory sqlite DB.
        self.configure(db_string='sqlite://', metadata_factory=None)

    def _initialize(self):
        # Manages an ORM engine and a metadata instance for this persister.
        # Both are global objects that should only be created once per process
        # (for each ORM persister), hence we use a global object manager. 
        if not is_engine_initialized(self.name):
            db_string = self._config['db_string']
            engine = create_engine(db_string)
            # Bind the session to the engine.
            OrmSession.configure(bind=engine)
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

    def _make_session(self):
        # Enable the transaction extension.
        OrmSession.configure(extension=ZopeTransactionExtension())
        return OrmSession()

    @property
    def engine(self):
        return get_engine(self.name)

    @property
    def metadata(self):
        return get_metadata(self.name)


class InMemorySessionMixin(object):
    def _make_session(self):
        # Pass a weak reference to avoid circular references.
        session = InMemorySession(weakref.ref(self))
        # Create a data manager and join the zope transaction.
        dm = DataManager(session)
        transaction.get().join(dm)
        return session


class DummyPersister(InMemorySessionMixin, Persister):
    _configurables = []

    def _initialize(self):
        pass

    def commit(self, rc=None):
        pass


class FileSystemPersister(InMemorySessionMixin, Persister):
    """
    Persister using the file system as storage.
    
    On initialization, this persister loads resource representations from
    files into the root repository. Each commit operation writes the specified
    resource back to file.
    """
    _configurables = ['directory', 'content_type']

    def __init__(self, name):
        super(FileSystemPersister, self).__init__(name)
        self.configure(directory=os.getcwd(), content_type=CsvMime)

    def commit(self, rc=None):
        directory = self._config['directory']
        content_type = self._config['content_type']
        rc_repo = get_utility(IRepository, self.name)
        if rc is None:
            rcs = rc_repo.managed_collections
        else:
            rcs = [get_collection_class(rc)]
        for coll_cls in rcs:
            coll = rc_repo.get(coll_cls)
            fn = "%s%s" % (coll_cls.root_name, content_type.file_extensions[0])
            stream = file(os.path.join(directory, fn), 'w')
            with stream:
                dump_resource(coll, stream, content_type=content_type)

    def _initialize(self):
        directory = self._config['directory']
        content_type = self._config['content_type']
        fn_map = \
            dict([(os.path.splitext(fn)[0], fn)
                  for fn in os.listdir(directory)
                  if os.path.splitext(fn)[1] in content_type.file_extensions])
        rc_repo = get_utility(IRepository, self.name)
        for coll_cls in rc_repo.managed_collections:
            rc_fn = fn_map.get(coll_cls.root_name)
            if not rc_fn is None:
                rc_repo.load_representation(coll_cls, 'file://%s' % rc_fn,
                                            content_type=content_type)


class EntityCache(object):
    """
    Simple cache for entities.
    """
    def __init__(self):
        self.__slug_map = {}
        self.__id_map = {}
        self.__id_gen = id_generator()
        self.__last_id = self.__id_gen.next()

    def get_by_id(self, entity_id):
        return self.__id_map.get(entity_id)

    def get_by_slug(self, entity_slug):
        return self.__slug_map.get(entity_slug)

    def get_all(self):
        return self.__id_map.values()

    def add(self, entity):
        entity_id = entity.id
        entity_slug = entity.slug
        if entity_id in self.__id_map:
            raise ValueError('Duplicate ID "%s".' % entity_id)
        if entity_slug in self.__slug_map:
            raise ValueError('Duplicate slug "%s".' % entity_slug)
        if not entity_id is None:
            if entity_slug is None:
                raise ValueError('Entities added to a memory aggregate which '
                                 'specify an ID also need to specify a slug.')
            self.__id_map[entity_id] = entity
            self.__slug_map[entity_slug] = entity
            if entity_id > self.__last_id:
                self.__last_id = entity_id
                self.__id_gen.send(entity_id)

    def remove(self, entity):
        del self.__id_map[entity.id]
        del self.__slug_map[entity.slug]

    def flush(self, entity):
        if entity.id is None:
            entity.id = self.__last_id
            self.__last_id = self.__id_gen.next()
            self.add(entity)


class InMemorySession(object):
    """
    """
    def __init__(self, persister, autoflush=True):
        #: Flag controlling if a flush should be performed automatically
        #: at the time any of the get_* methods is executed.
        self.autoflush = autoflush
        self.__persister = persister
        self.__entities = {}
        self.__id_generators = {}
        self.__state = threading.local()
        self.__cache_lock = threading.Lock()
        self.__reset()
        self.__needs_flush = False

    def commit(self):
        if self.__needs_flush and self.autoflush:
            self.flush()
        for entity_cls in self.__state.dirty:
            self.__persister.commit(entity_cls)
        # Reset state.
        self.__reset()

    def rollback(self):
        # Update cache.
        with self.__cache_lock:
            for (added_cls, added_entity) in self.__state.added:
                self.__entities[added_cls].remove(added_entity)
            for (removed_cls, removed_entity) in self.__state.removed:
                self.__entities[removed_cls].append(removed_entity)
        # Reset state.
        self.__reset()

    def add(self, entity_cls, entity):
        # Update cache.
        cache = self.__get_cache(entity_cls)
        with self.__cache_lock:
            cache.add(entity)
        # Update state.
        self.__state.dirty.add(entity_cls)
        key = (entity_cls, entity)
        if key in self.__state.removed:
            self.__state.removed.remove(key)
        else:
            self.__state.added.add(key)
        self.__needs_flush = True

    def remove(self, entity_cls, entity):
        # Update cache.
        cache = self.__get_cache(entity_cls)
        with self.__cache_lock:
            cache.remove(entity)
        # Update state.
        self.__state.dirty.add(entity_cls)
        key = (entity_cls, entity)
        if key in self.__state.added:
            self.__state.added.remove(key)
        else:
            self.__state.removed.add(key)

    def get_by_id(self, entity_cls, entity_id):
        if self.__needs_flush and self.autoflush:
            self.flush()
        self.__state.dirty.add(entity_cls)
        cache = self.__get_cache(entity_cls)
        return cache.get_by_id(entity_id)

    def get_by_slug(self, entity_cls, entity_slug):
        if self.__needs_flush and self.autoflush:
            self.flush()
        self.__state.dirty.add(entity_cls)
        cache = self.__get_cache(entity_cls)
        return cache.get_by_slug(entity_slug)

    def get_all(self, entity_cls):
        if self.__needs_flush and self.autoflush:
            self.flush()
        self.__state.dirty.add(entity_cls)
        cache = self.__get_cache(entity_cls)
        return cache.get_all()

    def flush(self):
        for (entity_cls, entity) in self.__state.added:
            if entity.id is None:
                cache = self.__get_cache(entity_cls)
                with self.__cache_lock:
                    cache.flush(entity)
        self.__needs_flush = False

    @property
    def is_dirty(self):
        return len(self.__state.dirty) > 0

    def __get_cache(self, entity_cls):
        cache = self.__entities.get(entity_cls)
        if cache is None:
            cache = EntityCache()
            self.__entities[entity_cls] = cache
        return cache

    def __reset(self):
        self.__state.dirty = set()
        self.__state.added = set()
        self.__state.removed = set()


class DataManager(object):
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
