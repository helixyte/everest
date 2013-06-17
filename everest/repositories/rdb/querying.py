"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.constants import DomainAttributeKinds
from everest.exceptions import MultipleResultsException
from everest.exceptions import NoResultsException
from everest.querying.filtering import RepositoryFilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.ordering import OrderSpecificationVisitor
from everest.querying.ordering import RepositoryOrderSpecificationVisitor
from everest.resources.interfaces import IResource
from functools import reduce as func_reduce
from sqlalchemy import and_ as sqlalchemy_and
from sqlalchemy import not_ as sqlalchemy_not
from sqlalchemy import or_ as sqlalchemy_or
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.interfaces import MANYTOMANY
from sqlalchemy.orm.interfaces import MANYTOONE
from sqlalchemy.orm.interfaces import ONETOMANY
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import ClauseList
from sqlalchemy.sql.expression import func
from sqlalchemy.sql.expression import over
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['OptimizedCountingQuery',
           'OrderClauseList',
           'OrmAttributeInspector',
           'SimpleCountingQuery',
           'SqlFilterSpecificationVisitor',
           'SqlOrderSpecificationVisitor',
           ]


class OrmAttributeInspector(object):
    """
    Helper class inspecting class attributes mapped by the ORM.
    """
    __cache = {}

    @staticmethod
    def inspect(orm_class, attribute_name):
        """
        :param attribute_name: name of the mapped attribute to inspect.
        :returns: list of 2-tuples containing information about the inspected
          attribute (first element: mapped entity attribute kind; second 
          attribute: mapped entity attribute) 
        """
        key = (orm_class, attribute_name)
        elems = OrmAttributeInspector.__cache.get(key)
        if elems is None:
            elems = OrmAttributeInspector.__inspect(key)
            OrmAttributeInspector.__cache[key] = elems
        return elems

    @staticmethod
    def __inspect(key):
        orm_class, attribute_name = key
        elems = []
        entity_type = orm_class
        ent_attr_tokens = attribute_name.split('.')
        count = len(ent_attr_tokens)
        for idx, ent_attr_token in enumerate(ent_attr_tokens):
            entity_attr = getattr(entity_type, ent_attr_token)
            kind, attr_type = OrmAttributeInspector.__classify(entity_attr)
            if idx == count - 1:
                pass
                # We are at the last name token - this must be a TERMINAL
                # or an ENTITY.
#                if kind == DomainAttributeKinds.AGGREGATE:
#                    raise ValueError('Invalid attribute name "%s": the '
#                                     'last element (%s) references an '
#                                     'aggregate attribute.'
#                                     % (attribute_name, ent_attr_token))
            else:
                if kind == DomainAttributeKinds.TERMINAL:
                    # We should not get here - the last attribute was a
                    # terminal.
                    raise ValueError('Invalid attribute name "%s": the '
                                     'element "%s" references a terminal '
                                     'attribute.'
                                     % (attribute_name, ent_attr_token))
                entity_type = attr_type
            elems.append((kind, entity_attr))
        return elems

    @staticmethod
    def __classify(attr):
        # Looks up the entity attribute kind and target type for the given
        # entity attribute.
        # We look for an attribute "property" to identify mapped attributes
        # (instrumented attributes and attribute proxies).
        if not hasattr(attr, 'property'):
            raise ValueError('Attribute "%s" is not mapped.' % attr)
        # We detect terminals by the absence of an "argument" attribute of
        # the attribute's property.
        if not hasattr(attr.property, 'argument'):
            kind = DomainAttributeKinds.TERMINAL
            target_type = None
        else: # We have a relationship.
            target_type = attr.property.argument
            if attr.property.direction in (ONETOMANY, MANYTOMANY):
                if not attr.property.uselist:
                    # 1:1
                    kind = DomainAttributeKinds.ENTITY
                else:
                    kind = DomainAttributeKinds.AGGREGATE
            elif attr.property.direction == MANYTOONE:
                kind = DomainAttributeKinds.ENTITY
            else:
                raise ValueError('Unsupported relationship direction "%s".' # pragma: no cover
                                 % attr.property.direction)
        return kind, target_type


