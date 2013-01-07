"""
ORM data store.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from everest.datastores.base import DataStore
from everest.datastores.base import SessionFactory
from everest.entities.attributes import EntityAttributeKinds
from everest.entities.base import Aggregate
from everest.exceptions import DuplicateException
from everest.orm import AutocommittingSession
from everest.orm import OrderClauseList
from everest.orm import Session
from everest.orm import empty_metadata
from everest.orm import get_engine
from everest.orm import get_metadata
from everest.orm import is_engine_initialized
from everest.orm import is_metadata_initialized
from everest.orm import map_system_entities
from everest.orm import set_engine
from everest.orm import set_metadata
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.filtering import FilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.ordering import OrderSpecificationVisitor
from everest.querying.utils import OrmAttributeInspector
from everest.resources.interfaces import IResource
from everest.utils import get_filter_specification_visitor
from everest.utils import get_order_specification_visitor
from sqlalchemy import and_ as sqlalchemy_and
from sqlalchemy import not_ as sqlalchemy_not
from sqlalchemy import or_ as sqlalchemy_or
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.expression import ClauseList
from zope.interface import implements  # pylint: disable=E0611,F0401
from zope.sqlalchemy import ZopeTransactionExtension  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['OrmDataStore',
           'SqlFilterSpecificationVisitor',
           'SqlOrderSpecificationVisitor',
           ]


class OrmSessionFactory(SessionFactory):
    """
    Factory for ORM data store sessions.
    """
    def __init__(self, entity_store):
        SessionFactory.__init__(self, entity_store)
        if self._entity_store.autocommit:
            # Use an autocommitting Session class with our session factory.
            self.__fac = scoped_session(
                                sessionmaker(class_=AutocommittingSession))
        else:
            # Use the default Session factory.
            self.__fac = Session

    def configure(self, **kw):
        self.__fac.configure(**kw)

    def __call__(self):
        if not self.__fac.registry.has():
            self.__fac.configure(autoflush=self._entity_store.autoflush)
            if not self._entity_store.autocommit \
               and self._entity_store.join_transaction:
                # Enable the Zope transaction extension with the standard
                # sqlalchemy Session class.
                self.__fac.configure(extension=ZopeTransactionExtension())
        return self.__fac()


class OrmDataStore(DataStore):
    """
    Data store connected to a relational database backend (through an ORM).
    """
    _configurables = DataStore._configurables \
                     + ['db_string', 'metadata_factory']

    def __init__(self, name,
                 autoflush=True, join_transaction=True, autocommit=False):
        DataStore.__init__(self, name, autoflush=autoflush,
                           join_transaction=join_transaction,
                           autocommit=autocommit)
        # Default to an in-memory sqlite DB.
        self.configure(db_string='sqlite://', metadata_factory=empty_metadata)

    def _initialize(self):
        # Manages an ORM engine and a metadata instance for this entity store.
        # Both are global objects that should only be created once per process
        # (for each ORM entity store), hence we use a global object manager.
        if not is_engine_initialized(self.name):
            engine = self.__make_engine()
            set_engine(self.name, engine)
            # Bind the engine to the session factory and the metadata.
            self.session_factory.configure(bind=engine)
        else:
            engine = get_engine(self.name)
        if not is_metadata_initialized(self.name):
            md_fac = self._config['metadata_factory']
            if self._config.get('messaging_enable', False):
                # Wrap the metadata callback to also call the mapping
                # function for system entities.
                reset_on_start = \
                    self._config.get('messaging_reset_on_start', False)
                def wrapper(engine, reset_on_start=reset_on_start):
                    metadata = md_fac(engine)
                    map_system_entities(engine, metadata, reset_on_start)
                    return metadata
                metadata = wrapper(engine)
            else:
                metadata = md_fac(engine)
            set_metadata(self.name, metadata)
        else:
            metadata = get_metadata(self.name)
        metadata.bind = engine

    def _make_session_factory(self):
        return OrmSessionFactory(self)

    def __make_engine(self):
        db_string = self._config['db_string']
        if db_string.startswith('sqlite://'):
            # Enable connection sharing across threads for pysqlite.
            kw = {'poolclass':StaticPool,
                  'connect_args':{'check_same_thread':False}
                  }
        else:
            kw = {}  # pragma: no cover
        return create_engine(db_string, **kw)


class OrmAggregate(Aggregate):
    """
    Aggregate implementation for the ORM data store.
    """
    def __init__(self, entity_class, session_factory, search_mode=False):
        Aggregate.__init__(self, entity_class, session_factory)
        self._search_mode = search_mode

    def count(self):
        if not self._relationship is None:
            # We need a flush here because we may have newly added entities
            # in the aggregate which need to get an ID *before* we build the
            # relation filter spec.
            self._session.flush()
        if self.__defaults_empty:
            cnt = 0
        else:
            cnt = self.__get_filtered_query(None).count()
        return cnt

    def get_by_id(self, id_key):
        query = self.__get_filtered_query(id_key)
        try:
            ent = query.filter_by(id=id_key).one()
        except NoResultFound:
            ent = None
        except MultipleResultsFound:  # pragma: no cover
            raise DuplicateException('Duplicates found for ID "%s".' % id_key)
        return ent

    def get_by_slug(self, slug):
        query = self.__get_filtered_query(slug)
        try:
            ent = query.filter_by(slug=slug).one()
        except NoResultFound:
            ent = None
        except MultipleResultsFound:  # pragma: no cover
            raise DuplicateException('Duplicates found for slug "%s".' % slug)
        return ent

    def iterator(self):
        if self.__defaults_empty:
            raise StopIteration()
        else:
            if len(self._session.new) > 0:
                # We need a flush here because we may have newly added
                # entities in the aggregate which need to get an ID *before*
                # we build the query expression.
                self._session.flush()
            query = self._get_data_query()
            for obj in iter(query):
                yield obj

    def add(self, entity):
        if self._relationship is None:
            self._session.add(entity)
        else:
            self._relationship.children.append(entity)

    def remove(self, entity):
        if self._relationship is None:
            self._session.delete(entity)
        else:
            self._relationship.children.remove(entity)

    def update(self, entity, source_entity):
        source_entity.id = entity.id
        self._session.merge(source_entity)

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass

    def _query_generator(self, query, key):  # unused pylint: disable=W0613
        return query

    def _filter_visitor_factory(self):
        visitor_cls = get_filter_specification_visitor(EXPRESSION_KINDS.SQL)
        return visitor_cls(self.entity_class)

    def _order_visitor_factory(self):
        visitor_cls = get_order_specification_visitor(EXPRESSION_KINDS.SQL)
        return visitor_cls(self.entity_class)

    def _get_base_query(self):
        if self._relationship is None:
            query = self._session.query(self.entity_class)
        else:
            # Pre-filter the base query with the relation specification.
            rel_spec = self._relationship.specification
            visitor = self._filter_visitor_factory()
            rel_spec.accept(visitor)
            expr = visitor.expression
            query = self._session.query(self.entity_class).filter(expr)
        return query

    def _get_data_query(self):
        query = self.__get_ordered_query(self._slice_key)
        if not self._slice_key is None:
            query = query.slice(self._slice_key.start,
                                self._slice_key.stop)
        return query

    def __get_filtered_query(self, key):
        query = self._query_generator(self._get_base_query(), key)
        if not self._filter_spec is None:
            visitor = self._filter_visitor_factory()
            self._filter_spec.accept(visitor)
            query = query.filter(visitor.expression)
        return query

    def __get_ordered_query(self, key):
        query = self.__get_filtered_query(key)
        if not self._order_spec is None:
            visitor = self._order_visitor_factory()
            self._order_spec.accept(visitor)
            for join_expr in visitor.get_joins():
                # FIXME: only join when needed here.
                query = query.outerjoin(join_expr)
            query = query.order_by(visitor.expression)
        return query

    @property
    def __defaults_empty(self):
        return self._filter_spec is None and self._search_mode


class SqlFilterSpecificationVisitor(FilterSpecificationVisitor):
    """
    Filter specification visitor implementation for the ORM data store
    (builds a SQL expression).
    """

    implements(IFilterSpecificationVisitor)

    def __init__(self, entity_class, custom_clause_factories=None):
        """
        Constructs a SqlFilterSpecificationVisitor

        :param entity_class: an entity class that is mapped with SQLAlchemy
        :param custom_clause_factories: a map containing custom clause factory 
          functions for selected (attribute name, operator) combinations.
        """
        FilterSpecificationVisitor.__init__(self)
        self.__entity_class = entity_class
        if custom_clause_factories is None:
            custom_clause_factories = {}
        self.__custom_clause_factories = custom_clause_factories

    def visit_nullary(self, spec):
        key = (spec.attr_name, spec.operator.name)
        if key in self.__custom_clause_factories:
            self._push(self.__custom_clause_factories[key](spec.attr_value))
        else:
            FilterSpecificationVisitor.visit_nullary(self, spec)

    def _starts_with_op(self, spec):
        return self.__build(spec.attr_name, 'startswith', spec.attr_value)

    def _ends_with_op(self, spec):
        return self.__build(spec.attr_name, 'endswith', spec.attr_value)

    def _contains_op(self, spec):
        return self.__build(spec.attr_name, 'contains', spec.attr_value)

    def _contained_op(self, spec):
        return self.__build(spec.attr_name, 'in_', spec.attr_value)

    def _equal_to_op(self, spec):
        return self.__build(spec.attr_name, '__eq__', spec.attr_value)

    def _less_than_op(self, spec):
        return self.__build(spec.attr_name, '__lt__', spec.attr_value)

    def _less_than_or_equal_to_op(self, spec):
        return self.__build(spec.attr_name, '__le__', spec.attr_value)

    def _greater_than_op(self, spec):
        return self.__build(spec.attr_name, '__gt__', spec.attr_value)

    def _greater_than_or_equal_to_op(self, spec):
        return self.__build(spec.attr_name, '__ge__', spec.attr_value)

    def _in_range_op(self, spec):
        from_value, to_value = spec.attr_value
        return self.__build(spec.attr_name, 'between', from_value, to_value)

    def _conjunction_op(self, spec, *expressions):
        return sqlalchemy_and(*expressions)

    def _disjunction_op(self, spec, *expressions):
        return sqlalchemy_or(*expressions)

    def _negation_op(self, spec, expression):
        return sqlalchemy_not(expression)

    def __build(self, attribute_name, sql_op, *values):
        # Builds an SQL expression from the given (possibly dotted)
        # attribute name, SQL operation name, and values.
        exprs = []
        infos = OrmAttributeInspector.inspect(self.__entity_class,
                                              attribute_name)
        count = len(infos)
        for idx, info in enumerate(infos):
            kind, entity_attr = info
            if idx == count - 1:
                #
                args = \
                    [val.get_entity() if IResource.providedBy(val) else val  # pylint: disable=E1101
                     for val in values]
                expr = getattr(entity_attr, sql_op)(*args)
            elif kind == EntityAttributeKinds.ENTITY:
                expr = entity_attr.has
                exprs.insert(0, expr)
            elif kind == EntityAttributeKinds.AGGREGATE:
                expr = entity_attr.any
                exprs.insert(0, expr)
        return reduce(lambda g, h: h(g), exprs, expr)


class SqlOrderSpecificationVisitor(OrderSpecificationVisitor):
    """
    Order specification visitor implementation for the ORM data store 
    (builds a SQL expression).
    """

    implements(IOrderSpecificationVisitor)

    def __init__(self, entity_class, custom_join_clauses=None):
        """
        Constructs a SqlOrderSpecificationVisitor

        :param klass: a class that is mapped to a selectable using SQLAlchemy
        """
        OrderSpecificationVisitor.__init__(self)
        self.__entity_class = entity_class
        if custom_join_clauses is None:
            custom_join_clauses = {}
        self.__custom_join_clauses = custom_join_clauses
        self.__joins = set()

    def visit_nullary(self, spec):
        OrderSpecificationVisitor.visit_nullary(self, spec)
        if spec.attr_name in self.__custom_join_clauses:
            self.__joins = set(self.__custom_join_clauses[spec.attr_name])

    def get_joins(self):
        return self.__joins.copy()

    def _conjunction_op(self, spec, *expressions):
        clauses = []
        for expr in expressions:
            if isinstance(expr, ClauseList):
                clauses.extend(expr.clauses)
            else:
                clauses.append(expr)
        return OrderClauseList(*clauses)

    def _asc_op(self, spec):
        return self.__build(spec.attr_name, 'asc')

    def _desc_op(self, spec):
        return self.__build(spec.attr_name, 'desc')

    def __build(self, attribute_name, sql_op):
        expr = None
        infos = OrmAttributeInspector.inspect(self.__entity_class,
                                              attribute_name)
        count = len(infos)
        for idx, info in enumerate(infos):
            kind, entity_attr = info
            if idx == count - 1:
                expr = getattr(entity_attr, sql_op)()
            elif kind != EntityAttributeKinds.TERMINAL:
                # FIXME: Avoid adding multiple attrs with the same target here.
                self.__joins.add(entity_attr)
        return expr
