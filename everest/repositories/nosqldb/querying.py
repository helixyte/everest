"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 29, 2013.
"""
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.base import ExpressionBuilderMixin
from everest.querying.base import RepositoryQuery
from everest.querying.filtering import RepositoryFilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.operators import CONTAINS
from everest.querying.operators import EQUAL_TO
from everest.querying.operators import IN_RANGE
from everest.querying.ordering import RepositoryOrderSpecificationVisitor
from everest.repositories.nosqldb.utils import NoSqlAttributeInspector
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.utils import get_root_collection
from functools import reduce as func_reduce
from itertools import chain
from pymongo import ASCENDING
from pymongo import DESCENDING
from pyramid.compat import string_types
from zope.interface import implementer # pylint: disable=E0611,F0401
import re

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlFilterSpecificationVisitor',
           'NoSqlOrderSpecificationVisitor',
           'NoSqlQuery',
           ]


class NoSqlExpressionBuilderMixin(ExpressionBuilderMixin):
    """
    Mixin class for building Mongo DB filter and order expressions from
    specifications.
    """
    expression_kind = EXPRESSION_KINDS.NOSQL


class NoSqlQuery(NoSqlExpressionBuilderMixin, RepositoryQuery):
    """
    Query operating on objects held in a NoSQL repository.
    """
    def count(self):
        return self._repository.count(self._entity_class,
                                      filter_expression=self._filter_expr)


@implementer(IFilterSpecificationVisitor)
class NoSqlFilterSpecificationVisitor(RepositoryFilterSpecificationVisitor):
    __id_func_literal = 'function(c) { return c._id; }'
    __nested_terminal_query_template = \
        "db['%(root_collection_name)s'].find(%(terminal_expression)s)"
    __nested_member_query_template = \
        "db['%%(root_collection_name)s'].find({'%%(nested_attr_name)s.$id'" \
        " : {'$in' : %%%%(nested_expression)s.map(%s)}})" % __id_func_literal
    __nested_collection_query_template = \
        "db['%%(root_collection_name)s'].find({'%%(nested_attr_name)s'" \
        " : {'$elemMatch' : {'$id' : { '$in' : " \
        "%%%%(nested_expression)s.map(%s)}}}}" % __id_func_literal

    def _starts_with_op(self, spec):
        attr_value = re.compile('^%s.*$' % spec.attr_value)
        return self.__build('$regex', spec.attr_name, attr_value)

    def _ends_with_op(self, spec):
        attr_value = re.compile('^.*%s$' % spec.attr_value)
        return self.__build('$regex', spec.attr_name, attr_value)

    def _contains_op(self, spec):
        if isinstance(spec.attr_value, string_types):
            attr_value = re.compile('^.*%s.*' % spec.attr_value)
            expr = self.__build('$regex', spec.attr_name, attr_value)
        else:
            expr = self.__build('$exists', spec.attr_name, spec.attr_value)
        return expr

    def _contained_op(self, spec):
        return self.__build('$in', spec.attr_name, spec.attr_value)

    def _equal_to_op(self, spec):
        return self.__build(None, spec.attr_name, spec.attr_value)

    def _less_than_op(self, spec):
        return self.__build('$lt', spec.attr_name, spec.attr_value)

    def _less_than_or_equal_to_op(self, spec):
        return self.__build('$lte', spec.attr_name, spec.attr_value)

    def _greater_than_op(self, spec):
        return self.__build('$gt', spec.attr_name, spec.attr_value)

    def _greater_than_or_equal_to_op(self, spec):
        return self.__build('$gte', spec.attr_name, spec.attr_value)

    def _in_range_op(self, spec):
        return self.__build(IN_RANGE.name, spec.attr_name, spec.attr_value)

    def _conjunction_op(self, spec, *expressions):
        return {'$and' : list(expressions)}

    def _disjunction_op(self, spec, *expressions):
        return {'$or' : list(expressions)}

    def _negation_op(self, spec, expression):
        if spec.wrapped_spec.operator == EQUAL_TO:
            (key, val), = expression.items()
            expr = {key:{'$ne':val}}
        elif spec.wrapped_spec.operator == CONTAINS \
             and isinstance(spec.wrapped_spec.attr_value, string_types):
            # The $not operator does not work with the $regex operator, so
            # we actually have to invert the regular expression.
            (key, valexpr), = expression.items()
            inv_regex = re.compile('^(?!%s)' % valexpr['$regex'].pattern[1:])
            expression[key] = {'$regex' : inv_regex}
            expr = expression
        else:
            (key, val), = expression.items()
            expr = {key:{'$not':val}}
        return expr

    def __build(self, op, attr_name, attr_value):
        infos = NoSqlAttributeInspector.inspect(self._entity_class,
                                                attr_name)
        is_nested = len(infos) > 1
        parent_type = self._entity_class
        exprs = []
        for info in infos[:-1]:
            nested_attr_kind, nested_attr_type, nested_attr_name = info
            root_coll = get_root_collection(parent_type)
            templ_map = dict(root_collection_name=root_coll.__name__,
                             nested_attr_name=nested_attr_name,
                             )
            if nested_attr_kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
                expr = self.__nested_member_query_template % templ_map
            else: # RESOURCE_ATTRIBUTE_KINDS.COLLECTION
                expr = self.__nested_collection_query_template % templ_map
            exprs.insert(0, expr)
            parent_type = nested_attr_type
        terminal_attr_name = infos[-1][-1]
        expr = self.__prepare_criterion(terminal_attr_name, op, attr_value)
        if is_nested:
            # FIXME: Need to handle value -> string conversion here.
            root_coll = get_root_collection(parent_type)
            templ_map = dict(root_collection_name=root_coll.__name__,
                             terminal_expression=str(expr))
            terminal_expr = self.__nested_terminal_query_template % templ_map
            expr = func_reduce(lambda g, h: h % dict(nested_expression=g),
                               exprs, terminal_expr)
        return expr

    def __prepare_criterion(self, attr, op, val):
        if op in (None, '$exists'):
            if IMemberResource.providedBy(val): # pylint: disable=E1101
                attr = '%s.$id' % attr
                val = getattr(val.get_entity(), '_id')
            if op is None:
                crit = {attr:val}
            else:
                crit = {attr:{op:val}}
        elif op == '$in':
            if ICollectionResource.providedBy(val): # pylint: disable=E1101
                val = [getattr(mb.get_entity(), '_id') for mb in val]
                attr = '%s.$id' % attr
            crit = {attr:{op:val}}
        elif op == IN_RANGE.name:
            from_value, to_value = val
            crit = {'$and':[{attr:{'$gte':from_value}},
                            {attr:{'$lte':to_value}}]}
        else:
            crit = {attr:{op:val}}
        return crit


@implementer(IOrderSpecificationVisitor)
class NoSqlOrderSpecificationVisitor(RepositoryOrderSpecificationVisitor):
    def _asc_op(self, spec):
        return [(spec.attr_name, ASCENDING)]

    def _desc_op(self, spec):
        return [(spec.attr_name, DESCENDING)]

    def _conjunction_op(self, spec, *expressions):
        return list(chain(*expressions))
