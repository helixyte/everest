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
__all__ = ['commit_veto',
           'get_engine',
           'get_metadata',
           'is_engine_initialized',
           'is_metadata_initialized',
           'reset_engines',
           'reset_metadata',
           'set_engine',
           'set_metadata',
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

class _GlobalObjectManager(object):
    _globs = None
    _lock = None

    @classmethod
    def set(cls, key, obj):
        """
        Sets the given object as global object for the given key.
        """
        with cls._lock:
            if not cls._globs.get(key) is None:
                raise ValueError('Duplicate key "%s".' % key)
            cls._globs[key] = obj
        return cls._globs[key]

    @classmethod
    def get(cls, key):
        """
        Returns the global object for the given key.
        
        :raises KeyError: if no global object was initialized for the given 
          key.
        """
        with cls._lock:
            return cls._globs[key]

    @classmethod
    def is_initialized(cls, key):
        """
        Checks if a global object with the given key has been initialized.
        """
        with cls._lock:
            return not cls._globs.get(key) is None

    @classmethod
    def reset(cls):
        """
        Discards all global objects held by this manager.
        """
        with cls._lock:
            cls._globs.clear()


class _DbEngineManager(_GlobalObjectManager):
    _globs = {}
    _lock = Lock()

get_engine = _DbEngineManager.get
set_engine = _DbEngineManager.set
is_engine_initialized = _DbEngineManager.is_initialized
reset_engines = _DbEngineManager.reset


class _MetaDataManager(_GlobalObjectManager):
    _globs = {}
    _lock = Lock()

    @classmethod
    def reset(cls):
        clear_mappers()
        super(_MetaDataManager, cls).reset()

get_metadata = _MetaDataManager.get
set_metadata = _MetaDataManager.set
is_metadata_initialized = _MetaDataManager.is_initialized
reset_metadata = _MetaDataManager.reset


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
