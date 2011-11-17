"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 10, 2011.
"""

from everest.db import reset_metadata
from everest.specifications import FilterSpecificationFactory
from everest.specifications import OrderSpecificationFactory
from everest.testing import BaseTestCase
from everest.visitors import CqlFilterSpecificationVisitor
from everest.visitors import CqlOrderSpecificationVisitor
from everest.visitors import QueryOrderSpecificationVisitor
from everest.visitors import QueryFilterSpecificationVisitor
import sqlalchemy as sa
import sqlalchemy.orm as orm


__docformat__ = 'reStructuredText en'
__all__ = ['CompositeCqlFilterSpecificationVisitorTestCase',
           'CompositeQueryFilterSpecificationVisitorTestCase',
           'ManyValueBoundQueryFilterSpecificationVisitorTestCase',
           'NegationCqlFilterSpecificationVisitorTestCase',
           'NegationQueryFilterSpecificationVisitorTestCase',
           'QueryOrderSpecificationSpecificationVisitorTestCase',
           'OrderSpecificationCqlFilterSpecificationVisitorTestCase',
           'ValueBoundCqlFilterSpecificationVisitorTestCase',
           'ValueBoundQueryFilterSpecificationVisitorTestCase',
           ]


class Person(object):
    metadata = None
    id = None
    name = None
    age = None

    def __init__(self, name, age):
        self.name = name
        self.age = age


def setup():
    # Module level setup.
    reset_metadata()
    metadata = sa.MetaData()
    person_table = sa.Table('person', metadata,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String, nullable=False, unique=True),
        sa.Column('age', sa.Integer, nullable=False),
        )
    orm.mapper(Person, person_table)


def teardown():
    # Module level tear down.
    reset_metadata()


# FIXME: Clean up code duplication below # pylint:disable-msg=W0511

class CqlFilterSpecificationVisitorTestCase(BaseTestCase):
    visitor = None
    specs_factory = None

    def set_up(self):
        if Person.metadata is None:
            setup()
        self.visitor = CqlFilterSpecificationVisitor()
        self.specs_factory = FilterSpecificationFactory()


class ValueBoundCqlFilterSpecificationVisitorTestCase(
                                        CqlFilterSpecificationVisitorTestCase):

    def test_visit_value_starts_with(self):
        expected_cql = 'name:starts-with:"Ni"'
        spec = self.specs_factory.create_starts_with('name', 'Ni')
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_ends_with(self):
        expected_cql = 'name:ends-with:"os"'
        spec = self.specs_factory.create_ends_with('name', 'os')
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_contains(self):
        expected_cql = 'name:contains:"iko"'
        spec = self.specs_factory.create_contains('name', 'iko')
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_contained(self):
        expected_cql = 'age:equal-to:22,33,44,55'
        spec = self.specs_factory.create_contained('age', [22, 33, 44, 55])
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_equal_to(self):
        expected_cql = 'name:equal-to:"Nikos"'
        spec = self.specs_factory.create_equal_to('name', 'Nikos')
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_less_than(self):
        expected_cql = 'age:less-than:34'
        spec = self.specs_factory.create_less_than('age', 34)
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_less_or_equals(self):
        expected_cql = 'age:less-than-or-equal-to:34'
        spec = self.specs_factory.create_less_than_or_equal_to('age', 34)
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_greater_than(self):
        expected_cql = 'age:greater-than:34'
        spec = self.specs_factory.create_greater_than('age', 34)
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_greater_or_equals(self):
        expected_cql = 'age:greater-than-or-equal-to:34'
        spec = self.specs_factory.create_greater_than_or_equal_to('age', 34)
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_in_range(self):
        expected_cql = 'age:between:30-40'
        spec = self.specs_factory.create_in_range('age', 30, 40)
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)


class CompositeCqlFilterSpecificationVisitorTestCase(
                                        CqlFilterSpecificationVisitorTestCase):

    def test_visit_conjuction(self):
        expected_cql = 'age:greater-than:34~name:equal-to:"Nikos"'
        left_spec = self.specs_factory.create_greater_than('age', 34)
        right_spec = self.specs_factory.create_equal_to('name', 'Nikos')
        spec = left_spec.and_(right_spec)
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_disjuction(self):
        expected_cql = 'age:equal-to:34,44'
        spec1 = self.specs_factory.create_equal_to('age', 34)
        spec2 = self.specs_factory.create_equal_to('age', 44)
        spec = spec1.or_(spec2)
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_conjuction_with_disjuction(self):
        expected_cql = 'age:equal-to:34,44~name:equal-to:"Nikos","Oliver"'

        specA1 = self.specs_factory.create_equal_to('age', 34)
        specA2 = self.specs_factory.create_equal_to('age', 44)
        specA = specA1.or_(specA2)

        specB1 = self.specs_factory.create_equal_to('name', 'Nikos')
        specB2 = self.specs_factory.create_equal_to('name', 'Oliver')
        specB = specB1.or_(specB2)

        spec = specA.and_(specB)
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)


class NegationCqlFilterSpecificationVisitorTestCase(
                                        CqlFilterSpecificationVisitorTestCase):

    def test_visit_value_not_starts_with(self):
        expected_cql = 'name:not-starts-with:"Ni"'
        spec = self.specs_factory.create_starts_with('name', 'Ni').not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_not_ends_with(self):
        expected_cql = 'name:not-ends-with:"os"'
        spec = self.specs_factory.create_ends_with('name', 'os').not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_not_contains(self):
        expected_cql = 'name:not-contains:"iko"'
        spec = self.specs_factory.create_contains('name', 'iko').not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_not_contained(self):
        expected_cql = 'age:not-equal-to:22,33,44,55'
        spec = self.specs_factory.create_contained('age',
                                                   [22, 33, 44, 55]).not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_not_equal_to(self):
        expected_cql = 'name:not-equal-to:"Nikos"'
        spec = self.specs_factory.create_equal_to('name', 'Nikos').not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_not_less_than(self):
        expected_cql = 'age:greater-than-or-equal-to:34'
        spec = self.specs_factory.create_less_than('age', 34).not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_not_less_or_equals(self):
        expected_cql = 'age:greater-than:34'
        spec = self.specs_factory.create_less_than_or_equal_to('age', 34).not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_not_greater_than(self):
        expected_cql = 'age:less-than-or-equal-to:34'
        spec = self.specs_factory.create_greater_than('age', 34).not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_not_greater_or_equals(self):
        expected_cql = 'age:less-than:34'
        spec = self.specs_factory.create_greater_than_or_equal_to('age', 34).not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_visit_value_not_in_range(self):
        expected_cql = 'age:not-between:30-40'
        spec = self.specs_factory.create_in_range('age', 30, 40).not_()
        spec.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)


class QueryFilterSpecificationVisitorTestCase(BaseTestCase):
    visitor = None
    specs_factory = None
    def set_up(self):
        if Person.metadata is None:
            setup()
        self.visitor = QueryFilterSpecificationVisitor(Person)
        self.specs_factory = FilterSpecificationFactory()


class ValueBoundQueryFilterSpecificationVisitorTestCase(
                                    QueryFilterSpecificationVisitorTestCase):

    def test_visit_value_starts_with(self):
        expected_expr = Person.name.startswith('Ni')
        spec = self.specs_factory.create_starts_with('name', 'Ni')
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_ends_with(self):
        expected_expr = Person.name.endswith('os')
        spec = self.specs_factory.create_ends_with('name', 'os')
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_contains(self):
        expected_expr = Person.name.contains('iko')
        spec = self.specs_factory.create_contains('name', 'iko')
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_equal_to(self):
        expected_expr = Person.name == 'Nikos'
        spec = self.specs_factory.create_equal_to('name', 'Nikos')
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_less_than(self):
        expected_expr = Person.age < 34
        spec = self.specs_factory.create_less_than('age', 34)
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def _test_visit_value_less_or_equals(self):
        expected_expr = Person.age <= 34
        spec = self.specs_factory.create_less_than_or_equal_to('age', 34)
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_greater_than(self):
        expected_expr = Person.age > 34
        spec = self.specs_factory.create_greater_than('age', 34)
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_greater_or_equals(self):
        expected_expr = Person.age >= 34
        spec = self.specs_factory.create_greater_than_or_equal_to('age', 34)
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_in_range(self):
        expected_expr = Person.age.between(30, 40)
        spec = self.specs_factory.create_in_range('age', 30, 40)
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))


class CompositeQueryFilterSpecificationVisitorTestCase(
                                    QueryFilterSpecificationVisitorTestCase):

    def test_visit_conjuction(self):
        expected_expr = sa.and_(Person.age > 34, Person.name == 'Nikos')
        left_spec = self.specs_factory.create_greater_than('age', 34)
        right_spec = self.specs_factory.create_equal_to('name', 'Nikos')
        spec = left_spec.and_(right_spec)
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_disjuction(self):
        expected_expr = sa.or_(Person.name.startswith('Nikos'),
                               Person.name.startswith('Oliver'))
        spec1 = self.specs_factory.create_starts_with('name', 'Nikos')
        spec2 = self.specs_factory.create_starts_with('name', 'Oliver')
        spec = spec1.or_(spec2)
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_conjuction_with_list_equality(self):
        expected_expr = sa.and_(Person.age.in_([34, 44]),
                                Person.name.in_(['Nikos', 'Oliver']))

        specA = self.specs_factory.create_contained('age', [34, 44])
        specB = self.specs_factory.create_contained('name', ['Nikos', 'Oliver'])

        spec = specA.and_(specB)
        spec.accept(self.visitor)

        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))


class NegationQueryFilterSpecificationVisitorTestCase(
                                    QueryFilterSpecificationVisitorTestCase):

    def test_visit_value_not_starts_with(self):
        expected_expr = sa.not_(Person.name.startswith('Ni'))
        spec = self.specs_factory.create_starts_with('name', 'Ni').not_()
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_not_ends_with(self):
        expected_expr = sa.not_(Person.name.endswith('os'))
        spec = self.specs_factory.create_ends_with('name', 'os').not_()
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_not_contains(self):
        expected_expr = sa.not_(Person.name.contains('iko'))
        spec = self.specs_factory.create_contains('name', 'iko').not_()
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_not_equal_to(self):
        expected_expr = sa.not_(Person.name == 'Nikos')
        spec = self.specs_factory.create_equal_to('name', 'Nikos').not_()
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_not_less_than(self):
        expected_expr = sa.not_(Person.age < 34)
        spec = self.specs_factory.create_less_than('age', 34).not_()
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_not_less_or_equals(self):
        expected_expr = sa.not_(Person.age <= 34)
        spec = self.specs_factory.create_less_than_or_equal_to('age', 34).not_()
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_not_greater_than(self):
        expected_expr = sa.not_(Person.age > 34)
        spec = self.specs_factory.create_greater_than('age', 34).not_()
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_not_greater_or_equals(self):
        expected_expr = sa.not_(Person.age >= 34)
        spec = \
          self.specs_factory.create_greater_than_or_equal_to('age', 34).not_()
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))

    def test_visit_value_not_in_range(self):
        expected_expr = sa.not_(Person.age.between(30, 40))
        spec = self.specs_factory.create_in_range('age', 30, 40).not_()
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))


class ManyValueBoundQueryFilterSpecificationVisitorTestCase(
                                        QueryFilterSpecificationVisitorTestCase):

    def test_visit_value_contained_in_list(self):
        many_ages = range(1000)
        expected_expr = Person.age.in_(many_ages)
        spec = self.specs_factory.create_contained('age', many_ages)
        spec.accept(self.visitor)
        self.assert_equal(str(self.visitor.get_expression()),
                          str(expected_expr))


class QueryOrderSpecificationSpecificationVisitorTestCase(BaseTestCase):
    visitor = None
    order_factory = None

    def set_up(self):
        if Person.metadata is None:
            setup()
        self.visitor = QueryOrderSpecificationVisitor(Person)
        self.order_factory = OrderSpecificationFactory()

    def test_simple_order_by_one_attribute(self):
        expected_expr = [Person.age.asc()]
        order = self.order_factory.create_simple('age')
        order.accept(self.visitor)
        orm_order = self.visitor.get_order()
        self.assert_equal(str(orm_order[0]), str(expected_expr[0]))

    def test_simple_reversed_order_by_one_attribute(self):
        expected_expr = [Person.age.desc()]
        order = self.order_factory.create_simple('age').reverse()
        order.accept(self.visitor)
        orm_order = self.visitor.get_order()
        self.assert_equal(str(orm_order[0]), str(expected_expr[0]))

    def test_simple_order_by_two_attributes(self):
        expected_expr = [Person.age.asc(), Person.name.asc()]
        order = self.order_factory.create_simple('age').and_(
                                    self.order_factory.create_simple('name')
                                    )
        order.accept(self.visitor)
        orm_order = self.visitor.get_order()
        self.assert_equal(len(orm_order), len(expected_expr))
        self.assert_equal(str(orm_order[0]), str(expected_expr[0]))
        self.assert_equal(str(orm_order[1]), str(expected_expr[1]))

    def test_simple_order_by_two_attributes_left_reversed(self):
        expected_expr = [Person.age.desc(), Person.name.asc()]
        order = self.order_factory.create_simple('age').reverse().and_(
                                    self.order_factory.create_simple('name')
                                    )
        order.accept(self.visitor)
        orm_order = self.visitor.get_order()
        self.assert_equal(len(orm_order), len(expected_expr))
        self.assert_equal(str(orm_order[0]), str(expected_expr[0]))
        self.assert_equal(str(orm_order[1]), str(expected_expr[1]))

    def test_simple_order_by_two_attributes_right_reversed(self):
        expected_expr = [Person.age.asc(), Person.name.desc()]
        order = self.order_factory.create_simple('age').and_(
                            self.order_factory.create_simple('name').reverse()
                            )
        order.accept(self.visitor)
        orm_order = self.visitor.get_order()
        self.assert_equal(len(orm_order), len(expected_expr))
        self.assert_equal(str(orm_order[0]), str(expected_expr[0]))
        self.assert_equal(str(orm_order[1]), str(expected_expr[1]))

    def test_simple_order_by_two_attributes_both_reversed(self):
        expected_expr = [Person.age.desc(), Person.name.desc()]
        order = self.order_factory.create_simple('age').reverse().and_(
                            self.order_factory.create_simple('name').reverse()
                            )
        order.accept(self.visitor)
        orm_order = self.visitor.get_order()
        self.assert_equal(len(orm_order), len(expected_expr))
        self.assert_equal(str(orm_order[0]), str(expected_expr[0]))
        self.assert_equal(str(orm_order[1]), str(expected_expr[1]))


class OrderSpecificationCqlFilterSpecificationVisitorTestCase(BaseTestCase):
    visitor = None
    order_factory = None

    def set_up(self):
        if Person.metadata is None:
            setup()
        self.visitor = CqlOrderSpecificationVisitor()
        self.order_factory = OrderSpecificationFactory()

    def test_simple_order_by_one_attribute(self):
        expected_cql = 'my-name:asc'
        order = self.order_factory.create_simple('my_name')
        order.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_simple_reversed_order_by_one_attribute(self):
        expected_cql = 'name:desc'
        order = self.order_factory.create_simple('name').reverse()
        order.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_simple_order_by_two_attributes(self):
        expected_cql = 'name:asc~age:asc'
        order = self.order_factory.create_simple('name').and_(
                                        self.order_factory.create_simple('age')
                                        )
        order.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_simple_order_by_two_attributes_left_reversed(self):
        expected_cql = 'name:desc~age:asc'
        order = self.order_factory.create_simple('name').reverse().and_(
                                        self.order_factory.create_simple('age')
                                        )
        order.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_simple_order_by_two_attributes_right_reversed(self):
        expected_cql = 'name:asc~age:desc'
        order = self.order_factory.create_simple('name').and_(
                              self.order_factory.create_simple('age').reverse()
                              )
        order.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)

    def test_simple_order_by_two_attributes_both_reversed(self):
        expected_cql = 'name:desc~age:desc'
        order = self.order_factory.create_simple('name').reverse().and_(
                              self.order_factory.create_simple('age').reverse()
                              )
        order.accept(self.visitor)
        self.assert_equal(self.visitor.get_cql(), expected_cql)
