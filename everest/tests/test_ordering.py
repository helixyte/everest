"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from everest.querying.ordering import BubbleSorter
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.specifications import DescendingOrderSpecification
from everest.repositories.rdb import SqlOrderSpecificationVisitor
from everest.testing import Pep8CompliantTestCase
from everest.tests.simple_app.entities import FooEntity
from mock import MagicMock
import random

__docformat__ = 'reStructuredText en'
__all__ = ['AscendingOrderSpecificationTestCase',
           'ConjunctionOrderSpecificationTestCase',
           'ReverseOrderSpecificationTestCase',
           'SorterTestCase',
           'SqlOrderingSpecificationVisitorTestCase',
           ]


class Person(object):

    name = None
    age = None

    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __repr__(self):
        str_format = '<%s name: %s, age: %s>'
        params = (self.__class__.__name__, self.name, self.age)
        return str_format % params


class OrderSpecificationTestCase(Pep8CompliantTestCase):

    def set_up(self):
        self.person_a1 = Person('John', 33)
        self.person_a2 = Person('John', 44)
        self.person_b1 = Person('Mike', 55)
        self.person_b2 = Person('Mike', 66)

    def create_asc_order(self, attr_name):
        return AscendingOrderSpecification(attr_name)

    def create_desc_order(self, attr_name):
        return DescendingOrderSpecification(attr_name)


class AscendingOrderSpecificationTestCase(OrderSpecificationTestCase):

    def test_order_is_satisfied(self):
        order = self.create_asc_order('age')
        self.assert_true(order.lt(self.person_a1, self.person_b1))

    def test_order_is_not_satisfied(self):
        order = self.create_asc_order('age')
        self.assert_false(order.lt(self.person_b1, self.person_a1))


class ReverseOrderSpecificationTestCase(OrderSpecificationTestCase):

    def test_order_is_satisfied(self):
        order = self.create_desc_order('age')
        self.assert_true(order.lt(self.person_b1, self.person_a1))

    def test_order_is_not_satisfied(self):
        order = self.create_desc_order('age')
        self.assert_false(order.lt(self.person_a1, self.person_b1))


class ConjunctionOrderSpecificationTestCase(OrderSpecificationTestCase):

    def test_order_is_satisfied(self):
        order = self.create_asc_order('name') & self.create_asc_order('age')
        self.assert_true(order.lt(self.person_a1, self.person_b1))

    def test_order_is_not_satisfied(self):
        order = self.create_asc_order('name') & self.create_desc_order('age')
        self.assert_false(order.lt(self.person_b1, self.person_a1))

    def test_reverse_order_is_satisfied(self):
        order = self.create_asc_order('name') & self.create_desc_order('age')
        self.assert_true(order.lt(self.person_a2, self.person_a1))

    def test_reverse_order_is_not_satisfied(self):
        order = self.create_asc_order('name') & self.create_desc_order('age')
        self.assert_false(order.lt(self.person_a1, self.person_a2))


class SorterTestCase(Pep8CompliantTestCase):
    andrew11 = None
    bill22 = None
    john33 = None
    john44 = None
    mike55 = None
    mike66 = None
    persons = None

    def set_up(self):
        self.andrew11 = Person('Andrew', 11)
        self.bill22 = Person('Bill', 22)
        self.john33 = Person('John', 33)
        self.john44 = Person('John', 44)
        self.mike55 = Person('Mike', 55)
        self.mike66 = Person('Mike', 66)
        self.persons = [self.andrew11, self.bill22, self.john33, self.john44,
                        self.mike55, self.mike66]
        random.shuffle(self.persons)

    def tear_down(self):
        pass

    def create_asc_order(self, attr_name):
        return AscendingOrderSpecification(attr_name)

    def create_desc_order(self, attr_name):
        return DescendingOrderSpecification(attr_name)

    def get_persons_ordered_by_name_and_age(self):
        return [self.andrew11, self.bill22, self.john33, self.john44,
                self.mike55, self.mike66]

    def get_persons_ordered_by_name_reversed_and_age(self):
        return [self.mike55, self.mike66, self.john33, self.john44,
                self.bill22, self.andrew11]

    def get_persons_ordered_by_name_and_age_reversed(self):
        return [self.andrew11, self.bill22, self.john44, self.john33,
                self.mike66, self.mike55]

    def get_persons_reversed_ordered_by_name_and_age(self):
        return [self.mike66, self.mike55, self.john44, self.john33,
                self.bill22, self.andrew11]

    def test_bubble_sorter(self):
        order = self.create_asc_order('name') & self.create_asc_order('age')
        sorter = BubbleSorter(order)
        sorter.sort(self.persons)
        self.assert_equal(self.persons,
                          self.get_persons_ordered_by_name_and_age())

        order = self.create_desc_order('name') & self.create_asc_order('age')
        sorter.set_order(order)
        sorter.sort(self.persons)
        self.assert_equal(self.persons,
                          self.get_persons_ordered_by_name_reversed_and_age())

        order = self.create_asc_order('name') & self.create_desc_order('age')
        sorter.set_order(order)
        sorter.sort(self.persons)
        self.assert_equal(self.persons,
                          self.get_persons_ordered_by_name_and_age_reversed())

        order = self.create_desc_order('name') & self.create_desc_order('age')
        sorter.set_order(order)
        sorter.sort(self.persons)
        self.assert_equal(self.persons,
                          self.get_persons_reversed_ordered_by_name_and_age())


class SqlOrderingSpecificationVisitorTestCase(Pep8CompliantTestCase):
    class MySqlOrderSpecificationVisitor(SqlOrderSpecificationVisitor):
        def _asc_op(self, spec):
            return lambda value: None

    def test_custom_clause(self):
        obj = object()
        spec = AscendingOrderSpecification('id')
        join_map = {'id':[obj]}
        def get_item(key):
            return join_map[key]
        def contains(key):
            return key in join_map
        mock_join_map = MagicMock(spec=dict)
        mock_join_map.__getitem__.side_effect = get_item
        mock_join_map.__contains__.side_effect = contains
        visitor = self.MySqlOrderSpecificationVisitor(FooEntity,
                                                      custom_join_clauses=
                                                                mock_join_map)
        visitor.visit_nullary(spec)
        mock_join_map.__getitem__.assert_called_with('id')
