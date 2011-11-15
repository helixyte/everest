"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""

from datetime import datetime, timedelta
from everest.specifications import ConjuctionFilterSpecification
from everest.specifications import DisjuctionFilterSpecification
from everest.specifications import LeafFilterSpecification
from everest.specifications import NegationFilterSpecification
from everest.specifications import ValueContainedFilterSpecification
from everest.specifications import ValueContainsFilterSpecification
from everest.specifications import ValueEndsWithFilterSpecification
from everest.specifications import ValueEqualToFilterSpecification
from everest.specifications import ValueGreaterThanOrEqualToFilterSpecification
from everest.specifications import ValueGreaterThanFilterSpecification
from everest.specifications import ValueInRangeFilterSpecification
from everest.specifications import ValueLessThanOrEqualToFilterSpecification
from everest.specifications import ValueLessThanFilterSpecification
from everest.specifications import ValueStartsWithFilterSpecification
from everest.testing import BaseTestCase
from nose.tools import raises

__docformat__ = 'reStructuredText en'
__all__ = ['TestConjuctionFilterSpecification',
           'TestDisjuctionFilterSpecification',
           'TestNegationFilterSpecification',
           'TestValueContainedFilterSpecification',
           'TestValueContainsFilterSpecification',
           'TestValueEqualToFilterSpecification',
           'TestValueGreaterThanOrEqualToFilterSpecification',
           'TestValueGreaterThanFilterSpecification',
           'TestValueInRangeFilterSpecification',
           'TestValueLessThanOrEqualToFilterSpecification',
           'TestValueLessThanFilterSpecification',
           'TestValueEndsWithFilterSpecification',
           'TestValueStartsWithFilterSpecification',
           ]


class Candidate(object):
    def __init__(self, **attributes):
        for attr_name, attr_value in attributes.iteritems():
            setattr(self, attr_name, attr_value)

    def __str__(self):
        attrs = ['%s: %s' % (k, getattr(self, k))
                 for k in self.__dict__
                 if not k.startswith('_')]
        return 'Candidate -> %s' % ', '.join(attrs)


class AlwaysTrueFilterSpecification(LeafFilterSpecification):
    def is_satisfied_by(self, candidate):
        return True

    def accept(self, visitor):
        pass


class AlwaysFalseFilterSpecification(LeafFilterSpecification):
    def is_satisfied_by(self, candidate):
        return False

    def accept(self, visitor):
        pass

