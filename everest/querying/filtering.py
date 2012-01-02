"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""

from everest.entities.attributes import EntityAttributeKinds
from everest.entities.utils import slug_from_identifier
from everest.querying.base import CqlExpression
from everest.querying.base import SpecificationBuilder
from everest.querying.base import SpecificationDirector
from everest.querying.base import SpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationBuilder
from everest.querying.interfaces import IFilterSpecificationDirector
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.operators import CONTAINED
from everest.querying.operators import CONTAINS
from everest.querying.operators import ENDS_WITH
from everest.querying.operators import EQUAL_TO
from everest.querying.operators import GREATER_OR_EQUALS
from everest.querying.operators import GREATER_THAN
from everest.querying.operators import IN_RANGE
from everest.querying.operators import LESS_OR_EQUALS
from everest.querying.operators import LESS_THAN
from everest.querying.operators import STARTS_WITH
from everest.querying.utils import OrmAttributeInspector
from everest.resources.interfaces import IResource
from everest.url import resource_to_url
from everest.url import url_to_resource
from functools import partial
from operator import and_ as operator_and
from operator import or_ as operator_or
from sqlalchemy import and_ as sqlalchemy_and
from sqlalchemy import not_ as sqlalchemy_not
from sqlalchemy import or_ as sqlalchemy_or
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['CqlFilterSpecificationVisitor',
           'EvalFilterSpecificationVisitor',
           'FilterSpecificationBuilder',
           'FilterSpecificationDirector',
           'FilterSpecificationVisitor',
           'SqlFilterSpecificationVisitor',
           ]


class FilterSpecificationDirector(SpecificationDirector):
    """
    Director for filter specifications.
    """

    implements(IFilterSpecificationDirector)

    def _process_parse_result(self, parse_result):
        for crit in parse_result.criteria:
            name, op_string, values = crit
            if len(values) > 0: # criteria with no values are ignored
                name = self._format_identifier(name)
                op_name = self._format_identifier(op_string)
                values = self.__prepare_values(values)
                func = self._get_build_function(op_name)
                func(name, values)

    def __prepare_values(self, values):
        prepared = []
        for v in values:
            if self.__is_empty_string(v):
                continue
            elif self.__is_url(v):
                v = url_to_resource(''.join(v))
            if not v in prepared:
                prepared.append(v)
        return prepared

    def __is_url(self, v):
        return isinstance(v, basestring) and v.startswith('http://')

    def __is_empty_string(self, v):
        return isinstance(v, basestring) and len(v) == 0


