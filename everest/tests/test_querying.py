"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.querying.base import CqlExpressionList
from everest.querying.filtering import CqlFilterExpression
from everest.querying.operators import GREATER_OR_EQUALS
from everest.querying.operators import GREATER_THAN
from everest.querying.operators import LESS_OR_EQUALS
from everest.querying.operators import LESS_THAN
from everest.testing import Pep8CompliantTestCase
from operator import and_ as operator_and
from operator import or_ as operator_or

__docformat__ = 'reStructuredText en'
__all__ = ['QueryingTestCase',
           ]


class QueryingTestCase(Pep8CompliantTestCase):
    def test_cql_expression_combination(self):
        cql_expr = CqlFilterExpression('foo', LESS_THAN.name, '1')
        expr_str = 'foo:less-than:1'
        self.assert_equal(str(cql_expr), expr_str)
        cql_exprs = CqlExpressionList([cql_expr])
        and_expr_str = '~'.join((expr_str, expr_str))
        self.assert_equal(str(operator_and(cql_expr, cql_expr)),
                          and_expr_str)
        self.assert_equal(str(operator_and(cql_expr, cql_exprs)),
                          and_expr_str)
        self.assert_raises(TypeError, operator_and, cql_expr, None)
        self.assert_equal(str(operator_and(cql_exprs, cql_expr)),
                          and_expr_str)
        self.assert_equal(str(operator_and(cql_exprs, cql_exprs)),
                          and_expr_str)
        self.assert_raises(TypeError, operator_and, cql_exprs, None)
        cql_or_expr = operator_or(cql_expr, cql_expr)
        self.assert_equal(str(cql_or_expr), "%s,1" % expr_str)
        self.assert_raises(ValueError, operator_or, cql_expr,
                           CqlFilterExpression('bar', GREATER_THAN.name, '1'))

    def test_cql_expression_negation(self):
        inv_expr = ~CqlFilterExpression('foo', LESS_THAN.name, '1')
        self.assert_equal(inv_expr.op_name, GREATER_OR_EQUALS.name)
        inv_inv_expr = ~inv_expr
        self.assert_equal(inv_inv_expr.op_name, LESS_THAN.name)
        inv_expr = ~CqlFilterExpression('foo', GREATER_THAN.name, '1')
        self.assert_equal(inv_expr.op_name, LESS_OR_EQUALS.name)
        inv_inv_expr = ~inv_expr
        self.assert_equal(inv_inv_expr.op_name, GREATER_THAN.name)
        invalid_expr = CqlFilterExpression('foo', 'bar', '1')
        self.assert_raises(ValueError, invalid_expr.__invert__)
