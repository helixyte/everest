"""
Repository for the NoSQL backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 11, 2013.
"""
from bson.objectid import ObjectId
from everest.entities.utils import get_entity_class
from everest.repositories.base import Repository
from everest.repositories.memory.session import MemorySessionFactory
from everest.repositories.nosqldb.aggregate import NoSqlAggregate
from everest.repositories.nosqldb.querying import NoSqlQuery
from everest.repositories.nosqldb.utils import MongoClassRegistry
from everest.repositories.nosqldb.utils import transform_incoming
from everest.repositories.nosqldb.utils import transform_outgoing
from everest.repositories.state import ENTITY_STATUS
from everest.repositories.state import EntityState
from everest.repositories.utils import get_engine
from everest.repositories.utils import is_engine_initialized
from everest.repositories.utils import set_engine
from everest.resources.utils import get_root_collection
from logging import getLogger as get_logger
from pymongo.mongo_client import MongoClient
from pyramid.compat import string_types
from threading import RLock
import operator

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlRepository',
           ]


class NoSqlRepository(Repository):
    """
    Repository connected to a NoSQL backend.
    """
    _configurables = Repository._configurables \
                     + ['db_host', 'db_port', 'db_name']

    lock = RLock()

    def __init__(self, name, aggregate_class=None,
                 join_transaction=True, autocommit=False):
        if aggregate_class is None:
            aggregate_class = NoSqlAggregate
        Repository.__init__(self, name, aggregate_class,
                            join_transaction=join_transaction,
                            autocommit=autocommit)
        self.__db = None
        if __debug__:
            self.__logger = get_logger('everest.repositories')
        else:
            self.__logger = None

    def retrieve(self, entity_class, filter_expression=None,
                 order_expression=None, slice_key=None):
        if not slice_key is None:
            options = dict(limit=slice_key.stop - slice_key.start,
                           skip=slice_key.start)
        else:
            options = dict()
        if not isinstance(filter_expression, string_types) \
           and not isinstance(order_expression, string_types):
            # Simple query expressions (dictionaries).
            mongo_coll = self.__get_mongo_collection(entity_class)
            sons = mongo_coll.find(spec=filter_expression,
                                   sort=order_expression,
                                   **options)
        else:
            # Complex query expression with dynamic joins that must be
            # evaluated (string).
            exprs = [filter_expression]
            if not order_expression is None:
                exprs.append('sort(%s)' % order_expression)
            if not slice_key is None:
                limit = slice_key.stop - slice_key.start
                skip = slice_key.start
                exprs.append('skip(%d).limit(%d)' % (skip, limit))
            exprs.append('toArray()')
            sons = self.__db.eval('function() {return %s;}' % '.'.join(exprs))
        for son in sons:
            yield transform_outgoing(entity_class, son)

    def count(self, entity_class, filter_expression=None):
        mongo_coll = self.__get_mongo_collection(entity_class)
        return mongo_coll.find(spec=filter_expression).count()

    def flush(self, unit_of_work):
        if __debug__:
            self.__logger.info('Starting FLUSH.')
        # First, make sure that all entities have OIDs and IDs.
        for new_ent in unit_of_work.get_new():
            ent_oid = getattr(new_ent, '_id', None)
            if ent_oid is None:
                ent_oid = ObjectId()
                setattr(new_ent, '_id', ent_oid)
            if new_ent.id is None:
                new_ent.id = str(ent_oid)
        for state in unit_of_work.iterator():
            if state.is_persisted:
                continue
            else:
                self.__persist(state)
                unit_of_work.mark_persisted(state.entity)
        if __debug__:
            self.__logger.info('Finished FLUSH.')

    def commit(self, unit_of_work):
        if __debug__:
            self.__logger.info('Starting COMMIT.')
        self.flush(unit_of_work)
        if __debug__:
            self.__logger.info('Finished COMMIT.')

    def rollback(self, unit_of_work):
        if __debug__:
            self.__logger.info('Starting ROLLBACK.')
        for state in unit_of_work.iterator():
            if state.is_persisted:
                self.__rollback(state)
        if __debug__:
            self.__logger.info('Finished ROLLBACK.')

    def _initialize(self):
        if not is_engine_initialized(self.name):
            engine = self.__make_engine()
            set_engine(self.name, engine)
        else:
            engine = get_engine(self.name)
        db_name = self._config['db_name']
        self.__db = operator.getitem(engine, db_name)
        if db_name == 'test':
            # Reset the test database.
            for coll_name in \
              self.__db.collection_names(include_system_collections=False):
                self.__db.drop_collection(coll_name)
        #
        for rc in self.registered_resources:
            ent_cls = get_entity_class(rc)
            if not MongoClassRegistry.is_registered(ent_cls):
                MongoClassRegistry.register(ent_cls, self.__db)

    def _make_session_factory(self):
        return MemorySessionFactory(self,
                                    query_class=NoSqlQuery,
                                    clone_on_load=False)

    def __make_engine(self):
        db_host = self._config['db_host']
        db_port = self._config['db_port']
        if __debug__:
            self.__logger.debug('Creating Mongo DB engine (host: %s, '
                                'port: %s' % (db_host, db_port))
        engine = MongoClient(db_host, db_port, tz_aware=True)
        return engine

    def __get_mongo_collection(self, entity_class):
#        key = "%s.%s" % (entity_class.__module__, entity_class.__name__)
        key = get_root_collection(entity_class).__name__
        return getattr(self.__db, key)

    def __persist(self, state):
        source_entity = state.entity
        ent_cls = type(source_entity)
        status = state.status
        if status != ENTITY_STATUS.CLEAN:
            mongo_coll = self.__get_mongo_collection(ent_cls)
            ent_id = source_entity.id
            ent_oid = getattr(source_entity, '_id')
            if ent_id is None or ent_oid is None:
                raise ValueError('Can not persist entity with ID value set '
                                 'to None.')
            if status == ENTITY_STATUS.DELETED:
                mongo_coll.remove(ent_oid)
            else:
                data = transform_incoming(ent_cls, source_entity)
                if status == ENTITY_STATUS.NEW:
                    mongo_coll.insert(data)
                else:
                    assert status == ENTITY_STATUS.DIRTY
                    mongo_coll.update({'_id':ent_oid}, data)

    def __rollback(self, state):
        source_entity = state.entity
        ent_cls = type(source_entity)
        status = state.status
        if status != ENTITY_STATUS.CLEAN:
            mongo_coll = self.__get_mongo_collection(ent_cls)
            ent_oid = getattr(source_entity, '_id')
            if status == ENTITY_STATUS.NEW:
                mongo_coll.remove(ent_oid)
            else:
                if status == ENTITY_STATUS.DELETED:
                    data = transform_incoming(ent_cls, source_entity)
                    mongo_coll.insert(data)
                else:
                    assert status == ENTITY_STATUS.DIRTY
                    EntityState.set_state_data(source_entity,
                                               state.clean_data)
                    data = transform_incoming(ent_cls, source_entity)
                    mongo_coll.update({'_id':ent_oid}, data)
