"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 2, 2011.
"""

import logging
from pyparsing import ParseException

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


class Operator(object):
    name = None


class UnaryOperator(Operator):
    @staticmethod
    def apply(value):
        raise NotImplementedError('Abstract method.')


class BinaryOperator(Operator):

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

    #: The operator for this specification. This needs to be set to a subclass 
    #: of :class:`everest.querying.operators.Operator` in derived classes. 
    operator = None

    def __init__(self):
        if self.__class__ is Specification:
            raise NotImplementedError('Abstract class')

    def accept(self, visitor):
        """
        Sends a request to a visitor.
        
        This triggers visits of this specification and all other dependent
        specifications which in turn dispatch appropriate visiting operations.

        :param visitor: a visitor that packages related operations
        :type visitor: :class:`everest.querying.base.SpecificationVisitor`
        """
        raise NotImplementedError('Abstract method')


class SpecificationDirector(object):
    """
    Abstract base class for specification directors.
    
    A specification director coordinates a specification parser and a 
    specification builder.
    """

    def __init__(self, parser, builder):
        self.__parser = parser
        self.__builder = builder
        self.__errors = []

    def construct(self, expression):
        """
        Constructs a specification (using the builder passed to the 
        constructor) from the result of parsing the given expression (using
        the parser passed to the constructor).
        """
        try:
            self._logger.debug('Expression received: %s' % expression)
            result = self.__parser(expression)
        except ParseException, err:
            # FIXME: show better error messages # pylint: disable=W0511
            self.__errors.append('Expression parameters have errors. %s' % err)
        else:
            self._process_parse_result(result)

    def has_errors(self):
        """
        Checks if the director encountered errors during the last call to 
        :method:`construct`.
        """
        return len(self.__errors) > 0

    def get_errors(self):
        """
        Returns the errors that were encountered during the last call to
        :method:`construct`
        """
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


class SpecificationVisitor(object):
    """
    Base class for all specification visitors.
    """
    def __init__(self):
        self.__expression_stack = []

    def visit(self, spec):
        """
        Visits the given specification with a dispatched visiting operation.
        """
        op = self.__get_op_func(spec.operator.name)
        self.__expression_stack.append(op(spec))

    def visit_last(self, spec):
        """
        Visits the given specification with a dispatched visiting operation, 
        passing the last generated expression as additional argument.
        """
        op = self.__get_op_func(spec.operator.name)
        expr = self.__expression_stack.pop()
        self.__expression_stack.append(op(spec, expr))

    def visit_last_two(self, spec):
        """
        Visits the given specification with a dispatched visiting operation, 
        passing the last two generated expressions as additional argument.
        """
        op = self.__get_op_func(spec.operator.name)
        right_expr = self.__expression_stack.pop()
        left_expr = self.__expression_stack.pop()
        self.__expression_stack.append(op(spec, left_expr, right_expr))

    def _conjunction_op(self, *expressions):
        raise NotImplementedError('Abstract method.')

    def _push(self, expr):
        self.__expression_stack.append(expr)

    def _pop(self):
        return self.__expression_stack.pop()

    @property
    def expression(self):
        """
        Returns the expression constructed by this visitor.
        """
        return self.__expression_stack.pop()

    def __get_op_func(self, op_name):
        # Visitor function dispatch using the operator name.
        return getattr(self, '_%s_op' % op_name.replace('-', '_'))
