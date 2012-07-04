"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from everest.querying.orderparser import parse_order
from everest.testing import BaseTestCase
from pyparsing import ParseException

__docformat__ = 'reStructuredText en'
__all__ = ['OrderSpecificationParserTestCase',
           ]


class OrderSpecificationParserTestCase(BaseTestCase):

    def set_up(self):
        self.parser = parse_order

    def test_no_criterion_query(self):
        expr = ''
        self.assert_raises(ParseException, self.parser, expr)

    def test_one_sort_order(self):
        expr = 'name:asc'
        result = self.parser(expr)
        self.assert_equal(len(result.criteria), 1)
        order = result.criteria[0]
        self.assert_equal(order.name, 'name')
        self.assert_equal(order.operator, 'asc')

    def test_one_sort_order_reversed(self):
        expr = 'name:desc'
        result = self.parser(expr)
        self.assert_equal(len(result.criteria), 1)
        order = result.criteria[0]
        self.assert_equal(order.name, 'name')
        self.assert_equal(order.operator, 'desc')

    def test_two_sort_order_left_reversed(self):
        expr = 'name:desc~age:asc'
        result = self.parser(expr)
        self.assert_equal(len(result.criteria), 2)
        first_order, second_order = result.criteria
        self.assert_equal(first_order.name, 'name')
        self.assert_equal(first_order.operator, 'desc')
        self.assert_equal(second_order.name, 'age')
        self.assert_equal(second_order.operator, 'asc')
