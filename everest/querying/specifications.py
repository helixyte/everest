"""
Specifications.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The central idea of a Specification is to separate the statement of how to 
match a candidate from the candidate object that it is matched against.

Read http://en.wikipedia.org/wiki/Specification_pattern for more info and
especially http://www.martinfowler.com/apsupp/spec.pdf

Created on Jul 5, 2011.
"""
from everest.querying.base import Specification
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.interfaces import IOrderSpecificationFactory
from everest.querying.operators import ASCENDING
from everest.querying.operators import CONJUNCTION
from everest.querying.operators import CONTAINED
from everest.querying.operators import CONTAINS
from everest.querying.operators import DESCENDING
from everest.querying.operators import DISJUNCTION
from everest.querying.operators import ENDS_WITH
from everest.querying.operators import EQUAL_TO
from everest.querying.operators import GREATER_OR_EQUALS
from everest.querying.operators import GREATER_THAN
from everest.querying.operators import IN_RANGE
from everest.querying.operators import LESS_OR_EQUALS
from everest.querying.operators import LESS_THAN
from everest.querying.operators import NEGATION
from everest.querying.operators import STARTS_WITH
from everest.resources.interfaces import IResource
from pyramid.threadlocal import get_current_registry
from zope.interface import implements # pylint: disable=E0611,F0401
import re

__docformat__ = 'reStructuredText en'
__all__ = ['CompositeFilterSpecification',
           'ConjunctionFilterSpecification',
           'ConjuctionOrderSpecification',
           'CriterionFilterSpecification',
           'DescendingOrderSpecification',
           'DisjuctionFilterSpecification',
           'FilterSpecification',
           'FilterSpecificationFactory',
           'LeafFilterSpecification',
           'NaturalOrderSpecification',
           'NegationFilterSpecification',
           'ObjectOrderSpecification',
           'OrderSpecification',
           'OrderSpecificationFactory',
           'ValueContainedFilterSpecification',
           'ValueContainsFilterSpecification',
           'ValueEndsWithFilterSpecification',
           'ValueEqualToFilterSpecification',
           'ValueGreaterThanFilterSpecification',
           'ValueGreaterThanOrEqualToFilterSpecification',
           'ValueInRangeFilterSpecification',
           'ValueLessThanFilterSpecification',
           'ValueLessThanOrEqualToFilterSpecification',
           'ValueStartsWithFilterSpecification',
           ]


class FilterSpecification(Specification):
    """
    Abstract base class for all filter specifications.
    """

    def __init__(self):
        if self.__class__ is FilterSpecification:
            raise NotImplementedError('Abstract class')
        Specification.__init__(self)

    def is_satisfied_by(self, candidate):
        """
        Tells if the given candidate object matches this specification.

        :param candidate: the candidate object
        :type candidate: object
        :returns: True if the specification is met by the candidate.
        :rtype: bool
        """
        raise NotImplementedError('Abstract method')

    def and_(self, other):
        """
        Generative method to create a :class:`ConjunctionFilterSpecification`.

        :param other: the other specification
        :type other: :class:`FilterSpecification`
        :returns: a new conjuction specification
        :rtype: :class:`ConjunctionFilterSpecification`
        """
        return ConjunctionFilterSpecification(self, other)

    def or_(self, other):
        """
        Generative method to create a :class:`DisjuctionFilterSpecification`

        :param other: the other specification
        :type other: :class:`FilterSpecification`
        :returns: a new disjuction specification
        :rtype: :class:`DisjuctionFilterSpecification`
        """
        return DisjuctionFilterSpecification(self, other)

    def not_(self):
        """
        Generative method to create a :class:`NegationFilterSpecification`

        :returns: a new negation specification
        :rtype: :class:`NegationFilterSpecification`
        """
        return NegationFilterSpecification(self)


