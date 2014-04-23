"""
Query specifications.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The central idea of a Specification is to separate the statement of how to
match a candidate from the candidate object that it is matched against.

Read http://en.wikipedia.org/wiki/Specification_pattern for more info and
especially http://www.martinfowler.com/apsupp/spec.pdf

Created on Jul 5, 2011.
"""
import re

from pyramid.compat import string_types
from pyramid.threadlocal import get_current_registry

from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.interfaces import IOrderSpecificationFactory
from everest.querying.interfaces import ISpecification
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
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.utils import get_nested_attribute
from zope.interface import implementer # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['AscendingOrderSpecification',
           'CompositeFilterSpecification',
           'ConjunctionFilterSpecification',
           'ConjunctionOrderSpecification',
           'CriterionFilterSpecification',
           'DescendingOrderSpecification',
           'DisjunctionFilterSpecification',
           'FilterSpecification',
           'FilterSpecificationFactory',
           'LeafFilterSpecification',
           'NaturalOrderSpecification',
           'NegationFilterSpecification',
           'ObjectOrderSpecification',
           'OrderSpecification',
           'OrderSpecificationFactory',
           'Specification',
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
           'asc',
           'cnts',
           'cntd',
           'desc',
           'eq',
           'ends',
           'ge',
           'gt',
           'le',
           'lt',
           'order',
           'rng',
           'starts',
           ]


@implementer(ISpecification)
class Specification(object):
    """
    Abstract base classs for all specifications.
    """
    operator = None

    def __init__(self):
        if self.__class__ is Specification:
            raise NotImplementedError('Abstract class')

    def accept(self, visitor):
        raise NotImplementedError('Abstract method')


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

    def __and__(self, other):
        return ConjunctionFilterSpecification(self, other)

    def __or__(self, other):
        return DisjunctionFilterSpecification(self, other)

    def __invert__(self):
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
        self.attr_name = attr_name
        self.attr_value = attr_value

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

    def is_satisfied_by(self, candidate):
        cand_value = self._get_candidate_value(candidate)
        if IMemberResource.providedBy(self.attr_value): # pylint: disable=E1101
            attr_value = self.attr_value.get_entity()
        elif ICollectionResource.providedBy(self.attr_value): # pylint: disable=E1101
            attr_value = self.attr_value.get_aggregate()
        else:
            attr_value = self.attr_value
        return self.operator.apply(cand_value, attr_value)

    def _get_candidate_value(self, candidate):
        attr_func = get_nested_attribute if '.' in self.attr_name else getattr
        return attr_func(candidate, self.attr_name)


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
    Concrete conjunction filter specification.
    """
    operator = CONJUNCTION


class DisjunctionFilterSpecification(CompositeFilterSpecification):
    """
    Concrete disjuction filter specification.
    """
    operator = DISJUNCTION


class NegationFilterSpecification(FilterSpecification):
    """
    Concrete negation specification.
    """
    operator = NEGATION

    def __init__(self, wrapped_spec):
        """
        Constructs a NegationFilterSpecification.

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
        """
        Returns the wrapped (negated) specification.
        """
        return self.__wrapped_spec


class ValueStartsWithFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value starts with specification.
    """
    operator = STARTS_WITH


class ValueEndsWithFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value ends with specification.
    """
    operator = ENDS_WITH


class ValueContainsFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value contains specification.
    """
    operator = CONTAINS


class ValueContainedFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value contained in a list of values specification.
    """
    operator = CONTAINED


class ValueEqualToFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value equal to specification.
    """
    operator = EQUAL_TO


class ValueGreaterThanFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value greater than specification.
    """
    operator = GREATER_THAN


class ValueLessThanFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value less than specification.
    """
    operator = LESS_THAN


class ValueGreaterThanOrEqualToFilterSpecification(
                                            CriterionFilterSpecification):
    """
    Concrete value greater than or equal to specification.
    """
    operator = GREATER_OR_EQUALS


class ValueLessThanOrEqualToFilterSpecification(CriterionFilterSpecification):
    """
    Concrete value less than or equal to specification.
    """
    operator = LESS_OR_EQUALS


class ValueInRangeFilterSpecification(CriterionFilterSpecification):
    """
    Concrete specification for a range of values.
    """
    operator = IN_RANGE

    @property
    def from_value(self):
        """
        Returns the first (FROM) value from the range specification.
        """
        return self.attr_value[0]

    @property
    def to_value(self):
        """
        Returns the second (TO) value from the range specification.
        """
        return self.attr_value[1]


@implementer(IFilterSpecificationFactory)
class FilterSpecificationFactory(object):
    """
    Filter specification factory.
    """
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
        return DisjunctionFilterSpecification(left_spec, right_spec)

    def create_negation(self, wrapped):
        return NegationFilterSpecification(wrapped)


class OrderSpecification(Specification):
    """
    Abstract base class for all order specifications.
    """
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

    def __and__(self, other):
        return ConjunctionOrderSpecification(self, other)


class ObjectOrderSpecification(OrderSpecification): # pylint: disable=W0223
    """
    Abstract base class for all order specifications operating on object
    attributes.
    """
    def __init__(self, attr_name):
        if self.__class__ is ObjectOrderSpecification:
            raise NotImplementedError('Abstract class')
        OrderSpecification.__init__(self)
        self.__attr_name = attr_name
        self.__attr_func = \
                get_nested_attribute if '.' in attr_name else getattr

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
        return self.__attr_func(obj, self.attr_name)


class AscendingOrderSpecification(ObjectOrderSpecification):
    """
    Concrete ascending order specification.
    """
    operator = ASCENDING


class DescendingOrderSpecification(ObjectOrderSpecification):
    """
    Concrete descending order specification.
    """
    operator = DESCENDING


class NaturalOrderSpecification(ObjectOrderSpecification):
    """
    See http://www.codinghorror.com/blog/2007/12/sorting-for-humans-natural-sort-order.html
    """
    operator = ASCENDING

    def _get_value(self, obj):
        value = ObjectOrderSpecification._get_value(self, obj)
        if isinstance(value, string_types):
            res = [self.__convert(c) for c in re.split(r'([0-9]+)', value)]
        else:
            res = value
        return res

    def __convert(self, txt):
        return int(txt) if txt.isdigit() else txt


class ConjunctionOrderSpecification(OrderSpecification):
    """
    Concrete conjunction order specification.
    """
    operator = CONJUNCTION

    def __init__(self, left, right):
        OrderSpecification.__init__(self)
        self.__left = left
        self.__right = right

    def __str__(self):
        str_format = '<%s left_spec: %s, right_spec: %s>'
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


@implementer(IOrderSpecificationFactory)
class OrderSpecificationFactory(object):
    """
    Order specification factory.
    """
    def create_ascending(self, attr_name):
        return AscendingOrderSpecification(attr_name)

    def create_descending(self, attr_name):
        return DescendingOrderSpecification(attr_name)

    def create_natural(self, attr_name):
        return NaturalOrderSpecification(attr_name)

    def create_conjunction(self, left_spec, right_spec):
        return ConjunctionOrderSpecification(left_spec, right_spec)


class specification_attribute(object):
    """
    Helper descriptor for the :class:`SpecificationGenerator`.
    """
    def __init__(self, ifactory, method_name):
        self.__method_name = method_name
        self.__ifactory = ifactory
        self.__factory = None

    def __get__(self, generator, generator_class):
        if generator is None:
            generator = generator_class(self.factory)
        generator.method_name = self.__method_name
        return generator

    @property
    def factory(self):
        if self.__factory is None:
            reg = get_current_registry()
            self.__factory = reg.queryUtility(self.__ifactory)
        return self.__factory


class _SpecificationGenerator(object):
    """
    Base class for specification generators.
    """
    def __init__(self, factory):
        self._factory = factory
        self.method_name = None


class FilterSpecificationGenerator(_SpecificationGenerator):
    """
    Helper class to simplify the generation of filter specifications.
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

    def __call__(self, **kw):
        fn = getattr(self._factory, self.method_name)
        spec = None
        for (attr, value) in kw.items():
            if spec is None:
                spec = fn(attr, value)
            else:
                spec = spec & fn(attr, value)
        return spec


class SingleOrderSpecificationGenerator(_SpecificationGenerator):
    """
    Helper class to simplify the generation of order specifications.
    """
    asc = specification_attribute(IOrderSpecificationFactory,
                                  'create_ascending')
    desc = specification_attribute(IOrderSpecificationFactory,
                                   'create_descending')

    def __call__(self, *args):
        fn = getattr(self._factory, self.method_name)
        spec = None
        for attr in args:
            if spec is None:
                spec = fn(attr)
            else:
                spec = spec & (fn(attr))
        return spec


class GenericOrderSpecificationGenerator(_SpecificationGenerator):
    """
    Helper class to simplify the generation of generic order specifications.
    """
    order = specification_attribute(IOrderSpecificationFactory, None)

    def __call__(self, *args):
        spec = None
        for order_crit in args:
            name, order_op = order_crit
            if order_op == ASCENDING:
                fn = self._factory.create_ascending
            elif order_op == DESCENDING:
                fn = self._factory.create_descending
            else:
                raise ValueError('Invalid ordering operator "%s".' % order_op)
            item_spec = fn(name)
            if spec is None:
                spec = item_spec
            else:
                spec &= item_spec
        return spec


def eq(**kw):
    "Convenience function to create an equal_to specification."
    return FilterSpecificationGenerator.eq(**kw)


def starts(**kw):
    "Convenience function to create a starts_with specification."
    return FilterSpecificationGenerator.starts(**kw)


def ends(**kw):
    "Convenience function to create an ends_with specification."
    return FilterSpecificationGenerator.ends(**kw)


def lt(**kw):
    "Convenience function to create a less_than specification."
    return FilterSpecificationGenerator.lt(**kw)


def le(**kw):
    "Convenience function to create less_than_or_equal_to specification."
    return FilterSpecificationGenerator.le(**kw)


def gt(**kw):
    "Convenience function to create a greater_than specification."
    return FilterSpecificationGenerator.gt(**kw)


def ge(**kw):
    "Convenience function to create a greater_than_or_equal specification."
    return FilterSpecificationGenerator.ge(**kw)


def cnts(**kw):
    "Convenience function to create a contains specification."
    return FilterSpecificationGenerator.cnts(**kw)


def cntd(**kw):
    "Convenience function to create a contained specification."
    return FilterSpecificationGenerator.cntd(**kw)


def rng(**kw):
    "Convenience function to create an in_range specification."
    return FilterSpecificationGenerator.rng(**kw)


def asc(*args):
    "Convenience function to create an ascending order specification."
    return SingleOrderSpecificationGenerator.asc(*args)


def desc(*args):
    "Convenience function to create a descending order specification."
    return SingleOrderSpecificationGenerator.desc(*args)


def order(*args):
    "Convenience function to create an order specification."
    return GenericOrderSpecificationGenerator.order(*args)
