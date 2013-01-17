"""
Data store for the NoSQL backend.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 11, 2013.
"""
from everest.datastores.base import DataStore
from everest.datastores.utils import is_engine_initialized
from everest.datastores.utils import set_engine
from pymongo.mongo_client import MongoClient

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlDataStore',
           ]


class NoSqlDataStore(DataStore):
    """
    Data store connected to a NoSQL backend.
    """
    def __init__(self, name,
                 autoflush=True, join_transaction=True, autocommit=False):
        DataStore.__init__(self, name, autoflush=autoflush,
                           join_transaction=join_transaction,
                           autocommit=autocommit)

    def _initialize(self):
        if not is_engine_initialized(self.name):
            engine = self.__make_engine()
            set_engine(self.name, engine)

    def _make_session_factory(self):
        DataStore._make_session_factory(self)

    def __make_engine(self):
        db_host = self._config['host']
        db_port = self._config['port']
        engine = MongoClient(db_host, db_port)
        return engine


