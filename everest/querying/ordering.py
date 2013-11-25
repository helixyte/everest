"""
Order specification visitor classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""
from everest.entities.utils import slug_from_identifier
from everest.querying.base import CqlExpression
from everest.querying.base import SpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.operators import CQL_ORDER_OPERATORS
from functools import reduce as func_reduce
from operator import and_ as and_operator
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['BubbleSorter',
           'CqlOrderExpression',
           'CqlOrderSpecificationVisitor',
           'OrderSpecificationVisitor',
           'RepositoryOrderSpecificationVisitor',
           'Sorter',
           'SorterTemplate',
           ]


class Sorter(object):
    _order = None

    def __init__(self, order):
        if self.__class__ is Sorter:
            raise NotImplementedError('Abstract class')
        self._order = order

    def sort(self, lst, lo=None, hi=None):
        raise NotImplementedError('Abstract method')

    def set_order(self, order):
        self._order = order


class SorterTemplate(Sorter):
    def __init__(self, order):
        if self.__class__ is SorterTemplate:
            raise NotImplementedError('Abstract class')
        Sorter.__init__(self, order)

    def sort(self, lst, lo=None, hi=None):
        lo = 0 if lo is None else lo
        hi = (len(lst) - 1) if hi is None else hi
        if lo < hi:
            s = self._split(lst, lo, hi)
            self.sort(lst, lo, s - 1)
            self.sort(lst, s, hi)
            self._join(lst, lo, s, hi)

    def _split(self, lst, lo, hi):
        raise NotImplementedError('Abstract method')

    def _join(self, lst, lo, s, hi):
        raise NotImplementedError('Abstract method')


class BubbleSorter(SorterTemplate):
    def __init__(self, order):
        SorterTemplate.__init__(self, order)

    def _split(self, lst, lo, hi):
        j = hi
        while lo < j:
            if self._order.lt(lst[j], lst[j - 1]):
                temp = lst[j]
                lst[j] = lst[j - 1]
                lst[j - 1] = temp
            j -= 1
        return lo + 1

    def _join(self, lst, low_index, split_index, high_index):
        pass


class OrderSpecificationVisitor(SpecificationVisitor):
    """
    Base class for order specification visitors.
    """
    def _asc_op(self, spec):
        raise NotImplementedError('Abstract method.')

    def _desc_op(self, spec):
        raise NotImplementedError('Abstract method.')


class CqlOrderExpression(CqlExpression):
    """
    CQL expression representing an order criterion.
    """
    __cql_format = '%(attr)s:%(op)s'

    def __init__(self, attr_name, op_name):
        CqlExpression.__init__(self)
        self.attr_name = attr_name
        self.op_name = op_name

    def _as_string(self):
        return self.__cql_format % dict(attr=self.attr_name,
                                        op=self.op_name)


@implementer(IOrderSpecificationVisitor)
class CqlOrderSpecificationVisitor(OrderSpecificationVisitor):
    """
    Order specification visitor building a CQL expression.
    """
    def _conjunction_op(self, spec, *expressions):
        res = func_reduce(and_operator, expressions)
        return res

    def _asc_op(self, spec):
        return CqlOrderExpression(self.__preprocess_attribute(spec.attr_name),
                                  CQL_ORDER_OPERATORS.ASCENDING.name)

    def _desc_op(self, spec):
        return CqlOrderExpression(self.__preprocess_attribute(spec.attr_name),
                                  CQL_ORDER_OPERATORS.DESCENDING.name)

    def __preprocess_attribute(self, attr_name):
        return slug_from_identifier(attr_name)


class RepositoryOrderSpecificationVisitor(OrderSpecificationVisitor): # pylint: disable=W0223
    """
    Specification visitors that build order expressions for a repository
    backend.
    """
    def __init__(self, entity_class):
        OrderSpecificationVisitor.__init__(self)
        self._entity_class = entity_class

    def order_query(self, query):
        """
        Returns the given query ordered by this visitor's order expression.
        """
        return query.order(self.expression)
