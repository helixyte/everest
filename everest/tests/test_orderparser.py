"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from everest.querying.operators import ASCENDING
from everest.querying.operators import DESCENDING
from everest.querying.orderparser import parse_order
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.specifications import ConjunctionOrderSpecification
from everest.querying.specifications import DescendingOrderSpecification
from everest.testing import TestCaseWithConfiguration
from pyparsing import ParseException

__docformat__ = 'reStructuredText en'
__all__ = ['OrderParserTestCase',
           ]


class OrderParserTestCase(TestCaseWithConfiguration):
    def set_up(self):
        TestCaseWithConfiguration.set_up(self)
        self.parser = parse_order

    def test_no_criterion_query(self):
        expr = ''
        self.assert_raises(ParseException, self.parser, expr)

    def test_one_sort_order(self):
        expr = 'name:asc'
        result = self.parser(expr)
        self.assert_true(isinstance(result, AscendingOrderSpecification))
        self.assert_equal(result.attr_name, 'name')
        self.assert_equal(result.operator, ASCENDING)

    def test_one_sort_order_reversed(self):
        expr = 'name:desc'
        result = self.parser(expr)
        self.assert_true(isinstance(result, DescendingOrderSpecification))
        self.assert_equal(result.attr_name, 'name')
        self.assert_equal(result.operator, DESCENDING)

    def test_two_sort_order_left_reversed(self):
        expr = 'name:desc~age:asc'
        result = self.parser(expr)
        self.assert_true(isinstance(result, ConjunctionOrderSpecification))
        self.assert_true(isinstance(result.left,
                                    DescendingOrderSpecification))
        self.assert_true(isinstance(result.right,
                                    AscendingOrderSpecification))
        self.assert_equal(result.left.attr_name, 'name')
        self.assert_equal(result.left.operator, DESCENDING)
        self.assert_equal(result.right.attr_name, 'age')
        self.assert_equal(result.right.operator, ASCENDING)