class ValueBoundFilterSpecificationTestCase(BaseTestCase):
    candidate = None

    TEXT_VALUE = 'Beta-2'
    GREATER_THAN_TEXT_VALUE = 'Gamma-3'
    LESS_THAN_TEXT_VALUE = 'Alpha-1'
    TEXT_VALUE_LIST = [LESS_THAN_TEXT_VALUE, TEXT_VALUE,
                       GREATER_THAN_TEXT_VALUE]

    NUMBER_VALUE = 40
    GREATER_THAN_NUMBER_VALUE = NUMBER_VALUE + 1
    LESS_THAN_NUMBER_VALUE = NUMBER_VALUE - 1

    DATE_VALUE = datetime(1970, 1, 1)
    GREATER_THAN_DATE_VALUE = DATE_VALUE + timedelta(1)
    LESS_THAN_DATE_VALUE = DATE_VALUE - timedelta(1)

    LIST_VALUES = [1, 2, 3, 4, 5]

    def set_up(self):
        self.candidate = self.create_candidate(text_attr=self.TEXT_VALUE,
                                               number_attr=self.NUMBER_VALUE,
                                               date_attr=self.DATE_VALUE,
                                               list_attr=self.LIST_VALUES)

    def tear_down(self):
        pass

    def create_candidate(self, **attributes):
        return Candidate(**attributes)

    def create_text_value_spec(self, text_value):
        return self.create_spec('text_attr', text_value)

    def create_number_value_spec(self, number_value):
        return self.create_spec('number_attr', number_value)

    def create_date_value_spec(self, date_value):
        return self.create_spec('date_attr', date_value)

    def create_list_value_spec(self, list_value):
        return self.create_spec('list_attr', list_value)

    def create_spec(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')


class TestValueEqualToFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return ValueEqualToFilterSpecification(attr_name, attr_value)

    def test_text_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.TEXT_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_text_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.GREATER_THAN_TEXT_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_not_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.GREATER_THAN_NUMBER_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_not_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.GREATER_THAN_DATE_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class TestValueGreaterThanFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return ValueGreaterThanFilterSpecification(attr_name, attr_value)

    def test_text_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.LESS_THAN_TEXT_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_text_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.TEXT_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.LESS_THAN_NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_not_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.NUMBER_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.LESS_THAN_DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_not_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.DATE_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class TestValueLessThanFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return ValueLessThanFilterSpecification(attr_name, attr_value)

    def test_text_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.GREATER_THAN_TEXT_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_text_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.TEXT_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.GREATER_THAN_NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_not_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.NUMBER_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.GREATER_THAN_DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_not_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.DATE_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class TestValueGreaterThanOrEqualToFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return ValueGreaterThanOrEqualToFilterSpecification(attr_name, attr_value)

    def test_text_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.LESS_THAN_TEXT_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

        spec = self.create_text_value_spec(self.TEXT_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_text_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.GREATER_THAN_TEXT_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.LESS_THAN_NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

        spec = self.create_number_value_spec(self.NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_not_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.GREATER_THAN_NUMBER_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.LESS_THAN_DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

        spec = self.create_date_value_spec(self.DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_not_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.GREATER_THAN_DATE_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class TestValueLessThanOrEqualToFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return ValueLessThanOrEqualToFilterSpecification(attr_name, attr_value)

    def test_text_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.GREATER_THAN_TEXT_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

        spec = self.create_text_value_spec(self.TEXT_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_text_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.LESS_THAN_TEXT_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.GREATER_THAN_NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

        spec = self.create_number_value_spec(self.NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_not_statisfied_by_candidate(self):
        spec = self.create_number_value_spec(self.LESS_THAN_NUMBER_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.GREATER_THAN_DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

        spec = self.create_date_value_spec(self.DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_not_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.LESS_THAN_DATE_VALUE)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class TestValueInRangeFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        from_value, to_value = attr_value
        return ValueInRangeFilterSpecification(attr_name, from_value, to_value)

    def test_text_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec((self.LESS_THAN_TEXT_VALUE,
                                            self.GREATER_THAN_TEXT_VALUE))
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_text_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec((self.GREATER_THAN_TEXT_VALUE,
                                            self.LESS_THAN_TEXT_VALUE))
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_statisfied_by_candidate(self):
        spec = self.create_number_value_spec((self.LESS_THAN_NUMBER_VALUE,
                                              self.GREATER_THAN_NUMBER_VALUE))
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_number_value_is_not_statisfied_by_candidate(self):
        spec = self.create_number_value_spec((self.GREATER_THAN_NUMBER_VALUE,
                                              self.LESS_THAN_NUMBER_VALUE))
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_statisfied_by_candidate(self):
        spec = self.create_date_value_spec((self.LESS_THAN_DATE_VALUE,
                                            self.GREATER_THAN_DATE_VALUE))
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_date_value_is_not_statisfied_by_candidate(self):
        spec = self.create_date_value_spec((self.GREATER_THAN_DATE_VALUE,
                                            self.LESS_THAN_DATE_VALUE))
        self.assert_false(spec.is_satisfied_by(self.candidate))


class TestValueStartsWithFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return ValueStartsWithFilterSpecification(attr_name, attr_value)

    def test_text_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.TEXT_VALUE[0])
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_text_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.GREATER_THAN_TEXT_VALUE[0])
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_list_value_is_statisfied_by_candidate(self):
        spec = self.create_list_value_spec(self.LIST_VALUES[0])
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_list_value_is_not_statisfied_by_candidate(self):
        spec = self.create_list_value_spec(self.LIST_VALUES[-1])
        self.assert_false(spec.is_satisfied_by(self.candidate))

    @raises(TypeError)
    def test_number_value_raises_exception(self):
        spec = self.create_number_value_spec(self.NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    @raises(TypeError)
    def test_date_value_is_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))


class TestValueEndsWithFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return ValueEndsWithFilterSpecification(attr_name, attr_value)

    def test_text_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.TEXT_VALUE[-1])
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_text_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.GREATER_THAN_TEXT_VALUE[-1])
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_list_value_is_statisfied_by_candidate(self):
        spec = self.create_list_value_spec(self.LIST_VALUES[-1])
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_list_value_is_not_statisfied_by_candidate(self):
        spec = self.create_list_value_spec(self.LIST_VALUES[0])
        self.assert_false(spec.is_satisfied_by(self.candidate))

    @raises(TypeError)
    def test_number_value_raises_exception(self):
        spec = self.create_number_value_spec(self.NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    @raises(TypeError)
    def test_date_value_is_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))


class TestValueContainsFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return ValueContainsFilterSpecification(attr_name, attr_value)

    def test_text_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.TEXT_VALUE[2])
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_text_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.GREATER_THAN_TEXT_VALUE[-1])
        self.assert_false(spec.is_satisfied_by(self.candidate))

    def test_list_value_is_statisfied_by_candidate(self):
        spec = self.create_list_value_spec(self.LIST_VALUES[2])
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_list_value_is_not_statisfied_by_candidate(self):
        spec = self.create_list_value_spec(-1)
        self.assert_false(spec.is_satisfied_by(self.candidate))

    @raises(TypeError)
    def test_number_value_raises_exception(self):
        spec = self.create_number_value_spec(self.NUMBER_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    @raises(TypeError)
    def test_date_value_is_statisfied_by_candidate(self):
        spec = self.create_date_value_spec(self.DATE_VALUE)
        self.assert_true(spec.is_satisfied_by(self.candidate))


class TestValueContainedFilterSpecification(ValueBoundFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return ValueContainedFilterSpecification(attr_name, attr_value)

    def test_contained_list_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.TEXT_VALUE_LIST)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_contained_list_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.LIST_VALUES)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class CompositeFilterSpecificationTestCase(BaseTestCase):
    candidate = None
    always_true = None
    always_false = None

    def set_up(self):
        self.candidate = object()
        self.always_true = AlwaysTrueFilterSpecification()
        self.always_false = AlwaysFalseFilterSpecification()

    def tear_down(self):
        pass

    def create_conjuction_spec(self, left_spec, right_spec):
        return ConjuctionFilterSpecification(left_spec, right_spec)

    def create_disjunction_spec(self, left_spec, right_spec):
        return DisjuctionFilterSpecification(left_spec, right_spec)


