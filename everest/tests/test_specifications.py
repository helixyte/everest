"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from datetime import datetime
from datetime import timedelta

from pyramid.compat import iteritems_
import pytest

from everest.querying.operators import UnaryOperator
from everest.querying.specifications import ConjunctionFilterSpecification
from everest.querying.specifications import DisjunctionFilterSpecification
from everest.querying.specifications import FilterSpecification
from everest.querying.specifications import FilterSpecificationGenerator
from everest.querying.specifications import NegationFilterSpecification
from everest.querying.specifications import asc
from everest.querying.specifications import cntd
from everest.querying.specifications import cnts
from everest.querying.specifications import desc
from everest.querying.specifications import ends
from everest.querying.specifications import eq
from everest.querying.specifications import ge
from everest.querying.specifications import gt
from everest.querying.specifications import le
from everest.querying.specifications import lt
from everest.querying.specifications import rng
from everest.querying.specifications import starts


__docformat__ = 'reStructuredText en'
__all__ = ['TestFilterSpecification',
           ]


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


class AlwaysTrueOperator(UnaryOperator):
    name = 'true'
    literal = 'T'

    @staticmethod
    def apply(arg): # pylint: disable=W0613
        return True


class AlwaysTrueFilterSpecification(FilterSpecification):

    operator = AlwaysTrueOperator

    def __init__(self):
        FilterSpecification.__init__(self)

    def is_satisfied_by(self, candidate):
        return self.operator.apply(candidate)

    def accept(self, visitor):
        pass


class AlwaysFalseOperator(UnaryOperator):
    name = 'false'
    literal = 'F'

    @staticmethod
    def apply(arg): # pylint: disable=W0613
        return False


class AlwaysFalseFilterSpecification(FilterSpecification):
    operator = AlwaysFalseOperator
    def is_satisfied_by(self, candidate):
        return False

    def accept(self, visitor):
        pass


class SpecificationCandidate(object):
    def __str__(self):
        attrs = ['%s: %s' % (k, getattr(self, k))
                 for k in self.__dict__
                 if not k.startswith('_')]
        return 'Candidate -> %s' % ', '.join(attrs)

    @classmethod
    def make_instance(self, **attributes):
        cand = SpecificationCandidate()
        for attr_name, attr_value in iteritems_(attributes):
            setattr(cand, attr_name, attr_value)
        return cand


@pytest.fixture
def specification_candidate_factory():
    return SpecificationCandidate.make_instance


@pytest.fixture
def specification_candidate(specification_candidate_factory): #pylint: disable=W0621
    return specification_candidate_factory(text_attr=TEXT_VALUE,
                                           number_attr=NUMBER_VALUE,
                                           date_attr=DATE_VALUE,
                                           list_attr=LIST_VALUES)


