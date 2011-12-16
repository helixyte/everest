"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 2, 2011.
"""

from everest.querying.interfaces import ISpecification
from everest.querying.interfaces import ISpecificationBuilder
from everest.querying.interfaces import ISpecificationDirector
from everest.querying.interfaces import ISpecificationVisitor
from pyparsing import ParseException
from zope.interface import implements # pylint: disable=E0611,F0401
import logging

__docformat__ = 'reStructuredText en'
__all__ = ['BinaryOperator',
           'CqlExpression',
           'CqlExpressionList',
           'NullaryOperator',
           'Operator',
           'Specification',
           'SpecificationBuilder,'
           'SpecificationDirector',
           'SpecificationVisitor',
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
    name = None


class UnaryOperator(Operator):
    """
    Unary querying operator.
    """
    @staticmethod
    def apply(value):
        raise NotImplementedError('Abstract method.')


class BinaryOperator(Operator):
    """
    Binary querying operator.
    """

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
        return CqlExpressionList([self, other])

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


class SpecificationDirector(object):
    """
    Abstract base class for specification directors.
    """

    implements(ISpecificationDirector)

    def __init__(self, parser, builder):
        self.__parser = parser
        self.__builder = builder
        self.__errors = []

    def construct(self, expression):
        try:
            self._logger.debug('Expression received: %s' % expression)
            result = self.__parser(expression)
        except ParseException, err:
            # FIXME: show better error messages # pylint: disable=W0511
            self.__errors.append('Expression parameters have errors. %s' % err)
        else:
            self._process_parse_result(result)

    def has_errors(self):
        return len(self.__errors) > 0

    def get_errors(self):
        return self.__errors[:]

    def _format_identifier(self, string):
        return string.replace('-', '_')

    @property
    def _logger(self):
        return logging.getLogger(self.__class__.__name__)

    def _get_build_function(self, op_name):
        # Builder function dispatch using the operator name.
        return getattr(self.__builder, 'build_%s' % op_name)

    def _process_parse_result(self, parse_result):
        raise NotImplementedError('Abstract method.')


class SpecificationBuilder(object):
    """
    Base class for specification builders.
    """

    implements(ISpecificationBuilder)

    def __init__(self, spec_factory):
        self._spec_factory = spec_factory
        self.__specification = None

    def _record_specification(self, new_specification):
        """
        Records a built specification. If another spec has been recorded 
        already by the builder, form the conjunction between the previously 
        recorded and the given spec.
        """
        if self.__specification is None:
            self.__specification = new_specification
        else:
            self.__specification = \
                self._spec_factory.create_conjunction(self.__specification,
                                                      new_specification)

    @property
    def specification(self):
        """
        Returns the built specification.
        """
        return self.__specification


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
        return getattr(self, '_%s_op' % op_name.replace('-', '_'))
