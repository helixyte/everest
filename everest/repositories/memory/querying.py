"""

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.querying.filtering import FilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.ordering import OrderSpecificationVisitor
from functools import partial
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ObjectFilterSpecificationVisitor',
           'ObjectOrderSpecificationVisitor',
           ]


@implementer(IFilterSpecificationVisitor)
class ObjectFilterSpecificationVisitor(FilterSpecificationVisitor):
    """
    Filter specification visitor building an evaluator for in-memory
    filtering.
    """

    @staticmethod
    def __evaluator(spec, entities):
        return [ent for ent in entities if spec.is_satisfied_by(ent)]

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


@implementer(IOrderSpecificationVisitor)
class ObjectOrderSpecificationVisitor(OrderSpecificationVisitor):
    """
    Order specification visitor building an evaluator for in-memory
    ordering.
    """

    def _conjunction_op(self, spec, *expressions):
        return lambda entities: sorted(entities, cmp=spec.cmp)

    def _asc_op(self, spec):
        return lambda entities: sorted(entities, cmp=spec.cmp)

    def _desc_op(self, spec):
        return lambda entities: sorted(entities, cmp=spec.cmp)
