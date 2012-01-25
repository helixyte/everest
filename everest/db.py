"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.
"""

from repoze.bfg.settings import get_settings
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import clear_mappers
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from threading import Lock
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['commit_veto',
           'get_engine',
           'get_metadata',
           'setup_db',
           'teardown_db',
           'Session',
           ]

#cache_opt = { # FIXME: move to config file # pylint: disable=W0511
#    'cache.regions': 'short_term',
#    'cache.short_term.expire': '3600',
#    }
#cache_manager = beaker_cache.CacheManager(**parse_cache_config_options(cache_opt))
#Session = scoped_session(
#    sessionmaker(query_cls=CachingQueryFactory(cache_manager),
#                 extension=ZopeTransactionExtension())
#    )

class _SingletonManager(object):
    _singleton = None
    __lock = Lock()

    @classmethod
    def set(cls, singleton):
        with _SingletonManager.__lock:
            if not cls._singleton is None:
                raise ValueError('Already initialized.')
            cls._singleton = singleton
        return cls._singleton

    @classmethod
    def get(cls):
        with _SingletonManager.__lock:
            return cls._singleton

    @classmethod
    def is_initialized(cls):
        with _SingletonManager.__lock:
            return not cls._singleton is None

    @classmethod
    def reset(cls):
        with _SingletonManager.__lock:
            cls._singleton = None


class _DbEngineManager(_SingletonManager):
    pass

get_engine = _DbEngineManager.get
_set_engine = _DbEngineManager.set
_is_engine_initialized = _DbEngineManager.is_initialized
_reset_engine = _DbEngineManager.reset


class _MetaDataManager(_SingletonManager):
    @classmethod
    def reset(cls):
        clear_mappers()
        super(_MetaDataManager, cls).reset()

get_metadata = _MetaDataManager.get
_set_metadata = _MetaDataManager.set
_is_metadata_initialized = _MetaDataManager.is_initialized
_reset_metadata = _MetaDataManager.reset


def setup_db(create_metadata_callback=None,
             reset_metadata=False, reset_engine=False):
    """
    Initialization function for the database (ORM).
    
    :param create_metadata_callback: if no metadata have been configured before
      or if a reset of the metadata is requested, this is called with no 
      arguments and is expected to return a metadata instance.
    :param bool reset_metadata: if set, previously configured metadata will be
      replaced.
    :param bool reset_engine: if set, a previously created DB engine will be
      replaced. 
    """
    if reset_metadata:
        if create_metadata_callback is None:
            raise ValueError('Need to provide a callback for creating the '
                             'ORM metadata when reset is requested.')
        _reset_metadata()
    if reset_engine:
        _reset_engine()
    if not _is_engine_initialized():
        db_string = get_settings().get('db_string')
        engine = create_engine(db_string)
        # Bind the session to the engine.
        Session.configure(bind=engine)
        _set_engine(engine)
    else:
        engine = get_engine()
    if not _is_metadata_initialized():
        # 
        metadata = create_metadata_callback()
        _set_metadata(metadata)
    else:
        metadata = get_metadata()
        metadata.bind = engine
    return engine, metadata


def teardown_db(reset_metadata=False, reset_engine=False):
    """
    Shutdown function for the DB (ORM).
    
    This is only needed in a testing context when tests need to create their
    own metadata and/or engine.

    :param bool reset_metadata: if set, previously configured metadata will be
      discarded. The next call to :func:`setup_db` will then always create new
      metadata.
    :param bool reset_engine: if set, a previously created DB engine will be
      discarded. The next call to :func:`setup_db` will then always create a
      new engine. 
    """
    if reset_metadata:
        _reset_metadata()
    if reset_engine:
        _reset_engine()


#: The scoped session maker. Instantiate this to obtain a thread local
#: session instance.
Session = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))


def commit_veto(environ, status, headers): # unused pylint: disable=W0613
    """
    Strict commit veto to use with the repoze.tm transaction manager.
    
    Unlike the default commit veto supplied with the transaction manager,
    this will veto all commits for HTTP status codes other than 2xx unless
    a commit is explicitly requested by setting the "x-tm" response header to
    "commit".
    """
    return not status.startswith('2') and not headers.get('x-tm') == 'commit'
