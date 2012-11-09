"""
Order specification builder, visitor, director classes.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

See also:

http://cnx.org/content/m17309/latest/

D. Nguyen and S. Wong, "Design Patterns for Sorting," SIGCSE Bulletin 33:1,
    March 2001, 263-267.

S. Merritt, "An Inverted Taxonomy of Sorting Algorithms" Comm. of the ACM,
    Jan. 1985, Volume 28, Number 1, pp. 96-99.

Created on Jul 5, 2011.
"""
from everest.entities.attributes import EntityAttributeKinds
from everest.entities.utils import slug_from_identifier
from everest.orm import OrderClauseList
from everest.querying.base import CqlExpression
from everest.querying.base import SpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.operators import CQL_ORDER_OPERATORS
from everest.querying.utils import OrmAttributeInspector
from operator import and_ as and_operator
from sqlalchemy.sql.expression import ClauseList
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['BubbleSorter',
           'EvalOrderSpecificationVisitor',
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

    def _asc_op(self, attr_name):
        raise NotImplementedError('Abstract method.')

    def _desc_op(self, attr_name):
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


class CqlOrderSpecificationVisitor(OrderSpecificationVisitor):
    """
    Order specification visitor building a CQL expression.
    """

    implements(IOrderSpecificationVisitor)

    def _conjunction_op(self, spec, *expressions):
        res = reduce(and_operator, expressions)
        return res

    def _asc_op(self, spec):
        return CqlOrderExpression(self.__preprocess_attribute(spec.attr_name),
                                  CQL_ORDER_OPERATORS.ASCENDING.name)

    def _desc_op(self, spec):
        return CqlOrderExpression(self.__preprocess_attribute(spec.attr_name),
                                  CQL_ORDER_OPERATORS.DESCENDING.name)

    def __preprocess_attribute(self, attr_name):
        return slug_from_identifier(attr_name)


class SqlOrderSpecificationVisitor(OrderSpecificationVisitor):
    """
    Order specification visitor building a SQL expression.
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


class EvalOrderSpecificationVisitor(OrderSpecificationVisitor):
    """
    Order specification visitor building an evaluator for in-memory 
    ordering.
    """

    implements(IOrderSpecificationVisitor)

    def _conjunction_op(self, spec, *expressions):
        return lambda entities: sorted(entities, cmp=spec.cmp)

    def _asc_op(self, spec):
        return lambda entities: sorted(entities, cmp=spec.cmp)

    def _desc_op(self, spec):
        return lambda entities: sorted(entities, cmp=spec.cmp)
