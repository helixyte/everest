"""
Base classes and constants for the querying subsystem.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 2, 2011.
"""
from everest.entities.utils import identifier_from_slug
from everest.exceptions import MultipleResultsException
from everest.exceptions import NoResultsException
from everest.querying.interfaces import IQuery
from everest.querying.interfaces import ISpecificationVisitor
from everest.querying.specifications import eq
from everest.querying.specifications import order
from everest.utils import generative
from everest.utils import get_filter_specification_visitor
from everest.utils import get_order_specification_visitor
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['CqlExpression',
           'CqlExpressionList',
           'EXPRESSION_KINDS',
           'SpecificationVisitor',
           'SpecificationExpressionHolder',
           ]


class EXPRESSION_KINDS(object):
    """
    Supported expression kinds.
    """
    CQL = 'CQL'
    SQL = 'SQL'
    EVAL = 'EVAL'
    NOSQL = 'NOSQL'


class CqlExpression(object):
    """
    Single CQL expression.

    CQL expressions can be converted to a string and support the conjunction
    (AND) operation.
    """
    def __str__(self):
        return self._as_string()

    def __and__(self, other):
        if isinstance(other, CqlExpression):
            res = CqlExpressionList([self, other])
        elif isinstance(other, CqlExpressionList):
            res = CqlExpressionList([self] + other.expressions)
        else:
            raise TypeError("unsupported operand type(s) for &: "
                            "'CqlExpression' and '%s'" % type(other))
        return res

    def _as_string(self):
        raise NotImplementedError('Abstract method.')


class CqlExpressionList(object):
    """
    List of CQL expressions.

    Like a single CQL expression, CQL expression lists can be converted to a
    string and joined with the conjunction (AND) operation.
    """
    __cql_and = '~'

    def __init__(self, expressions):
        self.expressions = expressions

    def __and__(self, other):
        if isinstance(other, CqlExpression):
            res = CqlExpressionList(self.expressions + [other])
        elif isinstance(other, CqlExpressionList):
            res = CqlExpressionList(self.expressions + other.expressions)
        else:
            raise TypeError("unsupported operand type(s) for &: "
                            "'CqlExpression' and '%s'" % type(other))
        return res

    def __str__(self):
        return self.__cql_and.join([str(expr) for expr in self.expressions])


class SpecificationExpressionHolder(object):
    """
    Base class for specification visitors.
    """
    def __init__(self):
        self.__expression_stack = []

    def _push(self, expr):
        self.__expression_stack.append(expr)

    def _pop(self):
        return self.__expression_stack.pop()

    @property
    def expression(self):
        # If we have more than one expression on the stack, traversal of the
        # input specification tree has not finished yet.
        assert len(self.__expression_stack) == 1
        return self.__expression_stack[0]


@implementer(ISpecificationVisitor)
class SpecificationVisitor(SpecificationExpressionHolder):
    """
    Base class for all specification visitors.
    """
    def visit_nullary(self, spec):
        op = self.__get_op_func(spec.operator.name)
        self._push(op(spec))

    def visit_unary(self, spec):
        op = self.__get_op_func(spec.operator.name)
        expr = self._pop()
        self._push(op(spec, expr))

    def visit_binary(self, spec):
        op = self.__get_op_func(spec.operator.name)
        right_expr = self._pop()
        left_expr = self._pop()
        self._push(op(spec, left_expr, right_expr))

    def _conjunction_op(self, spec, *expressions):
        raise NotImplementedError('Abstract method.')

    def __get_op_func(self, op_name):
        # Visitor function dispatch using the operator name.
        return getattr(self, '_%s_op' % identifier_from_slug(op_name))


@implementer(IQuery)
class Query(object):
    """
    Base class for everest queries.
    """
    def __init__(self, entity_class):
        self._entity_class = entity_class
        self._filter_expr = None
        self._order_expr = None
        self._slice_key = None

    def __iter__(self):
        raise NotImplementedError('Abstract method.')

    def count(self):
        raise NotImplementedError('Abstract method.')

    def all(self):
        return list(iter(self))

    def one(self):
        ents = self.all()
        if len(ents) == 0:
            raise NoResultsException('No results found when exactly one '
                                     'was expected.')
        elif len(ents) > 1:
            raise MultipleResultsException('More than one result found '
                                           'where exactly one was expected.')
        return ents[0]

    @generative
    def filter(self, filter_expression):
        if not filter_expression is None and not self._filter_expr is None:
            filter_expression = self._filter_expr & filter_expression
        self._filter_expr = filter_expression
        return self

    def filter_by(self, **kw):
        raise NotImplementedError('Abstract method.')

    @generative
    def order(self, order_expression):
        if not order_expression is None and not self._order_expr is None:
            order_expression = self._order_expr & order_expression
        self._order_expr = order_expression
        return self

    def order_by(self, *args):
        raise NotImplementedError('Abstract method.')

    @generative
    def slice(self, start, stop):
        self._slice_key = slice(start, stop)
        return self


class ExpressionBuilderMixin(object):
    """
    Mixin for query classes using eval filter and order expressions.
    """
    expression_kind = None

    def filter_by(self, **kw):
        spec = eq(**kw)
        visitor_cls = get_filter_specification_visitor(self.expression_kind)
        vst = visitor_cls(self._entity_class)
        spec.accept(vst)
        return vst.filter_query(self)

    def order_by(self, *args):
        spec = order(*args)
        visitor_cls = get_order_specification_visitor(self.expression_kind)
        vst = visitor_cls(self._entity_class)
        spec.accept(vst)
        return vst.order_query(self)


class RepositoryQuery(Query): # still abstract pylint:disable=W0223
    """
    Query operating on objects stored in a repository and loaded through a
    session.
    """
    def __init__(self, entity_class, session, repository):
        Query.__init__(self, entity_class)
        self._session = session
        self._repository = repository

    def __iter__(self):
        repo_ents = self._repository.retrieve(
                                        self._entity_class,
                                        filter_expression=self._filter_expr,
                                        order_expression=self._order_expr,
                                        slice_key=self._slice_key
                                        )
        for repo_ent in repo_ents:
            yield self._session.load(self._entity_class, repo_ent)

    def count(self):
        return sum(1 for _ in self._repository.retrieve(
                                        self._entity_class,
                                        filter_expression=self._filter_expr))

