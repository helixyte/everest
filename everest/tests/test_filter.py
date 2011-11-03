"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Jul 5, 2011.
"""

from everest.filter import SpecificationFilterBuilder
from everest.testing import BaseTestCase
from everest.specifications import specification_factory
from everest.specifications import ValueEqualToSpecification
from everest.specifications import ValueStartsWithSpecification
from everest.specifications import ValueEndsWithSpecification
from everest.specifications import ValueContainsSpecification
from everest.specifications import ValueLessThanOrEqualToSpecification
from everest.specifications import ValueLessThanSpecification
from everest.specifications import ValueGreaterThanOrEqualToSpecification
from everest.specifications import ValueGreaterThanSpecification
from everest.specifications import ValueInRangeSpecification
from everest.specifications import ValueContainedSpecification

__docformat__ = 'reStructuredText en'
__all__ = ['ValueBoundSpecificationFilterBuilderTestCase',
           ]



class ValueBoundSpecificationFilterBuilderTestCase(BaseTestCase):
    builder = None

    def set_up(self):
        self.builder = SpecificationFilterBuilder(specification_factory)

    def tear_down(self):
        pass

    def test_build_equal_to(self):
        attr_name, attr_values = ('name', ['Nikos'])
        expected_spec = ValueEqualToSpecification(attr_name, attr_values[0])
        self.builder.build_equal_to(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_not_equal_to(self):
        attr_name, attr_values = ('name', ['Nikos'])
        expected_spec = ValueEqualToSpecification(attr_name, attr_values[0]).not_()
        self.builder.build_not_equal_to(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_starts_with(self):
        attr_name, attr_values = ('name', ['Ni'])
        expected_spec = ValueStartsWithSpecification(attr_name, attr_values[0])
        self.builder.build_starts_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_not_starts_with(self):
        attr_name, attr_values = ('name', ['Ni'])
        expected_spec = ValueStartsWithSpecification(attr_name, attr_values[0]).not_()
        self.builder.build_not_starts_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_ends_with(self):
        attr_name, attr_values = ('name', ['os'])
        expected_spec = ValueEndsWithSpecification(attr_name, attr_values[0])
        self.builder.build_ends_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_not_ends_with(self):
        attr_name, attr_values = ('name', ['os'])
        expected_spec = ValueEndsWithSpecification(attr_name, attr_values[0]).not_()
        self.builder.build_not_ends_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_contains(self):
        attr_name, attr_values = ('name', ['iko'])
        expected_spec = ValueContainsSpecification(attr_name, attr_values[0])
        self.builder.build_contains(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_not_contains(self):
        attr_name, attr_values = ('name', ['iko'])
        expected_spec = ValueContainsSpecification(attr_name, attr_values[0]).not_()
        self.builder.build_not_contains(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_less_than_or_equal_to(self):
        attr_name, attr_values = ('age', [34])
        expected_spec = ValueLessThanOrEqualToSpecification(attr_name, attr_values[0])
        self.builder.build_less_than_or_equal_to(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_less_than(self):
        attr_name, attr_values = ('age', [34])
        expected_spec = ValueLessThanSpecification(attr_name, attr_values[0])
        self.builder.build_less_than(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_greater_than_or_equal_to(self):
        attr_name, attr_values = ('age', [34])
        expected_spec = ValueGreaterThanOrEqualToSpecification(attr_name, attr_values[0])
        self.builder.build_greater_than_or_equal_to(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_greater_than(self):
        attr_name, attr_values = ('age', [34])
        expected_spec = ValueGreaterThanSpecification(attr_name, attr_values[0])
        self.builder.build_greater_than(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_in_range(self):
        attr_name, attr_values = ('age', [(30, 40)])
        expected_spec = ValueInRangeSpecification(attr_name, *attr_values[0]) # pylint: disable=W0142
        self.builder.build_in_range(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_not_in_range(self):
        attr_name, attr_values = ('age', [(30, 40)])
        expected_spec = ValueInRangeSpecification(attr_name, *attr_values[0]).not_() # pylint: disable=W0142
        self.builder.build_not_in_range(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())


class CompositeSpecificationFilterBuilderTestCase(BaseTestCase):
    builder = None

    def set_up(self):
        self.builder = SpecificationFilterBuilder(specification_factory)

    def tear_down(self):
        pass

    def test_build_conjunction(self):
        left_name, left_values = ('age', [34])
        right_name, right_values = ('name', ['Nikos'])
        expected_spec = \
            ValueGreaterThanSpecification(left_name, left_values[0]).and_(
            ValueEqualToSpecification(right_name, right_values[0])
            )
        self.builder.build_greater_than(left_name, left_values)
        self.builder.build_equal_to(right_name, right_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_disjunction(self):
        attr_name, attr_values = ('name', ['Ni', 'Ol'])
        expected_spec = \
            ValueStartsWithSpecification(attr_name, attr_values[0]).or_(
            ValueStartsWithSpecification(attr_name, attr_values[1])
            )
        self.builder.build_starts_with(attr_name, attr_values)
        self.assert_equal(expected_spec, self.builder.get_specification())

    def test_build_conjunction_with_disjunction(self):
        left_name, left_values = ('age', [34, 44])
        right_name, right_values = ('name', ['Ni', 'Ol'])
        expected_spec = \
            ValueContainedSpecification(left_name, left_values).and_(
                ValueStartsWithSpecification(right_name, right_values[0]).or_(
                ValueStartsWithSpecification(right_name, right_values[1])
                )
            )
        self.builder.build_equal_to(left_name, left_values)
        self.builder.build_starts_with(right_name, right_values)
        self.assert_equal(expected_spec, self.builder.get_specification())
