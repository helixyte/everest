"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 29, 2013.
"""
from everest.querying.filtering import RepositoryFilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationVisitor
from pyramid.compat import string_types
from zope.interface import implementer # pylint: disable=E0611,F0401
import re

__docformat__ = 'reStructuredText en'
__all__ = []

class Query(object):
    pass


@implementer(IFilterSpecificationVisitor)
class NoSqlFilterSpecificationVisitor(RepositoryFilterSpecificationVisitor):
    def filter_query(self, query):
        RepositoryFilterSpecificationVisitor.filter_query(self, query)

    def _starts_with_op(self, spec):
        return {spec.attr_name :
                {'$regex' : re.compile('^%s.*$' % spec.attr_value)}}

    def _ends_with_op(self, spec):
        return {spec.attr_name :
                {'$regex' : re.compile('^.*%s$' % spec.attr_value)}}

    def _contains_op(self, spec):
        if isinstance(spec.attr_value, string_types):
            expr = {spec.attr_name :
                    {'$regex' : re.compile('^.*%s.*$' % spec.attr_value)}}
        else:
            expr = {spec.attr_name : {'$exists' : spec.attr_value}}
        return expr

    def _contained_op(self, spec):
        return {spec.attr_name : {'$in' : spec.attr_value}}

    def _equal_to_op(self, spec):
        return {spec.attr_name : spec.attr_value}

    def _less_than_op(self, spec):
        return {spec.attr_name : {'$lt' : spec.attr_value}}

    def _less_than_or_equal_to_op(self, spec):
        return {spec.attr_name : {'$lte' : spec.attr_value}}

    def _greater_than_op(self, spec):
        return {spec.attr_name : {'$gt' : spec.attr_value}}

    def _greater_than_or_equal_to_op(self, spec):
        return {spec.attr_name : {'$gte' : spec.attr_value}}

    def _in_range_op(self, spec):
        from_value, to_value = spec.attr_value
        return {'$and' : [{spec.attr_value : {'$gte' : from_value},
                           spec.attr_value : {'$lte' : to_value}}]}

    def _conjunction_op(self, spec, *expressions):
        return {'$and' : list(*expressions)}

    def _disjunction_op(self, spec, *expressions):
        return {'$or' : list(*expressions)}

    def _negation_op(self, spec, expression):
        return {'$not' : expression}
