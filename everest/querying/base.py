"""
Querying operators, expressions, visitors, builders, directors.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 2, 2011.
"""
from everest.entities.utils import identifier_from_slug
from everest.querying.interfaces import ISpecification
from everest.querying.interfaces import ISpecificationVisitor
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['BinaryOperator',
           'CqlExpression',
           'CqlExpressionList',
           'EXPRESSION_KINDS',
           'NullaryOperator',
           'Operator',
           'Specification',
           'SpecificationVisitor',
           'SpecificationVisitorBase',
           'UnaryOperator',
           ]


class EXPRESSION_KINDS(object):
    CQL = 'CQL'
    SQL = 'SQL'
    EVAL = 'EVAL'


class Operator(object):
    """
    Base class for querying operators.
    """
    #: The name of the operator. To be specified in derived classes.
    name = None
    #: The arity (number of arguments required) of the operator. To be 
    #: specified in derived classes.
    arity = None


class NullaryOperator(Operator):
    """
    Nullary querying operator.
    """
    arity = 0

    @staticmethod
    def apply():
        raise NotImplementedError('Abstract method.')



class UnaryOperator(Operator):
    """
    Unary querying operator.
    """
    arity = 1

    @staticmethod
    def apply(value):
        raise NotImplementedError('Abstract method.')


class BinaryOperator(Operator):
    """
    Binary querying operator.
    """
    arity = 2

    @staticmethod
    def apply(value, ref_value):
        raise NotImplementedError('Abstract method.')


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


class Specification(object):
    """
    Abstract base classs for all specifications.
    """

    implements(ISpecification)

    operator = None

    def __init__(self):
        if self.__class__ is Specification:
            raise NotImplementedError('Abstract class')

    def accept(self, visitor):
        raise NotImplementedError('Abstract method')


class SpecificationVisitorBase(object):
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


class SpecificationVisitor(SpecificationVisitorBase):
    """
    Base class for all specification visitors.
    """

    implements(ISpecificationVisitor)

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
