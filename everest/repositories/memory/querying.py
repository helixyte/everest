"""
Querying functionality for the memory repository.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.base import ExpressionBuilderMixin
from everest.querying.base import Query
from everest.querying.base import RepositoryQuery
from everest.querying.filtering import RepositoryFilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.ordering import RepositoryOrderSpecificationVisitor
from itertools import islice
from zope.interface import implementer # pylint: disable=E0611,F0401
import functools

__docformat__ = 'reStructuredText en'
__all__ = ['EvalFilterExpression',
           'EvalOrderExpression',
           'MemoryQuery',
           'MemoryRepositoryQuery',
           'ObjectFilterSpecificationVisitor',
           'ObjectOrderSpecificationVisitor',
           ]


class EvalFilterExpression(object):
    """
    Evaluation filter expression.
    """
    def __init__(self, spec):
        self.__spec = spec

    def __call__(self, entities):
        return self.__evaluator(self.__spec, entities)

    def __and__(self, other):
        return EvalFilterExpression(self.__spec & other.__spec) # pylint: disable=W0212

    def __or__(self, other):
        return EvalFilterExpression(self.__spec | other.__spec) # pylint: disable=W0212

    def __invert__(self):
        return EvalFilterExpression(~self.__spec)

    @staticmethod
    def __evaluator(spec, entities):
        return (ent for ent in entities if spec.is_satisfied_by(ent))


class EvalOrderExpression(object):
    """
    Evaluation order expression.
    """
    def __init__(self, spec):
        self.__spec = spec

    def __call__(self, entities):
        return sorted(entities, key=functools.cmp_to_key(self.__spec.cmp))

    def __and__(self, other):
        return EvalOrderExpression(self.__spec & other.__spec) # pylint: disable=W0212


class EvalExpressionBuilderMixin(ExpressionBuilderMixin):
    """
    Mixin class for building eval filter and order expressions from
    specifications.
    """
    expression_kind = EXPRESSION_KINDS.EVAL


class MemoryQuery(EvalExpressionBuilderMixin, Query):
    """
    Query operating on objects held in a sequence object.
    """
    def __init__(self, entity_class, entities):
        Query.__init__(self, entity_class)
        self.__entities = entities

    def __iter__(self):
        ents = iter(self.__entities)
        if not self._filter_expr is None:
            ents = self._filter_expr(ents)
        if not self._order_expr is None:
            # Ordering always involves a copy and conversion to a list, so
            # we have to wrap in an iterator.
            ents = iter(self._order_expr(ents))
        if not self._slice_key is None:
            ents = islice(ents, self._slice_key.start, self._slice_key.stop)
        return ents

    def count(self):
        ents = iter(self.__entities)
        if not self._filter_expr is None:
            ents = self._filter_expr(ents)
        return len(list(ents))


class MemoryRepositoryQuery(EvalExpressionBuilderMixin, RepositoryQuery):
    """
    Query operating on objects kept in a memory repository.
    """
    pass


@implementer(IFilterSpecificationVisitor)
class ObjectFilterSpecificationVisitor(RepositoryFilterSpecificationVisitor):
    """
    Filter specification visitor building an evaluator for in-memory
    filtering.
    """
    def _conjunction_op(self, spec, *expressions):
        return EvalFilterExpression(spec)

    def _disjunction_op(self, spec, *expressions):
        return EvalFilterExpression(spec)

    def _negation_op(self, spec, expression):
        return EvalFilterExpression(spec)

    def _starts_with_op(self, spec):
        return EvalFilterExpression(spec)

    def _ends_with_op(self, spec):
        return EvalFilterExpression(spec)

    def _contains_op(self, spec):
        return EvalFilterExpression(spec)

    def _contained_op(self, spec):
        return EvalFilterExpression(spec)

    def _equal_to_op(self, spec):
        return EvalFilterExpression(spec)

    def _less_than_op(self, spec):
        return EvalFilterExpression(spec)

    def _less_than_or_equal_to_op(self, spec):
        return EvalFilterExpression(spec)

    def _greater_than_op(self, spec):
        return EvalFilterExpression(spec)

    def _greater_than_or_equal_to_op(self, spec):
        return EvalFilterExpression(spec)

    def _in_range_op(self, spec):
        return EvalFilterExpression(spec)


@implementer(IOrderSpecificationVisitor)
class ObjectOrderSpecificationVisitor(RepositoryOrderSpecificationVisitor):
    """
    Order specification visitor building an evaluator for in-memory
    ordering.
    """
    def _conjunction_op(self, spec, *expressions):
        return lambda entities: sorted(entities,
                                       key=functools.cmp_to_key(spec.cmp))

    def _asc_op(self, spec):
        return lambda entities: sorted(entities,
                                       key=functools.cmp_to_key(spec.cmp))

    def _desc_op(self, spec):
        return lambda entities: sorted(entities,
                                       key=functools.cmp_to_key(spec.cmp))
