"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.
"""

from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import clear_mappers
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import cast
from threading import Lock

__docformat__ = 'reStructuredText en'
__all__ = ['as_slug_expression',
           'commit_veto',
           'convert_slug_to_hybrid_property',
           'convert_to_hybrid_property',
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
Session = scoped_session(sessionmaker()) # extension=ZopeTransactionExtension()))


def commit_veto(environ, status, headers): # unused pylint: disable=W0613
    """
    Strict commit veto to use with the transaction manager.
    
    Unlike the default commit veto supplied with the transaction manager,
    this will veto all commits for HTTP status codes other than 2xx unless
    a commit is explicitly requested by setting the "x-tm" response header to
    "commit".
    """
    return not status.startswith('2') and not headers.get('x-tm') == 'commit'


def as_slug_expression(attr):
    """
    Converts the given instrumented string attribute into an SQL expression
    that can be used as a slug.

    Slugs are identifiers for members in a collection that can be used in an
    URL. We create slug columns by replacing non-URL characters with dashes
    and lower casing the result. We need this at the ORM level so that we can
    use the slug in a query expression.
    """
    slug_expr = func.replace(attr, ' ', '-')
    slug_expr = func.replace(slug_expr, '_', '-')
    slug_expr = func.lower(slug_expr)
    return slug_expr


def convert_slug_to_hybrid_property(ent_cls):
    """
    Helper function that converts the slug property of the given entity class
    to a hybrid property that also works in SQL expressions.
    """
    convert_to_hybrid_property(ent_cls, 'slug',
                               lambda cls: cast(cls.id, String))


def convert_to_hybrid_property(ent_cls, name, expression):
    """
    Helper function to convert plain slug properties to hybrid properties that
    also work in SQL expressions.
    """
    setattr(ent_cls, name, hybrid_property(getattr(ent_cls, name).fget,
                                           expr=expression))