class LeafFilterSpecification(FilterSpecification): # still abstract pylint: disable=W0223
    """
    Abstract base class for specifications that represent leaves in a 
    specification tree.
    """

    def __init__(self):
        if self.__class__ is LeafFilterSpecification:
            raise NotImplementedError('Abstract class')
        FilterSpecification.__init__(self)

    def accept(self, visitor):
        visitor.visit_nullary(self)


class CriterionFilterSpecification(LeafFilterSpecification):
    """
    Abstract base class for specifications representing filter criteria.
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a filter specification for a query criterion.

        :param operator: operator
        :type operator: :class:`everest.querying.operators.Operator`
        :param attr_name: the candidate's attribute name
        :type attr_name: str
        :param attr_value: the value that satisfies the specification
        :type from_value: object
        """
        if self.__class__ is CriterionFilterSpecification:
            raise NotImplementedError('Abstract class')
        LeafFilterSpecification.__init__(self)
        self.__attr_name = attr_name
        self.__attr_value = attr_value

    def __eq__(self, other):
        return (isinstance(other, CriterionFilterSpecification)
                and self.attr_name == other.attr_name
                and self.attr_value == other.attr_value)

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        str_format = '<%s op_name: %s, attr_name: %s, attr_value: %s>'
        params = (self.__class__.__name__,
                  self.operator.name, self.attr_name, self.attr_value)
        return str_format % params

    @property
    def attr_name(self):
        return self.__attr_name

    @property
    def attr_value(self):
        return self.__attr_value

    def is_satisfied_by(self, candidate):
        cand_value = self._get_candidate_value(candidate)
        if IResource.providedBy(self.__attr_value): # pylint: disable=E1101
            attr_value = self.__attr_value.get_entity()
        else:
            attr_value = self.__attr_value
        return self.operator.apply(cand_value, attr_value)

    def _get_candidate_value(self, candidate):
        return getattr(candidate, self.attr_name)


class CompositeFilterSpecification(FilterSpecification):
    """
    Abstract base class for specifications that are composed of two other
    specifications.
    """

    def __init__(self, left_spec, right_spec):
        """
        Constructs a CompositeFilterSpecification

        :param left_spec: the left part of the composite specification
        :type left_spec: :class:`FilterSpecification`
        :param right_spec: the right part of the composite specification
        :type right_spec: :class:`FilterSpecification`
        """
        if self.__class__ is CompositeFilterSpecification:
            raise NotImplementedError('Abstract class')
        FilterSpecification.__init__(self)
        self.__left_spec = left_spec
        self.__right_spec = right_spec

    def __str__(self):
        str_format = '<%s left_spec: %s, right_spec: %s>'
        params = (self.__class__.__name__, self.left_spec, self.right_spec)
        return str_format % params

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and self.left_spec == other.left_spec
                and self.right_spec == other.right_spec)

    def __ne__(self, other):
        return not self.__eq__(other)

    def accept(self, visitor):
        self.left_spec.accept(visitor)
        self.right_spec.accept(visitor)
        visitor.visit_binary(self)

    @property
    def left_spec(self):
        return self.__left_spec

    @property
    def right_spec(self):
        return self.__right_spec

    def is_satisfied_by(self, candidate):
        return self.operator.apply(self.left_spec.is_satisfied_by(candidate),
                                   self.right_spec.is_satisfied_by(candidate))


class ConjunctionFilterSpecification(CompositeFilterSpecification):
    """
    Concrete conjuction specification.
    """

    operator = CONJUNCTION


class DisjuctionFilterSpecification(CompositeFilterSpecification):
    """
    Concrete disjuction specification.
    """

    operator = DISJUNCTION