class FilterSpecificationBuilder(SpecificationBuilder):
    """
    Filter specification builder.
    
    The filter specification builder is responsible for building concrete
    specs with build methods dispatched by the director and for forming 
    disjunction specs when a) multiple values are given in a single criterion;
    or b) the same combination of attribute name and operator is encountered
    multiple times.
    """

    implements(IFilterSpecificationBuilder)

    def __init__(self, spec_factory):
        SpecificationBuilder.__init__(self, spec_factory)
        self.__history = set()

    def build_equal_to(self, attr_name, attr_values):
        self._record_specification(
            self.__build_spec(self._spec_factory.create_equal_to,
                              attr_name, attr_values)
            )

    def build_not_equal_to(self, attr_name, attr_values):
        self._record_specification(
            self.__build_spec(self._spec_factory.create_equal_to,
                              attr_name, attr_values).not_()
            )

    def build_starts_with(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_starts_with,
                                 attr_name, attr_values)
        self._record_specification(spec)

    def build_not_starts_with(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_starts_with,
                                 attr_name, attr_values).not_()
        self._record_specification(spec)

    def build_ends_with(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_ends_with,
                                 attr_name, attr_values)
        self._record_specification(spec)

    def build_not_ends_with(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_ends_with,
                                 attr_name, attr_values).not_()
        self._record_specification(spec)

    def build_contained(self, attr_name, attr_values):
        # For the CONTAINED spec, we treat all parsed values as one value.
        spec = self.__build_spec(self._spec_factory.create_contained,
                                 attr_name, [attr_values])
        self._record_specification(spec)

    def build_not_contained(self, attr_name, attr_values):
        # For the CONTAINED spec, we treat all parsed values as one value.
        spec = self.__build_spec(self._spec_factory.create_contained,
                                 attr_name, [attr_values])
        self._record_specification(spec).not_()

    def build_contains(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_contains,
                                 attr_name, attr_values)
        self._record_specification(spec)

    def build_not_contains(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_contains,
                                 attr_name, attr_values).not_()
        self._record_specification(spec)

    def build_less_than_or_equal_to(self, attr_name, attr_values):
        spec = self.__build_spec(
                            self._spec_factory.create_less_than_or_equal_to,
                            attr_name, attr_values)
        self._record_specification(spec)

    def build_less_than(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_less_than,
                                 attr_name, attr_values)
        self._record_specification(spec)

    def build_greater_than_or_equal_to(self, attr_name, attr_values):
        spec = self.__build_spec(
                        self._spec_factory.create_greater_than_or_equal_to,
                        attr_name, attr_values)
        self._record_specification(spec)

    def build_greater_than(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_greater_than,
                                 attr_name, attr_values)
        self._record_specification(spec)

    def build_in_range(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_in_range,
                                 attr_name, attr_values)
        self._record_specification(spec)

    def build_not_in_range(self, attr_name, attr_values):
        spec = self.__build_spec(self._spec_factory.create_in_range,
                                 attr_name, attr_values).not_()
        self._record_specification(spec)

    def __build_spec(self, constructor, attr_name, attr_values):
        # Check if this (constructor, attr_name) combination has been seen
        # before. Currently, this is handled with an exception.
        key = (constructor, attr_name)
        if key in self.__history:
            raise ValueError('Can not build multiple specifications with '
                             'the same combination of attribute name and '
                             'filter operator.')
        else:
            self.__history.add(key)
        # Builds a single specification with the given spec constructor, 
        # attribute name and attribute values. 
        spec = None
        # Iterate over attribute values, forming disjunctions if more than one
        # was provided.
        for attr_value in attr_values:
            cur_spec = constructor(attr_name, attr_value)
            if spec is None:
                spec = cur_spec
            else:
                spec = self._spec_factory.create_disjunction(spec, cur_spec)
        return spec


class FilterSpecificationVisitor(SpecificationVisitor):
    """
    Base class for filter specification visitors.
    """

    def __init__(self):
        SpecificationVisitor.__init__(self)

    def _disjunction_op(self, spec, *expressions):
        raise NotImplementedError('Abstract method.')

    def _negation_op(self, spec, expression):
        raise NotImplementedError('Abstract method.')

    def _starts_with_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _ends_with_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _contains_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _contained_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _equal_to_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _less_than_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _less_than_or_equal_to_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _greater_than_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _greater_than_or_equal_to_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _in_range_op(self, spec):
        raise NotImplementedError('Abstract method.')


class CqlFilterExpression(CqlExpression):
    """
    CQL expression representing a filter criterion.
    """
    __cql_format = '%(attr)s:%(op)s:%(val)s'
    __cql_or = ','
    __cql_not = 'not-'

    def __init__(self, attr_name, op_name, value):
        CqlExpression.__init__(self)
        self.attr_name = attr_name
        self.op_name = op_name
        self.value = value

    def _as_string(self):
        return self.__cql_format % dict(attr=self.attr_name,
                                        op=slug_from_identifier(self.op_name),
                                        val=self.value)

    def __or__(self, other):
        if self.attr_name != other.attr_name \
           or self.op_name != other.op_name:
            raise ValueError('Attribute name and operator need to be the same '
                             'for CQL OR operation.')
        return CqlFilterExpression(self.attr_name, self.op_name,
                                   self.__cql_or.join(
                                                (self.value, other.value)))

    def __invert__(self):
        if self.op_name in [STARTS_WITH.name, ENDS_WITH.name, CONTAINED.name,
                            CONTAINS.name, EQUAL_TO.name, IN_RANGE.name]:
            op_name = "%s%s" % (self.__cql_not, self.op_name)
        elif self.op_name == LESS_THAN.name:
            op_name = GREATER_OR_EQUALS.name
        elif self.op_name == GREATER_THAN.name:
            op_name = LESS_OR_EQUALS.name
        elif self.op_name == LESS_OR_EQUALS.name:
            op_name = GREATER_THAN.name
        elif self.op_name == GREATER_OR_EQUALS.name:
            op_name = LESS_THAN.name
        else:
            raise ValueError('Invalid (non-invertible) operator name %s.'
                             % self.op_name)
        return CqlFilterExpression(self.attr_name, op_name, self.value)


