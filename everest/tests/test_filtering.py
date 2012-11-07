"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 5, 2011.
"""
from everest.querying.filtering import FilterSpecificationBuilder
from everest.querying.filtering import SqlFilterSpecificationVisitor
from everest.querying.specifications import FilterSpecificationFactory
from everest.querying.specifications import ValueContainedFilterSpecification
from everest.querying.specifications import ValueContainsFilterSpecification
from everest.querying.specifications import ValueEndsWithFilterSpecification
from everest.querying.specifications import ValueEqualToFilterSpecification
from everest.querying.specifications import ValueInRangeFilterSpecification
from everest.querying.specifications import ValueLessThanFilterSpecification
from everest.querying.specifications import ValueStartsWithFilterSpecification
from everest.querying.specifications import \
        ValueGreaterThanFilterSpecification
from everest.querying.specifications import \
        ValueGreaterThanOrEqualToFilterSpecification
from everest.querying.specifications import \
        ValueLessThanOrEqualToFilterSpecification
from everest.testing import TestCaseWithConfiguration
from everest.testing import Pep8CompliantTestCase
from everest.tests.testapp.entities import FooEntity

__docformat__ = 'reStructuredText en'
__all__ = ['CompositeFilterSpecificationBuilderTestCase',
           'CriterionFilterSpecificationBuilderTestCase',
           'SqlFilterSpecificationVisitorTestCase',
           ]


class CriterionFilterSpecificationBuilderTestCase(TestCaseWithConfiguration):

    def set_up(self):
        self.builder = FilterSpecificationBuilder(FilterSpecificationFactory())

    def tear_down(self):
        pass

    def test_build_equal_to(self):
        attr_name, attr_values = ('name', ['Nikos'])
        expected_spec = ValueEqualToFilterSpecification(attr_name,
                                                        attr_values[0])
        self.builder.build_equal_to(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_not_equal_to(self):
        attr_name, attr_values = ('name', ['Nikos'])
        expected_spec = ValueEqualToFilterSpecification(attr_name,
                                                        attr_values[0]).not_()
        self.builder.build_not_equal_to(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_starts_with(self):
        attr_name, attr_values = ('name', ['Ni'])
        expected_spec = ValueStartsWithFilterSpecification(attr_name,
                                                           attr_values[0])
        self.builder.build_starts_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_not_starts_with(self):
        attr_name, attr_values = ('name', ['Ni'])
        expected_spec = \
            ValueStartsWithFilterSpecification(attr_name,
                                               attr_values[0]).not_()
        self.builder.build_not_starts_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_ends_with(self):
        attr_name, attr_values = ('name', ['os'])
        expected_spec = ValueEndsWithFilterSpecification(attr_name,
                                                         attr_values[0])
        self.builder.build_ends_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_not_ends_with(self):
        attr_name, attr_values = ('name', ['os'])
        expected_spec = ValueEndsWithFilterSpecification(attr_name,
                                                         attr_values[0]).not_()
        self.builder.build_not_ends_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_contains(self):
        attr_name, attr_values = ('name', ['iko'])
        expected_spec = ValueContainsFilterSpecification(attr_name,
                                                         attr_values[0])
        self.builder.build_contains(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_not_contains(self):
        attr_name, attr_values = ('name', ['iko'])
        expected_spec = ValueContainsFilterSpecification(attr_name,
                                                         attr_values[0]).not_()
        self.builder.build_not_contains(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_less_than_or_equal_to(self):
        attr_name, attr_values = ('age', [34])
        expected_spec = \
                ValueLessThanOrEqualToFilterSpecification(attr_name,
                                                          attr_values[0])
        self.builder.build_less_than_or_equal_to(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_less_than(self):
        attr_name, attr_values = ('age', [34])
        expected_spec = ValueLessThanFilterSpecification(attr_name,
                                                         attr_values[0])
        self.builder.build_less_than(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_greater_than_or_equal_to(self):
        attr_name, attr_values = ('age', [34])
        expected_spec = \
                ValueGreaterThanOrEqualToFilterSpecification(attr_name,
                                                             attr_values[0])
        self.builder.build_greater_than_or_equal_to(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_greater_than(self):
        attr_name, attr_values = ('age', [34])
        expected_spec = ValueGreaterThanFilterSpecification(attr_name,
                                                            attr_values[0])
        self.builder.build_greater_than(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_in_range(self):
        attr_name, attr_values = ('age', [(30, 40)])
        expected_spec = ValueInRangeFilterSpecification(attr_name,
                                                        attr_values[0])
        self.builder.build_in_range(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_not_in_range(self):
        attr_name, attr_values = ('age', [(30, 40)])
        expected_spec = \
            ValueInRangeFilterSpecification(attr_name,
                                            attr_values[0]).not_()
        self.builder.build_not_in_range(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)


class CompositeFilterSpecificationBuilderTestCase(TestCaseWithConfiguration):

    def set_up(self):
        self.builder = FilterSpecificationBuilder(FilterSpecificationFactory())

    def tear_down(self):
        pass

    def test_build_conjunction(self):
        left_name, left_values = ('age', [34])
        right_name, right_values = ('name', ['Nikos'])
        expected_spec = \
            ValueGreaterThanFilterSpecification(left_name,
                                                left_values[0]).and_(
            ValueEqualToFilterSpecification(right_name, right_values[0])
            )
        self.builder.build_open_group()
        self.builder.build_greater_than(left_name, left_values)
        self.builder.build_and()
        self.builder.build_equal_to(right_name, right_values)
        self.builder.build_close_group()
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_disjunction(self):
        attr_name, attr_values = ('name', ['Ni', 'Ol'])
        expected_spec = \
            ValueStartsWithFilterSpecification(attr_name,
                                               attr_values[0]).or_(
            ValueStartsWithFilterSpecification(attr_name, attr_values[1])
            )
        self.builder.build_starts_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.specification)

    def test_build_conjunction_with_disjunction(self):
        left_name, left_values = ('age', [34, 44])
        right_name, right_values = ('name', ['Ni', 'Ol'])
        expected_spec = \
            ValueContainedFilterSpecification(left_name, left_values).and_(
                ValueStartsWithFilterSpecification(right_name,
                                                   right_values[0]).or_(
                ValueStartsWithFilterSpecification(right_name, right_values[1])
                )
            )
        self.builder.build_open_group()
        self.builder.build_contained(left_name, left_values)
        self.builder.build_and()
        self.builder.build_starts_with(right_name, right_values)
        self.builder.build_close_group()
        self.assert_equal(expected_spec, self.builder.specification)

    def test_grouped_junctions(self):
        name1, values1 = ('age', [34])
        name2, values2 = ('gender', ['F'])
        name3, values3 = ('name', ['Nikos'])
        name4, values4 = ('gender', ['M'])
        expected_spec = \
            (ValueEqualToFilterSpecification(name1, values1[0]).and_(
             ValueEqualToFilterSpecification(name2, values2[0]))).or_(
            (ValueEqualToFilterSpecification(name3, values3[0]).and_(
             ValueEqualToFilterSpecification(name4, values4[0]))))
        self.builder.build_open_group()
        self.builder.build_equal_to(name1, [values1[0]])
        self.builder.build_and()
        self.builder.build_equal_to(name2, [values2[0]])
        self.builder.build_close_group()
        self.builder.build_or()
        self.builder.build_open_group()
        self.builder.build_equal_to(name3, [values3[0]])
        self.builder.build_and()
        self.builder.build_equal_to(name4, [values4[0]])
        self.builder.build_close_group()
        self.assert_equal(expected_spec, self.builder.specification)

    def test_nested_grouped_junctions(self):
        name1, values1 = ('age', [34])
        name2, values2 = ('gender', ['F'])
        name3, values3 = ('name', ['Nikos'])
        name4, values4 = ('gender', ['M'])
        expected_spec = \
            ValueEqualToFilterSpecification(name1, values1[0]).and_(
            (ValueEqualToFilterSpecification(name2, values2[0]).or_(
             ValueEqualToFilterSpecification(name3, values3[0])))).and_(
             ValueEqualToFilterSpecification(name4, values4[0]))
        self.builder.build_open_group()
        self.builder.build_equal_to(name1, [values1[0]])
        self.builder.build_and()
        self.builder.build_open_group()
        self.builder.build_equal_to(name2, [values2[0]])
        self.builder.build_or()
        self.builder.build_equal_to(name3, [values3[0]])
        self.builder.build_close_group()
        self.builder.build_and()
        self.builder.build_open_group()
        self.builder.build_equal_to(name4, [values4[0]])
        self.builder.build_close_group()
        self.assert_equal(expected_spec, self.builder.specification)

class SqlFilterSpecificationVisitorTestCase(Pep8CompliantTestCase):
    def test_custom_clause(self):
        obj = object()
        func = lambda value: obj
        spec = ValueEqualToFilterSpecification('foo', 'bar')
        factory_map = {('foo', spec.operator.name):func}
        visitor = SqlFilterSpecificationVisitor(FooEntity,
                                                custom_clause_factories=
                                                                 factory_map)
        visitor.visit_nullary(spec)
        self.assert_true(visitor.expression is obj)
