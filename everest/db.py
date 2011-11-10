"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.
"""

from sqlalchemy.orm import clear_mappers
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from threading import Lock
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['initialize_db',
           'get_db_engine',
           'get_metadata',
           'initialize_db_engine',
           'initialize_metadata',
           'is_db_engine_initialized',
           'Session',
           'metadata']

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

set_db_engine = _DbEngineManager.set
get_db_engine = _DbEngineManager.get
is_db_engine_initialized = _DbEngineManager.is_initialized
reset_db_engine = _DbEngineManager.reset

class _MetaDataManager(_SingletonManager):
    @classmethod
    def reset(cls):
        clear_mappers()
        super(_MetaDataManager, cls).reset()

set_metadata = _MetaDataManager.set
is_metadata_initialized = _MetaDataManager.is_initialized
get_metadata = _MetaDataManager.get
reset_metadata = _MetaDataManager.reset

#: The scoped session maker. Instantiate this to obtain a thread local
#: session instance.
Session = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