class NegationFilterSpecification(FilterSpecification):
    """
    Concrete negation specification.
    """

    operator = NEGATION

    def __init__(self, wrapped_spec):
        """
        Constructs a NegationFilterSpecification

        :param wrapped: the wrapped specification
        :type wrapped: :class:`FilterSpecification`
        """
        FilterSpecification.__init__(self)
        self.__wrapped_spec = wrapped_spec

    def __eq__(self, other):
        """Equality operator"""
        return (isinstance(other, NegationFilterSpecification) and
                self.wrapped_spec == other.wrapped_spec)

    def __ne__(self, other):
        """Inequality operator"""
        return not (self == other)

    def __str__(self):
        str_format = '<%s wrapped_spec: %s>'
        params = (self.__class__.__name__, self.wrapped_spec)
        return str_format % params

    def is_satisfied_by(self, candidate):
        return self.operator.apply(
                                self.wrapped_spec.is_satisfied_by(candidate))

    def accept(self, visitor):
        self.wrapped_spec.accept(visitor)
        visitor.visit_unary(self)

    @property
    def wrapped_spec(self):
        return self.__wrapped_spec


class ValueStartsWithFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value starts with specification
    """

    operator = STARTS_WITH


class ValueEndsWithFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value ends with specification
    """

    operator = ENDS_WITH


class ValueContainsFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value contains specification
    """

    operator = CONTAINS


class ValueContainedFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value contained in a list of values specification
    """

    operator = CONTAINED


class ValueEqualToFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value equal to specification
    """

    operator = EQUAL_TO


class ValueGreaterThanFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value greater than specification
    """

    operator = GREATER_THAN


class ValueLessThanFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value less than specification
    """

    operator = LESS_THAN


class ValueGreaterThanOrEqualToFilterSpecification(
                                            CriterionFilterSpecification):
    """
    Concrete value greater than or equal to specification
    """

    operator = GREATER_OR_EQUALS


class ValueLessThanOrEqualToFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value less than or equal to specification
    """

    operator = LESS_OR_EQUALS


class ValueInRangeFilterSpecification(CriterionFilterSpecification):
    """
    Concrete specification for a range of values
    """

    operator = IN_RANGE

    @property
    def from_value(self):
        return self.attr_value[0]

    @property
    def to_value(self):
        return self.attr_value[1]


class FilterSpecificationFactory(object):
    """
    Filter specification factory.
    """

    implements(IFilterSpecificationFactory)

    def create_equal_to(self, attr_name, attr_value):
        return ValueEqualToFilterSpecification(attr_name, attr_value)

    def create_starts_with(self, attr_name, attr_value):
        return ValueStartsWithFilterSpecification(attr_name, attr_value)

    def create_ends_with(self, attr_name, attr_value):
        return ValueEndsWithFilterSpecification(attr_name, attr_value)

    def create_contains(self, attr_name, attr_value):
        return ValueContainsFilterSpecification(attr_name, attr_value)

    def create_contained(self, attr_name, attr_value):
        return ValueContainedFilterSpecification(attr_name, attr_value)

    def create_greater_than_or_equal_to(self, attr_name, attr_value):
        return ValueGreaterThanOrEqualToFilterSpecification(attr_name,
                                                            attr_value)

    def create_greater_than(self, attr_name, attr_value):
        return ValueGreaterThanFilterSpecification(attr_name, attr_value)

    def create_less_than_or_equal_to(self, attr_name, attr_value):
        return ValueLessThanOrEqualToFilterSpecification(attr_name, attr_value)

    def create_less_than(self, attr_name, attr_value):
        return ValueLessThanFilterSpecification(attr_name, attr_value)

    def create_in_range(self, attr_name, range_tuple):
        return ValueInRangeFilterSpecification(attr_name, range_tuple)

    def create_conjunction(self, left_spec, right_spec):
        return ConjunctionFilterSpecification(left_spec, right_spec)

    def create_disjunction(self, left_spec, right_spec):
        return DisjuctionFilterSpecification(left_spec, right_spec)

    def create_negation(self, wrapped):
        return NegationFilterSpecification(wrapped)


class OrderSpecification(Specification):

    def __init__(self):
        if self.__class__ is OrderSpecification:
            raise NotImplementedError('Abstract class')
        Specification.__init__(self)

    def eq(self, x, y):
        raise NotImplementedError('Abstract method')

    def lt(self, x, y):
        raise NotImplementedError('Abstract method')

    def le(self, x, y):
        raise NotImplementedError('Abstract method')

    def cmp(self, x, y):
        raise NotImplementedError('Abstract method')

    def ne(self, x, y):
        return not self.eq(x, y)

    def gt(self, x, y):
        return not self.le(x, y)

    def ge(self, x, y):
        return not self.lt(x, y)

    def and_(self, other):
        return ConjuctionOrderSpecification(self, other)


