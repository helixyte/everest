"""
Data store for the NoSQL backend.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 11, 2013.
"""
from everest.repositories.base import Repository
from everest.repositories.nosqldb.aggregate import NoSqlAggregate
from everest.repositories.utils import is_engine_initialized
from everest.repositories.utils import set_engine
from pymongo.mongo_client import MongoClient

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlRepository',
           ]


class NoSqlRepository(Repository):
    """
    Data store connected to a NoSQL backend.
    """
    def __init__(self, name, aggregate_class=None,
                 autoflush=True, join_transaction=True, autocommit=False):
        if aggregate_class is None:
            aggregate_class = NoSqlAggregate
        Repository.__init__(self, name, aggregate_class,
                            autoflush=autoflush,
                            join_transaction=join_transaction,
                            autocommit=autocommit)
        self.__db = None

    def _initialize(self):
        if not is_engine_initialized(self.name):
            engine = self.__make_engine()
            set_engine(self.name, engine)
        db_name = self._config['db_name']
        self.__db = getattr(engine, db_name)

    def _make_session_factory(self):
        Repository._make_session_factory(self)

    def __make_engine(self):
        db_host = self._config['db_host']
        db_port = self._config['db_port']
        engine = MongoClient(db_host, db_port)
        return engine