class TestFilterSpecification(object):

    def test_basics(self, filter_specification_factory):
        spec = filter_specification_factory.create_equal_to('foo', 'bar')
        assert spec == spec
        spec_other_attr = \
            filter_specification_factory.create_equal_to('bar', 'bar')
        assert spec != spec_other_attr
        spec_other_value = \
            filter_specification_factory.create_equal_to('foo', 'bar1')
        assert spec != spec_other_value
        str_str = '<%s op_name:' % spec.__class__.__name__
        assert str(spec)[:len(str_str)] == str_str

    @pytest.mark.parametrize('value,attr,outcome',
                             [(TEXT_VALUE, 'text_attr', True),
                              (GREATER_THAN_TEXT_VALUE, 'text_attr', False),
                              (NUMBER_VALUE, 'number_attr', True),
                              (GREATER_THAN_NUMBER_VALUE, 'number_attr',
                               False),
                              (DATE_VALUE, 'date_attr', True),
                              (GREATER_THAN_DATE_VALUE, 'date_attr', False),
                              ])
    def test_equal_to(self, filter_specification_factory,
                      specification_candidate, # pylint: disable=W0621
                      attr, value, outcome):
        spec = filter_specification_factory.create_equal_to(attr, value)
        assert spec.is_satisfied_by(specification_candidate) is outcome

    @pytest.mark.parametrize('value,attr,outcome',
                             [(LESS_THAN_TEXT_VALUE, 'text_attr', True),
                              (TEXT_VALUE, 'text_attr', False),
                              (LESS_THAN_NUMBER_VALUE, 'number_attr', True),
                              (NUMBER_VALUE, 'number_attr', False),
                              (LESS_THAN_DATE_VALUE, 'date_attr', True),
                              (DATE_VALUE, 'date_attr', False),
                              ])
    def test_greater_than(self, filter_specification_factory,
                          specification_candidate, # pylint: disable=W0621
                          attr, value, outcome):
        spec = filter_specification_factory.create_greater_than(attr, value)
        assert spec.is_satisfied_by(specification_candidate) is outcome

    @pytest.mark.parametrize('value,attr,outcome',
                             [(GREATER_THAN_TEXT_VALUE, 'text_attr', True),
                              (TEXT_VALUE, 'text_attr', False),
                              (GREATER_THAN_NUMBER_VALUE, 'number_attr',
                               True),
                              (NUMBER_VALUE, 'number_attr', False),
                              (GREATER_THAN_DATE_VALUE, 'date_attr', True),
                              (DATE_VALUE, 'date_attr', False),
                              ])
    def test_less_than(self, filter_specification_factory,
                       specification_candidate, # pylint: disable=W0621
                       attr, value, outcome):
        spec = filter_specification_factory.create_less_than(attr, value)
        assert spec.is_satisfied_by(specification_candidate) is outcome

    @pytest.mark.parametrize('value,attr,outcome',
                             [(LESS_THAN_TEXT_VALUE, 'text_attr', True),
                              (TEXT_VALUE, 'text_attr', True),
                              (GREATER_THAN_TEXT_VALUE, 'text_attr', False),
                              (LESS_THAN_NUMBER_VALUE, 'number_attr', True),
                              (NUMBER_VALUE, 'number_attr', True),
                              (GREATER_THAN_NUMBER_VALUE, 'number_attr',
                               False),
                              (LESS_THAN_DATE_VALUE, 'date_attr', True),
                              (DATE_VALUE, 'date_attr', True),
                              (GREATER_THAN_DATE_VALUE, 'date_attr', False),
                              ])
    def test_greater_than_or_equal_to(self,
                                      filter_specification_factory,
                                      specification_candidate, # pylint: disable=W0621
                                      attr, value, outcome):
        spec = \
          filter_specification_factory.create_greater_than_or_equal_to(attr,
                                                                       value)
        assert spec.is_satisfied_by(specification_candidate) is outcome

    @pytest.mark.parametrize('value,attr,outcome',
                             [(GREATER_THAN_TEXT_VALUE, 'text_attr', True),
                              (TEXT_VALUE, 'text_attr', True),
                              (LESS_THAN_TEXT_VALUE, 'text_attr', False),
                              (GREATER_THAN_NUMBER_VALUE, 'number_attr',
                               True),
                              (NUMBER_VALUE, 'number_attr', True),
                              (LESS_THAN_NUMBER_VALUE, 'number_attr', False),
                              (GREATER_THAN_DATE_VALUE, 'date_attr', True),
                              (DATE_VALUE, 'date_attr', True),
                              (LESS_THAN_DATE_VALUE, 'date_attr', False),
                              ])
    def test_less_than_or_equal_to(self, filter_specification_factory,
                                   specification_candidate, # pylint: disable=W0621
                                   attr, value, outcome):
        spec = \
            filter_specification_factory.create_less_than_or_equal_to(attr,
                                                                      value)
        assert spec.is_satisfied_by(specification_candidate) is outcome

    def test_in_range_basics(self, filter_specification_factory):
        spec = filter_specification_factory.create_in_range('foo',
                                                            ('bar0', 'bar1'))
        assert spec.from_value == 'bar0'
        assert spec.to_value == 'bar1'
        assert spec == spec
        spec_other_value = \
            filter_specification_factory.create_in_range('foo',
                                                         ('bar0', 'bar2'))
        assert spec != spec_other_value
        spec_other_attr = \
            filter_specification_factory.create_in_range('bar',
                                                         ('bar0', 'bar1'))
        assert spec != spec_other_attr

    @pytest.mark.parametrize('value1,value2,attr,outcome',
                             [(LESS_THAN_TEXT_VALUE, GREATER_THAN_TEXT_VALUE,
                               'text_attr', True),
                              (GREATER_THAN_TEXT_VALUE, LESS_THAN_TEXT_VALUE,
                               'text_attr', False),
                              (LESS_THAN_NUMBER_VALUE,
                               GREATER_THAN_NUMBER_VALUE, 'number_attr',
                               True),
                              (GREATER_THAN_DATE_VALUE,
                               LESS_THAN_DATE_VALUE, 'date_attr', False),
                              (LESS_THAN_DATE_VALUE, GREATER_THAN_DATE_VALUE,
                               'date_attr', True),
                              (GREATER_THAN_DATE_VALUE, LESS_THAN_DATE_VALUE,
                               'date_attr', False),
                              ])
    def test_in_range(self, filter_specification_factory,
                      specification_candidate, # pylint: disable=W0621
                      attr, value1, value2, outcome):
        spec = filter_specification_factory.create_in_range(attr,
                                                            (value1, value2))
        assert spec.is_satisfied_by(specification_candidate) is outcome

    @pytest.mark.parametrize('value,attr,outcome',
                             [(TEXT_VALUE[0], 'text_attr', True),
                              (GREATER_THAN_TEXT_VALUE[0], 'text_attr',
                               False),
                              (LIST_VALUES[0], 'list_attr', True),
                              (LIST_VALUES[-1], 'list_attr', False),
                              ])
    def test_starts_with(self, filter_specification_factory,
                         specification_candidate, # pylint: disable=W0621
                         attr, value, outcome):
        spec = filter_specification_factory.create_starts_with(attr, value)
        assert spec.is_satisfied_by(specification_candidate) is outcome

    @pytest.mark.parametrize('value,attr',
                             [(NUMBER_VALUE, 'number_attr'),
                              (DATE_VALUE, 'date_attr')
                              ])
    def test_starts_with_raises(self,
                                filter_specification_factory,
                                specification_candidate, # pylint: disable=W0621
                                attr, value):
        spec = filter_specification_factory.create_starts_with(attr, value)
        with pytest.raises(TypeError):
            spec.is_satisfied_by(specification_candidate)

    @pytest.mark.parametrize('value,attr,outcome',
                             [(TEXT_VALUE[-1], 'text_attr', True),
                              (GREATER_THAN_TEXT_VALUE[-1], 'text_attr',
                               False),
                              (LIST_VALUES[-1], 'list_attr', True),
                              (LIST_VALUES[0], 'list_attr', False),
                              ])
    def test_ends_with(self, filter_specification_factory,
                       specification_candidate, # pylint: disable=W0621
                       attr, value, outcome):
        spec = filter_specification_factory.create_ends_with(attr, value)
        assert spec.is_satisfied_by(specification_candidate) is outcome

    @pytest.mark.parametrize('value,attr',
                             [(NUMBER_VALUE, 'number_attr'),
                              (DATE_VALUE, 'date_attr')
                              ])
    def test_ends_with_raises(self,
                              filter_specification_factory,
                              specification_candidate, # pylint: disable=W0621
                              attr, value):
        spec = filter_specification_factory.create_ends_with(attr, value)
        with pytest.raises(TypeError):
            spec.is_satisfied_by(specification_candidate)

    @pytest.mark.parametrize('value,attr,outcome',
                             [(TEXT_VALUE[2], 'text_attr', True),
                              (GREATER_THAN_TEXT_VALUE[-1], 'text_attr',
                               False),
                              (LIST_VALUES[2], 'list_attr', True),
                              (-1, 'list_attr', False),
                              ])
    def test_contains(self, filter_specification_factory,
                      specification_candidate, # pylint: disable=W0621
                      attr, value, outcome):
        spec = filter_specification_factory.create_contains(attr, value)
        assert spec.is_satisfied_by(specification_candidate) is outcome

    @pytest.mark.parametrize('value,attr',
                             [(NUMBER_VALUE, 'number_attr'),
                              (DATE_VALUE, 'date_attr'),
                              ])
    def test_contains_raises(self,
                              filter_specification_factory,
                              specification_candidate, # pylint: disable=W0621
                              attr, value):
        spec = filter_specification_factory.create_contains(attr, value)
        with pytest.raises(TypeError):
            spec.is_satisfied_by(specification_candidate)

    @pytest.mark.parametrize('value,attr,outcome',
                             [(TEXT_VALUE_LIST, 'text_attr', True),
                              (LIST_VALUES, 'text_attr', False),
                              ])
    def test_contained(self, filter_specification_factory,
                      specification_candidate, # pylint: disable=W0621
                      attr, value, outcome):
        spec = filter_specification_factory.create_contained(attr, value)
        assert spec.is_satisfied_by(specification_candidate) is outcome

    @pytest.mark.parametrize('value,attr',
                             [(NUMBER_VALUE, 'number_attr'),
                              (DATE_VALUE, 'date_attr'),
                              ])
    def test_contained_raises(self,
                              filter_specification_factory,
                              specification_candidate, # pylint: disable=W0621
                              attr, value):
        spec = filter_specification_factory.create_contained(attr, value)
        with pytest.raises(TypeError):
            spec.is_satisfied_by(specification_candidate)

    def test_conjunction_basics(self, filter_specification_factory):
        always_true_spec = AlwaysTrueFilterSpecification()
        always_false_spec = AlwaysFalseFilterSpecification()
        spec = \
            filter_specification_factory.create_conjunction(always_true_spec,
                                                            always_false_spec)
        assert spec == spec
        other_spec = \
            filter_specification_factory.create_conjunction(always_false_spec,
                                                            always_true_spec)
        assert spec != other_spec
        str_str = '<%s left_spec:' % spec.__class__.__name__
        assert str(spec)[:len(str_str)] == str_str

    @pytest.mark.parametrize('left_spec,right_spec,outcome',
                             [(AlwaysTrueFilterSpecification(),
                               AlwaysTrueFilterSpecification(), True),
                              (AlwaysFalseFilterSpecification(),
                               AlwaysTrueFilterSpecification(), False),
                              (AlwaysTrueFilterSpecification(),
                               AlwaysFalseFilterSpecification(), False),
                              (AlwaysFalseFilterSpecification(),
                               AlwaysFalseFilterSpecification(), False),
                              ])
    def test_conjunction(self, filter_specification_factory,
                         specification_candidate_factory, #pylint: disable=W0621
                         left_spec, right_spec, outcome):
        spec = filter_specification_factory.create_conjunction(left_spec,
                                                               right_spec)
        cand = specification_candidate_factory()
        assert spec.is_satisfied_by(cand) is outcome

    @pytest.mark.parametrize('left_spec,right_spec,outcome',
                             [(AlwaysFalseFilterSpecification(),
                               AlwaysTrueFilterSpecification(), True),
                              (AlwaysTrueFilterSpecification(),
                               AlwaysFalseFilterSpecification(), True),
                              (AlwaysTrueFilterSpecification(),
                               AlwaysTrueFilterSpecification(), True),
                              (AlwaysFalseFilterSpecification(),
                               AlwaysFalseFilterSpecification(), False),
                              ])
    def test_disjunction(self, filter_specification_factory,
                         specification_candidate_factory, #pylint: disable=W0621
                         left_spec, right_spec, outcome):
        spec = filter_specification_factory.create_disjunction(left_spec,
                                                               right_spec)
        cand = specification_candidate_factory()
        assert spec.is_satisfied_by(cand) is outcome

    def test_negation_basics(self, filter_specification_factory):
        af_spec = AlwaysFalseFilterSpecification()
        spec = filter_specification_factory.create_negation(af_spec)
        assert spec == spec
        at_spec = AlwaysTrueFilterSpecification()
        other_spec = filter_specification_factory.create_negation(at_spec)
        assert spec != other_spec
        str_str = '<%s wrapped_spec:' % spec.__class__.__name__
        assert str(spec)[:len(str_str)] == str_str

    @pytest.mark.parametrize('wrapped_spec,outcome',
                             [(AlwaysFalseFilterSpecification(), True),
                              (AlwaysTrueFilterSpecification(), False)
                              ])
    def test_negation(self, filter_specification_factory,
                      specification_candidate_factory, #pylint: disable=W0621
                      wrapped_spec, outcome):
        spec = filter_specification_factory.create_negation(wrapped_spec)
        cand = specification_candidate_factory()
        assert spec.is_satisfied_by(cand) is outcome

    def test_order_basics(self, order_specification_factory):
        spec = order_specification_factory.create_ascending('foo')
        str_str = '<%s attr_name:' % spec.__class__.__name__
        assert str(spec)[:len(str_str)] == str_str

    @pytest.mark.parametrize('attr',
                             ['number_attr', 'text_attr'])
    def test_order_ascending(self, order_specification_factory,
                             specification_candidate_factory, #pylint: disable=W0621
                             attr):
        spec = order_specification_factory.create_ascending(attr)
        first_candidate = \
            specification_candidate_factory(number_attr=0, text_attr='a')
        second_candidate = \
            specification_candidate_factory(number_attr=1, text_attr='b')
        assert spec.attr_name == attr
        assert not spec.eq(first_candidate, second_candidate)
        assert spec.ne(first_candidate, second_candidate)
        assert spec.lt(first_candidate, second_candidate)
        assert not spec.ge(first_candidate, second_candidate)
        assert spec.le(first_candidate, second_candidate)
        assert not spec.gt(first_candidate, second_candidate)

    @pytest.mark.parametrize('attr',
                             ['number_attr', 'text_attr'])
    def test_order_descending(self, order_specification_factory,
                              specification_candidate_factory, #pylint: disable=W0621
                              attr):
        spec = order_specification_factory.create_descending(attr)
        first_candidate = \
            specification_candidate_factory(number_attr=0, text_attr='a')
        second_candidate = \
            specification_candidate_factory(number_attr=1, text_attr='b')
        assert spec.attr_name == attr
        assert not spec.eq(first_candidate, second_candidate)
        assert spec.ne(first_candidate, second_candidate)
        assert not spec.lt(first_candidate, second_candidate)
        assert spec.ge(first_candidate, second_candidate)
        assert not spec.le(first_candidate, second_candidate)
        assert spec.gt(first_candidate, second_candidate)

    def test_order_natural(self, order_specification_factory,
                           specification_candidate_factory): #pylint: disable=W0621
        text_spec = order_specification_factory.create_natural('text_attr')
        first_candidate = \
            specification_candidate_factory(number_attr=0, text_attr='a10')
        second_candidate = \
            specification_candidate_factory(number_attr=1, text_attr='a9')
        assert not text_spec.lt(first_candidate, second_candidate)
        number_spec = \
                order_specification_factory.create_natural('number_attr')
        assert number_spec.lt(first_candidate, second_candidate)

    def test_order_conjunction(self, order_specification_factory,
                               specification_candidate_factory): #pylint: disable=W0621
        text_spec = order_specification_factory.create_natural('text_attr')
        number_spec = \
                order_specification_factory.create_natural('number_attr')
        conj_spec = \
            order_specification_factory.create_conjunction(number_spec,
                                                           text_spec)
        first_candidate = \
            specification_candidate_factory(number_attr=0, text_attr='a')
        second_candidate = \
            specification_candidate_factory(number_attr=0, text_attr='b')
        str_str = '<%s left_spec:' % conj_spec.__class__.__name__
        assert str(conj_spec)[:len(str_str)] == str_str
        assert conj_spec.lt(first_candidate, second_candidate)
        assert conj_spec.le(first_candidate, second_candidate)
        assert not conj_spec.eq(first_candidate, second_candidate)
        assert conj_spec.cmp(first_candidate, second_candidate) == -1
        inv_conj_spec = \
            order_specification_factory.create_conjunction(text_spec,
                                                           number_spec)
        assert inv_conj_spec.lt(first_candidate, second_candidate)
        assert inv_conj_spec.le(first_candidate, second_candidate)
        assert not inv_conj_spec.eq(first_candidate, second_candidate)
        assert inv_conj_spec.cmp(first_candidate, second_candidate) == -1