class ObjectOrderSpecification(OrderSpecification): # pylint: disable=W0223

    def __init__(self, attr_name):
        if self.__class__ is ObjectOrderSpecification:
            raise NotImplementedError('Abstract class')
        OrderSpecification.__init__(self)
        self.__attr_name = attr_name

    def __str__(self):
        str_format = '<%s attr_name: %s>'
        params = (self.__class__.__name__, self.attr_name)
        return str_format % params

    @property
    def attr_name(self):
        return self.__attr_name

    def eq(self, x, y):
        res = self.operator.apply(self._get_value(x), self._get_value(y))
        return res == 0

    def lt(self, x, y):
        res = self.operator.apply(self._get_value(x), self._get_value(y))
        return res == -1

    def le(self, x, y):
        res = self.operator.apply(self._get_value(x), self._get_value(y))
        return res == -1 or res == 0

    def cmp(self, x, y):
        return self.operator.apply(self._get_value(x), self._get_value(y))

    def accept(self, visitor):
        visitor.visit_nullary(self)

    def _get_value(self, obj):
        return getattr(obj, self.attr_name)


class AscendingOrderSpecification(ObjectOrderSpecification):

    operator = ASCENDING


class DescendingOrderSpecification(ObjectOrderSpecification):

    operator = DESCENDING


class NaturalOrderSpecification(ObjectOrderSpecification):
    """
    See http://www.codinghorror.com/blog/2007/12/sorting-for-humans-natural-sort-order.html
    """

    operator = ASCENDING

    def _get_value(self, obj):
        value = ObjectOrderSpecification._get_value(self, obj)
        if isinstance(value, basestring):
            res = [self.__convert(c) for c in re.split(r'([0-9]+)', value)]
        else:
            res = value
        return res

    def __convert(self, txt):
        return int(txt) if txt.isdigit() else txt


class ConjuctionOrderSpecification(OrderSpecification):

    operator = CONJUNCTION

    def __init__(self, left, right):
        OrderSpecification.__init__(self)
        self.__left = left
        self.__right = right

    def __str__(self):
        str_format = '<%s left: %s, right: %s>'
        params = (self.__class__.__name__, self.left, self.right)
        return str_format % params

    def eq(self, x, y):
        return self.left.eq(x, y) and self.right.eq(x, y)

    def lt(self, x, y):
        if self.left.eq(x, y):
            res = self.right.lt(x, y)
        else:
            res = self.left.lt(x, y)
        return res

    def le(self, x, y):
        if self.left.eq(x, y):
            res = self.right.le(x, y)
        else:
            res = self.left.le(x, y)
        return res

    def cmp(self, x, y):
        left_cmp = self.left.cmp(x, y)
        if left_cmp == 0:
            res = self.right.cmp(x, y)
        else:
            res = left_cmp
        return res

    @property
    def left(self):
        return self.__left

    @property
    def right(self):
        return self.__right

    def accept(self, visitor):
        self.__left.accept(visitor)
        self.__right.accept(visitor)
        visitor.visit_binary(self)


class OrderSpecificationFactory(object):
    """
    Order specification factory.
    """

    implements(IOrderSpecificationFactory)

    def create_ascending(self, attr_name):
        return AscendingOrderSpecification(attr_name)

    def create_descending(self, attr_name):
        return DescendingOrderSpecification(attr_name)

    def create_conjunction(self, left_spec, right_spec):
        return ConjuctionOrderSpecification(left_spec, right_spec)


