"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.
"""

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401
import logging
import transaction
from sqlalchemy.orm import clear_mappers


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


class _DbEngineManager(object):
    __engine = None

    @classmethod
    def initialize(cls, db_string):
        cls.__engine = create_engine(db_string)
        return cls.__engine

    @classmethod
    def get(cls):
        return cls.__engine

    @classmethod
    def is_initialized(cls):
        return not cls.__engine is None

    @classmethod
    def reset(cls):
        cls.__engine = None

initialize_db_engine = _DbEngineManager.initialize
get_db_engine = _DbEngineManager.get
is_db_engine_initialized = _DbEngineManager.is_initialized
reset_db_engine = _DbEngineManager.reset

#: The scoped session maker. Instantiate this to obtain a thread local
#: session instance.
Session = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))


def create_session():
    return Session()


class _MetaDataManager(object):
    __metadata = None

    @classmethod
    def initialize(cls):
#        cls.__metadata = initialize_schema()
#        initialize_mappers(cls.__metadata.tables, cls.__metadata.views) # pylint: disable=E1101
        return cls.__metadata

    @classmethod
    def get(cls):
        if cls.__metadata is None:
            cls.initialize()
        return cls.__metadata

    @classmethod
    def reset(cls):
        clear_mappers()
        cls.__metadata = None

initialize_metadata = _MetaDataManager.initialize
get_metadata = _MetaDataManager.get
reset_metadata = _MetaDataManager.reset


def initialize_db(db_string, echo=False, create_schema=False, data=None):
    """
    Convenience function allowing the web application to initialize the
    metadata and DB engien in one call. Also loads and commits all data
    that are passed with the :param:`data` parameter.
    """
    metadata = get_metadata()
    engine = initialize_db_engine(db_string)
    engine.echo = echo
    Session.configure(bind=engine)
    if create_schema:
        metadata.create_all(engine)
    if not data is None:
        try:
            session = Session()
            session.add_all(data)
            transaction.commit()
        except IntegrityError, err:
            logger = logging.getLogger('sqlalchemy.engine')
            logger.error("Transaction aborted due to an integrity error")
            transaction.abort()
            raise err
    return engine
