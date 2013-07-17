"""

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.entities.attributes import EntityAttributeKinds
from everest.querying.filtering import FilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.ordering import OrderSpecificationVisitor
from everest.querying.specifications import ValueContainedFilterSpecification
from everest.repositories.rdb.orm import OrmAttributeInspector
from everest.repositories.rdb.utils import OrderClauseList
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IResource
from functools import reduce as func_reduce
from sqlalchemy import and_ as sqlalchemy_and
from sqlalchemy import not_ as sqlalchemy_not
from sqlalchemy import or_ as sqlalchemy_or
from sqlalchemy.sql.expression import ClauseList
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['SqlFilterSpecificationVisitor',
           'SqlOrderSpecificationVisitor',
           ]


@implementer(IFilterSpecificationVisitor)
class SqlFilterSpecificationVisitor(FilterSpecificationVisitor):
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
        if len(spec.attr_value) == 1:
            value = next(iter(spec.attr_value)) # Works also for sets.
            if ICollectionResource.providedBy(value): # pylint:disable=E1101
                # FIXME: This is a hack that allows us to query for containment
                #        of a member in an arbitrary collection (not supported
                #        by SQLAlchemy yet).
                spec = ValueContainedFilterSpecification(
                                        spec.attr_name + '.id',
                                        [rc.id for rc in value])
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
                    [val.get_entity() if IResource.providedBy(val) else val # pylint: disable=E1101
                     for val in values]
                expr = getattr(entity_attr, sql_op)(*args)
            elif kind == EntityAttributeKinds.ENTITY:
                expr = entity_attr.has
                exprs.insert(0, expr)
            elif kind == EntityAttributeKinds.AGGREGATE:
                expr = entity_attr.any
                exprs.insert(0, expr)
        return func_reduce(lambda g, h: h(g), exprs, expr)


@implementer(IOrderSpecificationVisitor)
class SqlOrderSpecificationVisitor(OrderSpecificationVisitor):
    """
    Order specification visitor implementation for the rdb repository
    (builds a SQL expression).
    """

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
