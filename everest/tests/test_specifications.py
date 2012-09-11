"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from datetime import datetime
from datetime import timedelta
from everest.querying.base import UnaryOperator
from everest.querying.specifications import FilterSpecification
from everest.querying.specifications import FilterSpecificationFactory
from everest.querying.specifications import NaturalOrderSpecification
from everest.querying.specifications import OrderSpecificationFactory
from everest.querying.specifications import ends
from everest.querying.specifications import eq
from everest.querying.specifications import ge
from everest.querying.specifications import gt
from everest.querying.specifications import le
from everest.querying.specifications import lt
from everest.querying.specifications import starts
from everest.testing import TestCaseWithConfiguration
from everest.testing import TestCaseWithIni
from nose.tools import raises
from everest.querying.specifications import cnts
from everest.querying.specifications import cntd
from everest.querying.specifications import rng
from everest.querying.specifications import asc
from everest.querying.specifications import desc

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


class AlwaysTrueOperator(UnaryOperator):
    name = 'true'
    literal = 'T'

    @staticmethod
    def apply(arg): # pylint: disable=W0613
        return True


class AlwaysFalseOperator(UnaryOperator):
    name = 'false'
    literal = 'F'

    @staticmethod
    def apply(arg): # pylint: disable=W0613
        return False


class AlwaysTrueFilterSpecification(FilterSpecification):

    operator = AlwaysTrueOperator

    def __init__(self):
        FilterSpecification.__init__(self)

    def is_satisfied_by(self, candidate):
        return self.operator.apply(candidate)

    def accept(self, visitor):
        pass


class AlwaysFalseFilterSpecification(FilterSpecification):
    operator = AlwaysFalseOperator
    def is_satisfied_by(self, candidate):
        return False

    def accept(self, visitor):
        pass


class _CriterionFilterSpecificationTestCase(TestCaseWithIni):

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
        self.factory = FilterSpecificationFactory()
        self.candidate = self.create_candidate(text_attr=self.TEXT_VALUE,
                                               number_attr=self.NUMBER_VALUE,
                                               date_attr=self.DATE_VALUE,
                                               list_attr=self.LIST_VALUES)

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

    def test_basics(self):
        spec = self.create_spec('foo', 'bar')
        self.assert_equal(spec, spec)
        spec_other_attr = self.create_spec('bar', 'bar')
        self.assert_not_equal(spec, spec_other_attr)
        spec_other_value = self.create_spec('foo', 'bar1')
        self.assert_not_equal(spec, spec_other_value)
        str_str = '<%s op_name:' % spec.__class__.__name__
        self.assert_equal(str(spec)[:len(str_str)], str_str)