@implementer(IFilterSpecificationVisitor)
class SqlFilterSpecificationVisitor(RepositoryFilterSpecificationVisitor):
    """
    Filter specification visitor implementation for the RDB repository
    (builds a SQL expression).
    """
    def __init__(self, entity_class, custom_clause_factories=None):
        """
        Constructs a SqlFilterSpecificationVisitor

        :param entity_class: an entity class that is mapped with SQLAlchemy
        :param custom_clause_factories: a map containing custom clause factory 
          functions for selected (attribute name, operator) combinations.
        """
        RepositoryFilterSpecificationVisitor.__init__(self, entity_class)
        if custom_clause_factories is None:
            custom_clause_factories = {}
        self.__custom_clause_factories = custom_clause_factories

    def visit_nullary(self, spec):
        key = (spec.attr_name, spec.operator.name)
        if key in self.__custom_clause_factories:
            self._push(self.__custom_clause_factories[key](spec.attr_value))
        else:
            RepositoryFilterSpecificationVisitor.visit_nullary(self, spec)

    def filter_query(self, query):
        return query.filter(self.expression)

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
        infos = OrmAttributeInspector.inspect(self._entity_class,
                                              attribute_name)
        count = len(infos)
        for idx, info in enumerate(infos):
            kind, entity_attr = info
            if idx == count - 1:
                #
                args = \
                    [val.get_entity() if IResource.providedBy(val) else val # pylint: disable=E1101
                     for val in values]
                expr = getattr(entity_attr, sql_op)(*args)
            elif kind == DomainAttributeKinds.ENTITY:
                expr = entity_attr.has
                exprs.insert(0, expr)
            elif kind == DomainAttributeKinds.AGGREGATE:
                expr = entity_attr.any
                exprs.insert(0, expr)
        return func_reduce(lambda g, h: h(g), exprs, expr)


class OrderClauseList(ClauseList):
    """
    Custom clause list for ORDER BY clauses.
    
    Suppresses the grouping parentheses which would trigger a syntax error.
    """
    def self_group(self, against=None):
        return self


@implementer(IOrderSpecificationVisitor)
class SqlOrderSpecificationVisitor(RepositoryOrderSpecificationVisitor):
    """
    Order specification visitor implementation for the rdb repository 
    (builds a SQL expression).
    """
    def __init__(self, entity_class, custom_join_clauses=None):
        """
        Constructs a SqlOrderSpecificationVisitor

        :param klass: a class that is mapped to a selectable using SQLAlchemy
        """
        RepositoryOrderSpecificationVisitor.__init__(self, entity_class)
        if custom_join_clauses is None:
            custom_join_clauses = {}
        self.__custom_join_clauses = custom_join_clauses
        self.__joins = set()

    def visit_nullary(self, spec):
        OrderSpecificationVisitor.visit_nullary(self, spec)
        if spec.attr_name in self.__custom_join_clauses:
            self.__joins = set(self.__custom_join_clauses[spec.attr_name])

    def order_query(self, query):
        for join_expr in self.__joins:
            # FIXME: only join when needed here.
            query = query.outerjoin(join_expr)
        return query.order_by(self.expression)

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
        infos = OrmAttributeInspector.inspect(self._entity_class,
                                              attribute_name)
        count = len(infos)
        for idx, info in enumerate(infos):
            kind, entity_attr = info
            if idx == count - 1:
                expr = getattr(entity_attr, sql_op)()
            elif kind != DomainAttributeKinds.TERMINAL:
                # FIXME: Avoid adding multiple attrs with the same target here.
                self.__joins.add(entity_attr)
        return expr


class _CountingQuery(Query):
    def __init__(self, *args, **kw):
        Query.__init__(self, *args, **kw)
        self.__count = None
        self.__data = None

    def __iter__(self):
        if self.__data is None:
            self.__count, self.__data = self._load()
        return iter(self.__data)

    def count(self):
        if self.__count is None:
            self.__count, self.__data = self._load()
        return self.__count

    def one(self):
        # Overwritten so we can translate exceptions.
        try:
            return Query.one(self)
        except NoResultFound:
            raise NoResultsException('No results found when exactly one '
                                     'was expected.')
        except MultipleResultsFound:
            raise MultipleResultsException('More than one result found '
                                           'where exactly one was expected.')

    def _load(self):
        raise NotImplementedError('Abstract method.')

    def _clone(self):
        clone = Query._clone(self)
        # pylint: disable=W0212
        clone.__data = None
        clone.__count = None
        # pylint: enable=W0212
        return clone


class SimpleCountingQuery(_CountingQuery):

    def _load(self):
        count_query = self.limit(None).offset(None)
        # Avoid circular calls to _load by "downcasting" the new query.
        count_query.__class__ = Query
        count = count_query.count()
        return count, list(Query.__iter__(self))


class OptimizedCountingQuery(_CountingQuery): # pragma: no cover

    def _load(self):
        query = self.add_columns(over(func.count(1)).label('_count'))
        res = [tup[0] for tup in Query.__iter__(query)]
        if len(res) > 0:
            count = tup._count # pylint:disable-msg=W0212,W0631
        else:
            count = 0
        return count, res