class TestSpecificationGenerator(object):

    @pytest.mark.parametrize('attrs,generator',
                             [(dict(number_attr=NUMBER_VALUE,
                                    text_attr=TEXT_VALUE), eq),
                              (dict(text_attr=TEXT_VALUE[0]), starts),
                              (dict(text_attr=TEXT_VALUE[-1]), ends),
                              (dict(number_attr=NUMBER_VALUE + 1), lt),
                              (dict(number_attr=NUMBER_VALUE), le),
                              (dict(number_attr=NUMBER_VALUE - 1), gt),
                              (dict(number_attr=NUMBER_VALUE), ge),
                              (dict(text_attr=TEXT_VALUE[1:2]), cnts),
                              (dict(text_attr=TEXT_VALUE), cntd),
                              (dict(number_attr=(NUMBER_VALUE - 1,
                                                 NUMBER_VALUE + 1)), rng),
                               ])
    def test_plain_generators(self, configurator,
                              specification_candidate, attrs, #pylint: disable=W0621
                              generator):
        configurator.begin()
        try:
            spec = generator(**attrs)
            if len(attrs) > 1:
                assert isinstance(spec, ConjunctionFilterSpecification)
            assert spec.is_satisfied_by(specification_candidate)
        finally:
            configurator.end()

    @pytest.mark.parametrize('attrs,generator,outcome',
                             [(('number_attr', 'text_attr'), asc, True),
                              (('number_attr', 'text_attr'), desc, False),
                              ])
    def test_order_generators(self, configurator,
                              specification_candidate_factory, #pylint: disable=W0621
                              attrs, generator, outcome):
        first_candidate = \
             specification_candidate_factory(number_attr=NUMBER_VALUE,
                                             text_attr=TEXT_VALUE)
        second_candidate = \
             specification_candidate_factory(number_attr=NUMBER_VALUE,
                                             text_attr=GREATER_THAN_TEXT_VALUE)
        configurator.begin()
        try:
            spec = generator(*attrs)
            assert spec.lt(first_candidate, second_candidate) is outcome
        finally:
            configurator.end()

    def test_instantiating_generator(self, filter_specification_factory,
                                     specification_candidate): #pylint: disable=W0621
        gen = FilterSpecificationGenerator(filter_specification_factory)
        spec = gen.lt(number_attr=NUMBER_VALUE + 1) \
                & gen.gt(number_attr=NUMBER_VALUE - 1)
        assert spec.is_satisfied_by(specification_candidate)

    def test_generator_or(self, specification_candidate): #pylint: disable=W0621
        spec = lt(number_attr=NUMBER_VALUE + 1) \
                | gt(number_attr=NUMBER_VALUE + 1)
        assert spec.is_satisfied_by(specification_candidate)

    def test_and(self, specification_candidate): #pylint: disable=W0621
        spec = eq(number_attr=NUMBER_VALUE) & eq(text_attr=TEXT_VALUE)
        assert isinstance(spec, ConjunctionFilterSpecification)
        assert spec.is_satisfied_by(specification_candidate)

    def test_or(self, specification_candidate): #pylint: disable=W0621
        spec = eq(number_attr=NUMBER_VALUE - 1) | eq(text_attr=TEXT_VALUE)
        assert isinstance(spec, DisjunctionFilterSpecification)
        assert spec.is_satisfied_by(specification_candidate)

    def test_not(self, specification_candidate): #pylint: disable=W0621
        spec = ~eq(number_attr=NUMBER_VALUE - 1)
        assert isinstance(spec, NegationFilterSpecification)
        assert spec.is_satisfied_by(specification_candidate)
