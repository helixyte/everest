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
from everest.repositories.rdb.utils import OrderClauseList
from everest.resources.interfaces import IResource
from sqlalchemy import and_ as sqlalchemy_and
from sqlalchemy import not_ as sqlalchemy_not
from sqlalchemy import or_ as sqlalchemy_or
from sqlalchemy.orm.interfaces import MANYTOMANY
from sqlalchemy.orm.interfaces import MANYTOONE
from sqlalchemy.orm.interfaces import ONETOMANY
from sqlalchemy.sql.expression import ClauseList
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['OrmAttributeInspector',
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
#                if kind == EntityAttributeKinds.AGGREGATE:
#                    raise ValueError('Invalid attribute name "%s": the '
#                                     'last element (%s) references an '
#                                     'aggregate attribute.'
#                                     % (attribute_name, ent_attr_token))
            else:
                if kind == EntityAttributeKinds.TERMINAL:
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
            kind = EntityAttributeKinds.TERMINAL
            target_type = None
        else: # We have a relationship.
            target_type = attr.property.argument
            if attr.property.direction in (ONETOMANY, MANYTOMANY):
                if not attr.property.uselist:
                    # 1:1
                    kind = EntityAttributeKinds.ENTITY
                else:
                    kind = EntityAttributeKinds.AGGREGATE
            elif attr.property.direction == MANYTOONE:
                kind = EntityAttributeKinds.ENTITY
            else:
                raise ValueError('Unsupported relationship direction "%s".' # pragma: no cover
                                 % attr.property.direction)
        return kind, target_type


class SqlFilterSpecificationVisitor(FilterSpecificationVisitor):
    """
    Filter specification visitor implementation for the RDB repository
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
                    [val.get_entity() if IResource.providedBy(val) else val # pylint: disable=E1101
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
    Order specification visitor implementation for the rdb repository 
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