class CqlFilterSpecificationVisitor(FilterSpecificationVisitor):
    """
    Filter specification visitor building a CQL expression.
    """

    implements(IFilterSpecificationVisitor)

    __cql_range_format = '%(from_value)s-%(to_value)s'

    def _starts_with_op(self, spec):
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   STARTS_WITH.name,
                                   self.__preprocess_value(spec.attr_value))

    def _ends_with_op(self, spec):
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   ENDS_WITH.name,
                                   self.__preprocess_value(spec.attr_value))

    def _contains_op(self, spec):
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   CONTAINS.name,
                                   self.__preprocess_value(spec.attr_value))

    def _contained_op(self, spec):
        value_string = \
            ','.join([self.__preprocess_value(val) for val in spec.attr_value])
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   CONTAINED.name,
                                   value_string)

    def _equal_to_op(self, spec):
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   EQUAL_TO.name,
                                   self.__preprocess_value(spec.attr_value))

    def _less_than_op(self, spec):
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   LESS_THAN.name,
                                   self.__preprocess_value(spec.attr_value))

    def _less_than_or_equal_to_op(self, spec):
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   LESS_OR_EQUALS.name,
                                   self.__preprocess_value(spec.attr_value))

    def _greater_than_op(self, spec):
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   GREATER_THAN.name,
                                   self.__preprocess_value(spec.attr_value))

    def _greater_than_or_equal_to_op(self, spec):
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   GREATER_OR_EQUALS.name,
                                   self.__preprocess_value(spec.attr_value))

    def _in_range_op(self, spec):
        from_value, to_value = spec.attr_value
        value = self.__cql_range_format % dict(
                          from_value=self.__preprocess_value(from_value),
                          to_value=self.__preprocess_value(to_value)
                          )
        return CqlFilterExpression(self.__preprocess_attribute(spec.attr_name),
                                   IN_RANGE.name,
                                   value)

    def _conjunction_op(self, spec, *expressions): # unused pylint:disable=W0613
        return reduce(operator_and, expressions)

    def _disjunction_op(self, spec, *expressions):
        return reduce(operator_or, expressions)

    def _negation_op(self, spec, expression):
        return ~expression

    def __preprocess_attribute(self, attr_name):
        return slug_from_identifier(attr_name)

    def __preprocess_value(self, value):
        if isinstance(value, basestring):
            result = '"%s"' % value
        elif IResource.providedBy(value): # pylint: disable=E1101
            result = resource_to_url(value)
        else:
            result = str(value)
        return result


