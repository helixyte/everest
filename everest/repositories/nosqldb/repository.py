"""
Repository for the NoSQL backend.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 11, 2013.
"""
from everest.repositories.base import Repository
from everest.repositories.nosqldb.aggregate import NoSqlAggregate
from everest.repositories.state import ENTITY_STATES
from everest.repositories.utils import is_engine_initialized
from everest.repositories.utils import set_engine
from pymongo.mongo_client import MongoClient
from bson.objectid import ObjectId

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlRepository',
           ]


class NoSqlRepository(Repository):
    """
    Repository connected to a NoSQL backend.
    """
    def __init__(self, name, aggregate_class=None,
                 join_transaction=True, autocommit=False):
        if aggregate_class is None:
            aggregate_class = NoSqlAggregate
        Repository.__init__(self, name, aggregate_class,
                            join_transaction=join_transaction,
                            autocommit=autocommit)
        self.__db = None

    def commit(self, unit_of_work):
        for ent_cls, ent, state in unit_of_work.iterator():
            if state == ENTITY_STATES.CLEAN:
                continue
            key = self.__make_class_key(ent_cls)
            coll = getattr(self.__db, key)
            if state == ENTITY_STATES.DELETED:
                coll.remove(ent)
            elif state == ENTITY_STATES.NEW:
                ent._id = ObjectId(ent.id) # pylint: disable=W0212
                coll.add(ent)
                unit_of_work.mark_clean(ent_cls, ent)
            elif state == ENTITY_STATES.DIRTY:
                coll.update({'_id':ent.id}, ent)

    def new_entity_id(self):
        return str(ObjectId())

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

    def __make_class_key(self, entity_class):
        return "%s.%s" % (entity_class.__module__, entity_class.__name__)