class ValueEqualToFilterSpecificationTestCase(
                                       _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return self.factory.create_equal_to(attr_name, attr_value)

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


class ValueGreaterThanFilterSpecificationTestCase(
                                       _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return self.factory.create_greater_than(attr_name, attr_value)

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


class ValueLessThanFilterSpecificationTestCase(
                                    _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return self.factory.create_less_than(attr_name, attr_value)

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


class ValueGreaterThanOrEqualToFilterSpecificationTestCase(
                                       _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return self.factory.create_greater_than_or_equal_to(attr_name,
                                                            attr_value)

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


class ValueLessThanOrEqualToFilterSpecificationTestCase(
                                       _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return self.factory.create_less_than_or_equal_to(attr_name,
                                                         attr_value)

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


class ValueInRangeFilterSpecificationTestCase(
                                       _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        from_value, to_value = attr_value
        return self.factory.create_in_range(attr_name, (from_value, to_value))

    def test_basics(self):
        spec = self.create_spec('foo', ('bar0', 'bar1'))
        self.assert_equal(spec.from_value, 'bar0')
        self.assert_equal(spec.to_value, 'bar1')
        self.assert_equal(spec, spec)
        spec_other_value = self.create_spec('foo', ('bar0', 'bar2'))
        self.assert_not_equal(spec, spec_other_value)
        spec_other_attr = self.create_spec('bar', ('bar0', 'bar1'))
        self.assert_not_equal(spec, spec_other_attr)

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


class ValueStartsWithFilterSpecificationTestCase(
                                       _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return self.factory.create_starts_with(attr_name, attr_value)

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


class ValueEndsWithFilterSpecificationTestCase(
                                    _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return self.factory.create_ends_with(attr_name, attr_value)

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


class ValueContainsFilterSpecificationTestCase(
                                    _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return self.factory.create_contains(attr_name, attr_value)

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


class ValueContainedFilterSpecificationTestCase(
                                       _CriterionFilterSpecificationTestCase):

    def create_spec(self, attr_name, attr_value):
        return self.factory.create_contained(attr_name, attr_value)

    def test_contained_list_value_is_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.TEXT_VALUE_LIST)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_contained_list_value_is_not_statisfied_by_candidate(self):
        spec = self.create_text_value_spec(self.LIST_VALUES)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class CompositeFilterSpecificationTestCase(TestCaseWithIni):

    def set_up(self):
        self.factory = FilterSpecificationFactory()
        self.candidate = object()
        self.always_true = AlwaysTrueFilterSpecification()
        self.always_false = AlwaysFalseFilterSpecification()

    def create_conjuction_spec(self, left_spec, right_spec):
        return self.factory.create_conjunction(left_spec, right_spec)

    def create_disjunction_spec(self, left_spec, right_spec):
        return self.factory.create_disjunction(left_spec, right_spec)

    def test_basics(self):
        conj_spec = self.create_conjuction_spec(self.always_true,
                                                self.always_false)
        self.assert_equal(conj_spec, conj_spec)
        conj_spec_other_spec = self.create_conjuction_spec(self.always_false,
                                                           self.always_true)
        self.assert_not_equal(conj_spec, conj_spec_other_spec)
        str_str = '<%s left_spec:' % conj_spec.__class__.__name__
        self.assert_equal(str(conj_spec)[:len(str_str)], str_str)


class ConjuctionFilterSpecificationTestCase(
                                     CompositeFilterSpecificationTestCase):

    def test_conjuction_is_statisfied_by_candidate(self):
        spec = self.create_conjuction_spec(self.always_true, self.always_true)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_conjuction_is_not_statisfied_by_candidate(self):
        spec = self.create_conjuction_spec(self.always_false,
                                           self.always_true)
        self.assert_false(spec.is_satisfied_by(self.candidate))

        spec = self.create_conjuction_spec(self.always_true,
                                           self.always_false)
        self.assert_false(spec.is_satisfied_by(self.candidate))
        spec = self.create_conjuction_spec(self.always_false,
                                           self.always_false)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class DisjuctionFilterSpecificationTestCase(
                                    CompositeFilterSpecificationTestCase):

    def test_is_statisfied_by_candidate(self):
        spec = self.create_disjunction_spec(self.always_false,
                                            self.always_true)
        self.assert_true(spec.is_satisfied_by(self.candidate))
        spec = self.create_disjunction_spec(self.always_true,
                                            self.always_false)
        self.assert_true(spec.is_satisfied_by(self.candidate))
        spec = self.create_disjunction_spec(self.always_true,
                                            self.always_true)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_disjunction_is_not_statisfied_by_candidate(self):
        spec = self.create_disjunction_spec(self.always_false,
                                            self.always_false)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class NegationFilterSpecificationTestCase(TestCaseWithIni):

    def set_up(self):
        self.factory = FilterSpecificationFactory()
        self.candidate = object()
        self.always_true = AlwaysTrueFilterSpecification()
        self.always_false = AlwaysFalseFilterSpecification()

    def create_negation_spec(self, wrapped_spec):
        return self.factory.create_negation(wrapped_spec)

    def test_basics(self):
        spec = self.create_negation_spec(self.always_false)
        self.assert_equal(spec, spec)
        spec_other_spec = self.create_negation_spec(self.always_true)
        self.assert_not_equal(spec, spec_other_spec)
        str_str = '<%s wrapped_spec:' % spec.__class__.__name__
        self.assert_equal(str(spec)[:len(str_str)], str_str)

    def test_negation_is_satisfied_by_candidate(self):
        spec = self.create_negation_spec(self.always_false)
        self.assert_true(spec.is_satisfied_by(self.candidate))

    def test_negation_is_not_satisfied_by_candidate(self):
        spec = self.create_negation_spec(self.always_true)
        self.assert_false(spec.is_satisfied_by(self.candidate))


class OrderSpecificationTestCase(TestCaseWithIni):
    def set_up(self):
        self.factory = OrderSpecificationFactory()

    def create_ascending_spec(self, attr_name):
        return self.factory.create_ascending(attr_name)

    def create_descending_spec(self, attr_name):
        return self.factory.create_descending(attr_name)

    def create_natural_spec(self, attr_name):
        return NaturalOrderSpecification(attr_name)

    def test_operations(self):
        first_candidate = Candidate(number_attr=0, text_attr='a')
        second_candidate = Candidate(number_attr=1, text_attr='b')
        def _test(attr):
            spec_asc = self.create_ascending_spec(attr)
            spec_desc = self.create_descending_spec(attr)
            self.assert_equal(spec_asc.attr_name, attr)
            self.assert_equal(spec_desc.attr_name, attr)
            self.assert_false(spec_asc.eq(first_candidate, second_candidate))
            self.assert_false(spec_desc.eq(first_candidate, second_candidate))
            self.assert_true(spec_asc.ne(first_candidate, second_candidate))
            self.assert_true(spec_desc.ne(first_candidate, second_candidate))
            self.assert_true(spec_asc.lt(first_candidate, second_candidate))
            self.assert_false(spec_desc.lt(first_candidate, second_candidate))
            self.assert_false(spec_asc.ge(first_candidate, second_candidate))
            self.assert_true(spec_desc.ge(first_candidate, second_candidate))
            self.assert_true(spec_asc.le(first_candidate, second_candidate))
            self.assert_false(spec_desc.le(first_candidate, second_candidate))
            self.assert_false(spec_asc.gt(first_candidate, second_candidate))
            self.assert_true(spec_desc.gt(first_candidate, second_candidate))
        _test('number_attr')
        _test('text_attr')

    def test_basics(self):
        spec = self.create_ascending_spec('foo')
        str_str = '<%s attr_name:' % spec.__class__.__name__
        self.assert_equal(str(spec)[:len(str_str)], str_str)

    def test_natural(self):
        first_candidate = Candidate(number_attr=0, text_attr='a10')
        second_candidate = Candidate(number_attr=1, text_attr='a9')
        text_spec = self.create_natural_spec('text_attr')
        self.assert_false(text_spec.lt(first_candidate, second_candidate))
        number_spec = self.create_natural_spec('number_attr')
        self.assert_true(number_spec.lt(first_candidate, second_candidate))

    def test_conjunction(self):
        first_candidate = Candidate(number_attr=0, text_attr='a')
        second_candidate = Candidate(number_attr=0, text_attr='b')
        text_spec = self.create_natural_spec('text_attr')
        number_spec = self.create_natural_spec('number_attr')
        conj_spec = self.factory.create_conjunction(number_spec, text_spec)
        str_str = '<%s left:' % conj_spec.__class__.__name__
        self.assert_equal(str(conj_spec)[:len(str_str)], str_str)
        self.assert_true(conj_spec.lt(first_candidate, second_candidate))
        self.assert_true(conj_spec.le(first_candidate, second_candidate))
        self.assert_false(conj_spec.eq(first_candidate, second_candidate))
        self.assert_equal(conj_spec.cmp(first_candidate, second_candidate),
                          - 1)
        conj_spec = self.factory.create_conjunction(text_spec, number_spec)
        self.assert_true(conj_spec.lt(first_candidate, second_candidate))
        self.assert_true(conj_spec.le(first_candidate, second_candidate))
        self.assert_false(conj_spec.eq(first_candidate, second_candidate))
        self.assert_equal(conj_spec.cmp(first_candidate, second_candidate),
                          - 1)


class SpecificationGeneratorTestCase(TestCaseWithConfiguration):
    def set_up(self):
        TestCaseWithConfiguration.set_up(self)
        self.candidate = Candidate(number_attr=0, text_attr='attr')

    def test_eq_generator(self):
        gen = eq(number_attr=0).and_(eq(text_attr='attr'))
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_starts_generator(self):
        gen = starts(text_attr='a')
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_ends_generator(self):
        gen = ends(text_attr='r')
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_lt_generator(self):
        gen = lt(number_attr=1)
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_le_generator(self):
        gen = le(number_attr=0)
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_gt_generator(self):
        gen = gt(number_attr= -1)
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_ge_generator(self):
        gen = ge(number_attr=0)
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_cnts_generator(self):
        gen = cnts(text_attr='tt')
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_cntd_generator(self):
        gen = cntd(text_attr=['attr'])
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_rng_generator(self):
        gen = rng(number_attr=(-1, 1))
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_asc_generator(self):
        second_candidate = Candidate(number_attr=0, text_attr='b')
        gen = asc('number_attr').and_(asc('text_attr'))
        self.assert_true(gen.spec.lt(self.candidate, second_candidate))

    def test_desc_generator(self):
        second_candidate = Candidate(number_attr=0, text_attr='b')
        gen = desc('number_attr').and_(desc('text_attr'))
        self.assert_true(gen.spec.lt(second_candidate, self.candidate))

    def test_chaining_generator(self):
        gen = lt(number_attr=1).gt(number_attr= -1)
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_generator_or(self):
        gen = lt(number_attr=1).or_(gt(number_attr=1))
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))

    def test_generator_not(self):
        gen = lt(number_attr= -1).not_()
        self.assert_true(gen.spec.is_satisfied_by(self.candidate))