class SqlFilterSpecificationVisitor(FilterSpecificationVisitor):
    """
    Filter specification visitor building a SQL expression.
    """

    implements(IFilterSpecificationVisitor)

    def __init__(self, entity_class, clause_factories=None):
        """
        Constructs a SqlFilterSpecificationVisitor

        :param entity_class: an entity class that is mapped with SQLAlchemy
        :param clause_factories: a map containing custom clause factory 
          functions for selected (attribute name, operator) combinations.
        """
        FilterSpecificationVisitor.__init__(self)
        self.__entity_class = entity_class
        if clause_factories is None:
            clause_factories = {}
        self.__clause_factories = clause_factories

    def visit_nullary(self, spec):
        key = (spec.attr_name, spec.operator.name)
        if key in self.__clause_factories:
            self._push(self.__clause_factories[key](spec.attr_value))
        else:
            FilterSpecificationVisitor.visit_nullary(self, spec)

    def _starts_with_op(self, spec):
        return self.__build(spec.attr_name, 'startswith',
                            self.__preprocess_value(spec.attr_value))

    def _ends_with_op(self, spec):
        return self.__build(spec.attr_name, 'endswith',
                            self.__preprocess_value(spec.attr_value))

    def _contains_op(self, spec):
        return self.__build(spec.attr_name, 'contains',
                            self.__preprocess_value(spec.attr_value))

    def _contained_op(self, spec):
        return self.__build(spec.attr_name, 'in_',
                            self.__preprocess_value(spec.attr_value))

    def _equal_to_op(self, spec):
        return self.__build(spec.attr_name, '__eq__',
                            self.__preprocess_value(spec.attr_value))

    def _less_than_op(self, spec):
        return self.__build(spec.attr_name, '__lt__',
                            self.__preprocess_value(spec.attr_value))

    def _less_than_or_equal_to_op(self, spec):
        return self.__build(spec.attr_name, '__le__',
                            self.__preprocess_value(spec.attr_value))

    def _greater_than_op(self, spec):
        return self.__build(spec.attr_name, '__gt__',
                            self.__preprocess_value(spec.attr_value))

    def _greater_than_or_equal_to_op(self, spec):
        return self.__build(spec.attr_name, '__ge__',
                            self.__preprocess_value(spec.attr_value))

    def _in_range_op(self, spec):
        from_value, to_value = spec.attr_value
        return self.__build(spec.attr_name, 'between',
                            self.__preprocess_value(from_value),
                            self.__preprocess_value(to_value))

    def _conjunction_op(self, spec, *expressions):
        return sqlalchemy_and(*expressions)

    def _disjunction_op(self, spec, *expressions):
        return sqlalchemy_or(*expressions)

    def _negation_op(self, spec, expression):
        return sqlalchemy_not(expression)

    def __preprocess_value(self, value):
        if IResource.providedBy(value): # pylint: disable=E1101
            conv_value = value.get_entity()
        else:
            conv_value = value
        return conv_value

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
                expr = getattr(entity_attr, sql_op)(*values)
            elif kind == EntityAttributeKinds.ENTITY:
                expr = entity_attr.has
                exprs.insert(0, expr)
            elif kind == EntityAttributeKinds.AGGREGATE:
                expr = entity_attr.any
                exprs.insert(0, expr)
        return reduce(lambda g, h: h(g), exprs, expr)


class EvalFilterSpecificationVisitor(FilterSpecificationVisitor):
    """
    Filter specification visitor building an evaluator for in-memory 
    filtering.
    """

    implements(IFilterSpecificationVisitor)

    __evaluator = lambda spec, entities: [ent for ent in entities
                                          if spec.is_satisfied_by(ent)]

    def _conjunction_op(self, spec, *expressions):
        return partial(self.__evaluator, spec)

    def _disjunction_op(self, spec, *expressions):
        return partial(self.__evaluator, spec)

    def _negation_op(self, spec, expression):
        return partial(self.__evaluator, spec)

    def _starts_with_op(self, spec):
        return partial(self.__evaluator, spec)

    def _ends_with_op(self, spec):
        return partial(self.__evaluator, spec)

    def _contains_op(self, spec):
        return partial(self.__evaluator, spec)

    def _contained_op(self, spec):
        return partial(self.__evaluator, spec)

    def _equal_to_op(self, spec):
        return partial(self.__evaluator, spec)

    def _less_than_op(self, spec):
        return partial(self.__evaluator, spec)

    def _less_than_or_equal_to_op(self, spec):
        return partial(self.__evaluator, spec)

    def _greater_than_op(self, spec):
        return partial(self.__evaluator, spec)

    def _greater_than_or_equal_to_op(self, spec):
        return partial(self.__evaluator, spec)

    def _in_range_op(self, spec):
        return partial(self.__evaluator, spec)
