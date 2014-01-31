"""
Filter specification visitors.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""
from everest.entities.utils import slug_from_identifier
from everest.querying.base import CqlExpression
from everest.querying.base import SpecificationVisitor
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
from everest.resources.interfaces import IResource
from everest.resources.utils import resource_to_url
from functools import reduce as func_reduce
from operator import and_ as operator_and
from operator import or_ as operator_or
from pyramid.compat import string_types
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['CqlFilterExpression',
           'CqlFilterSpecificationVisitor',
           'FilterSpecificationVisitor',
           'RepositoryFilterSpecificationVisitor',
           ]


class FilterSpecificationVisitor(SpecificationVisitor):
    """
    Abstract base class for filter specification visitors.
    """

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
        #: Returns this CQL expression as a string.
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


@implementer(IFilterSpecificationVisitor)
class CqlFilterSpecificationVisitor(FilterSpecificationVisitor):
    """
    Filter specification visitor building a CQL expression.
    """

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

    def _conjunction_op(self, spec, *expressions):
        return func_reduce(operator_and, expressions)

    def _disjunction_op(self, spec, *expressions):
        return func_reduce(operator_or, expressions)

    def _negation_op(self, spec, expression):
        return ~expression

    def __preprocess_attribute(self, attr_name):
        return slug_from_identifier(attr_name)

    def __preprocess_value(self, value):
        if isinstance(value, string_types):
            result = '"%s"' % value
        elif IResource.providedBy(value): # pylint: disable=E1101
            result = '"%s"' % resource_to_url(value)
        else:
            result = str(value)
        return result


class RepositoryFilterSpecificationVisitor(FilterSpecificationVisitor): # pylint: disable=W0223
    """
    Specification visitors that build filter expressions for a repository
    backend.
    """
    def __init__(self, entity_class):
        FilterSpecificationVisitor.__init__(self)
        self._entity_class = entity_class

    def filter_query(self, query):
        """
        Returns the given query filtered by this visitor's filter expression.
        """
        return query.filter(self.expression)

