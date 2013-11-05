"""
Repository for the NoSQL backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 11, 2013.
"""
from bson.objectid import ObjectId
from bson.son import SON
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.repositories.base import Repository
from everest.repositories.memory.session import MemorySessionFactory
from everest.repositories.nosqldb.aggregate import NoSqlAggregate
from everest.repositories.state import ENTITY_STATES
from everest.repositories.utils import is_engine_initialized
from everest.repositories.utils import set_engine
from everest.resources.attributes import get_resource_class_attribute_iterator
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import resource_to_url
from pymongo.mongo_client import MongoClient
import operator
from everest.resources.utils import url_to_resource

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlRepository',
           ]


class NoSqlRepository(Repository):
    """
    Repository connected to a NoSQL backend.
    """
    _configurables = Repository._configurables \
                     + ['db_host', 'db_port', 'db_name']

    def __init__(self, name, aggregate_class=None,
                 join_transaction=True, autocommit=False):
        if aggregate_class is None:
            aggregate_class = NoSqlAggregate
        Repository.__init__(self, name, aggregate_class,
                            join_transaction=join_transaction,
                            autocommit=autocommit)
        self.__db = None

    def retrieve(self, entity_class, filter_expression=None,
                 order_expression=None, slice_expression=None):
        key = self.__make_class_key(entity_class)
        coll = getattr(self.__db, key)
        if not slice_expression is None:
            limit = slice_expression.stop - slice_expression.start
            skip = slice_expression.start
        else:
            limit = skip = None
        sons = coll.find(spec=filter_expression, skip=skip, limit=limit,
                         sort=order_expression)
        return [self.__transform_outgoing(entity_class, son) for son in sons]

    def commit(self, unit_of_work):
        for ent_cls, ent, state in unit_of_work.iterator():
            if state == ENTITY_STATES.CLEAN:
                continue
            key = self.__make_class_key(ent_cls)
            coll = getattr(self.__db, key)
            if state == ENTITY_STATES.DELETED:
                coll.remove(ent._id) # pylint: disable=W0212
            else:
                data = self.__transform_incoming(ent_cls, ent)
                if state == ENTITY_STATES.NEW:
                    data['_id'] = ObjectId()
                    coll.insert(data)
                elif state == ENTITY_STATES.DIRTY:
                    coll.update({'_id':ent.id}, data)
                unit_of_work.mark_clean(ent_cls, ent)

    def new_entity_id(self):
        return str(ObjectId())

    def _initialize(self):
        if not is_engine_initialized(self.name):
            engine = self.__make_engine()
            set_engine(self.name, engine)
        db_name = self._config['db_name']
        self.__db = operator.getitem(engine, db_name)

    def _make_session_factory(self):
        return MemorySessionFactory(self)

    def __make_engine(self):
        db_host = self._config['db_host']
        db_port = self._config['db_port']
        engine = MongoClient(db_host, db_port)
        return engine

    def __make_class_key(self, entity_class):
        return "%s.%s" % (entity_class.__module__, entity_class.__name__)

    def __transform_incoming(self, ent_cls, ent):
        # Converts an incoming entity into a SON object. In particular,
        # this involves translating entity references to URLs.
        son = SON()
        root_coll = get_root_collection(ent_cls)
        coll_cls = get_collection_class(ent_cls)
        parent = coll_cls.create_from_entity(ent)
        parent.__parent__ = root_coll
        for attr in get_resource_class_attribute_iterator(coll_cls):
            value = getattr(ent, attr.resource_attr)
            if not attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                son[attr.entity_attr] = resource_to_url(value)
            else:
                son[attr.entity_attr] = value
        return son

    def __transform_outgoing(self, ent_cls, son):
        coll_cls = get_collection_class(ent_cls)
        for attr in get_resource_class_attribute_iterator(coll_cls):
            if not attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                url = son[attr.resource_attr]
                rc = url_to_resource(url)
                son[attr.resource_attr] = rc
        return son