class TestConjuctionFilterSpecification(CompositeFilterSpecificationTestCase):

    def test_conjuction_is_statisfied_by_candidate(self):
        spec = self.create_conjuction_spec(self.always_true, self.always_true)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_conjuction_is_not_statisfied_by_candidate(self):
        spec = self.create_conjuction_spec(self.always_false, self.always_true)
        self.assert_false(spec.is_satisfied_by(self.candidate))

        spec = self.create_conjuction_spec(self.always_true, self.always_false)
        self.assert_false(spec.is_satisfied_by(self.candidate))

        spec = self.create_conjuction_spec(self.always_false, self.always_false)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class TestDisjuctionFilterSpecification(CompositeFilterSpecificationTestCase):

    def test_is_statisfied_by_candidate(self):
        spec = self.create_disjunction_spec(self.always_false, self.always_true)
        self.assert_true(spec.is_satisfied_by(self.candidate))

        spec = self.create_disjunction_spec(self.always_true, self.always_false)
        self.assert_true(spec.is_satisfied_by(self.candidate))

        spec = self.create_disjunction_spec(self.always_true, self.always_true)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_disjunction_is_not_statisfied_by_candidate(self):
        spec = self.create_disjunction_spec(self.always_false, self.always_false)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class TestNegationFilterSpecification(BaseTestCase):
    candidate = None
    always_true = None
    always_false = None

    def set_up(self):
        self.candidate = object()
        self.always_true = AlwaysTrueFilterSpecification()
        self.always_false = AlwaysFalseFilterSpecification()

    def tear_down(self):
        pass

    def create_negation_spec(self, wrapped_spec):
        return NegationFilterSpecification(wrapped_spec)

    def test_negation_is_satisfied_by_candidate(self):
        spec = self.create_negation_spec(self.always_false)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_negation_is_not_satisfied_by_candidate(self):
        spec = self.create_negation_spec(self.always_true)
        self.assert_false(spec.is_satisfied_by(self.candidate))