class specification_attribute(object):
    """
    Helper descriptor for the :class:`SpecificationGenerator`.
    """
    def __init__(self, ifactory, attribute_name):
        self.attribute_name = attribute_name
        self.__ifactory = ifactory
        self.__factory = None

    def __get__(self, generator, generator_class):
        if generator is None:
            generator = SpecificationGenerator(self.factory,
                                               self.attribute_name)
        else:
            generator.attribute_name = self.attribute_name
        return generator

    @property
    def factory(self):
        if self.__factory is None:
            reg = get_current_registry()
            self.__factory = reg.queryUtility(self.__ifactory)
        return self.__factory


class SpecificationGenerator(object):
    """
    Helper class to simplify the generation of filter and order 
    specifications.
    """
    eq = specification_attribute(IFilterSpecificationFactory,
                                 'create_equal_to')
    starts = specification_attribute(IFilterSpecificationFactory,
                                     'create_starts_with')
    ends = specification_attribute(IFilterSpecificationFactory,
                                   'create_ends_with')
    lt = specification_attribute(IFilterSpecificationFactory,
                                 'create_less_than')
    le = specification_attribute(IFilterSpecificationFactory,
                                 'create_less_than_or_equal_to')
    gt = specification_attribute(IFilterSpecificationFactory,
                                 'create_greater_than')
    ge = specification_attribute(IFilterSpecificationFactory,
                                 'create_greater_than_or_equal_to')
    cnts = specification_attribute(IFilterSpecificationFactory,
                                   'create_contains')
    cntd = specification_attribute(IFilterSpecificationFactory,
                                   'create_contained')
    rng = specification_attribute(IFilterSpecificationFactory,
                                  'create_in_range')
    asc = specification_attribute(IOrderSpecificationFactory,
                                  'create_ascending')
    desc = specification_attribute(IOrderSpecificationFactory,
                                   'create_descending')

    def __init__(self, factory, attribute_name):
        self.factory = factory
        self.attribute_name = attribute_name
        self.spec = None

    def and_(self, other):
        self.spec = self.spec.and_(other.spec)
        return self

    def or_(self, other):
        self.spec = self.spec.or_(other.spec)
        return self

    def not_(self):
        self.spec = self.spec.not_()
        return self

    def __call__(self, *args, **kw):
        if self.spec is None:
            fn = getattr(self.factory, self.attribute_name)
        else:
            # By default, sequences of generatives are chained as
            # conjunctions.
            fn = getattr(self.factory, self.attribute_name)
        if args:
            value, = args
            spec = fn(value)
        else:
            (attr, value), = kw.items()
            spec = fn(attr, value)
        if self.spec is None:
            self.spec = spec
        else:
            self.spec = self.spec.and_(spec)
        return self


def eq(**kw):
    "Convenience function to create an equal_to specification."
    return SpecificationGenerator.eq(**kw)


def starts(**kw):
    "Convenience function to create a starts_with specification."
    return SpecificationGenerator.starts(**kw)


def ends(**kw):
    "Convenience function to create an ends_with specification."
    return SpecificationGenerator.ends(**kw)


def lt(**kw):
    "Convenience function to create a less_than specification."
    return SpecificationGenerator.lt(**kw)


def le(**kw):
    "Convenience function to create less_than_or_equal_to specification."
    return SpecificationGenerator.le(**kw)


def gt(**kw):
    "Convenience function to create a greater_than specification."
    return SpecificationGenerator.gt(**kw)


def ge(**kw):
    "Convenience function to create a greater_than_or_equal specification."
    return SpecificationGenerator.ge(**kw)


def cnts(**kw):
    "Convenience function to create a contains specification."
    return SpecificationGenerator.cnts(**kw)


def cntd(**kw):
    "Convenience function to create a contained specification."
    return SpecificationGenerator.cntd(**kw)


def rng(**kw):
    "Convenience function to create an in_range specification."
    return SpecificationGenerator.rng(**kw)


def asc(arg):
    "Convenience function to create an ascending specification."
    return SpecificationGenerator.asc(arg)


def desc(arg):
    "Convenience function to create a descending specification."
    return SpecificationGenerator.desc(arg)
