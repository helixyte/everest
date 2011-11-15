"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The central idea of a Specification is to separate the statement of how to match
a candidate, from the candidate object that it is matched against.

Read http://en.wikipedia.org/wiki/Specification_pattern for more info and
especially http://www.martinfowler.com/apsupp/spec.pdf

Created on Jul 5, 2011.
"""

from everest.interfaces import IFilterSpecificationFactory
from everest.interfaces import IOrderSpecificationFactory
from zope.interface import implements # pylint: disable=E0611,F0401
import re

__docformat__ = 'reStructuredText en'
__all__ = ['CompositeFilterSpecification',
           'ConjuctionFilterSpecification',
           'ConjuctionOrderSpecification',
           'DisjuctionFilterSpecification',
           'FilterSpecification',
           'FilterSpecificationFactory',
           'LeafFilterSpecification',
           'NaturalOrderSpecification',
           'NegationFilterSpecification',
           'ObjectOrderSpecification',
           'OrderSpecification',
           'OrderSpecificationFactory',
           'ReverseOrderSpecification',
           'SimpleOrderSpecification',
           'ValueBoundFilterSpecification',
           'ValueContainedFilterSpecification'
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


class FilterSpecification(object):
    """
    Abstract base class for all specifications
    """

    def __init__(self):
        if self.__class__ is FilterSpecification:
            raise NotImplementedError('Abstract class')

    def is_satisfied_by(self, candidate):
        """
        Tells if a candidate object matches some criteria

        :param candidate: the candidate object
        :type candidate: object
        :returns: True if all criteria are met by the candidate
        :rtype: bool
        """
        raise NotImplementedError('Abstract method')

    def accept(self, visitor):
        """
        Sends a request to a visitor

        When a specification "accepts" a visitor, it sends a request to the
        visitor that encodes the specifications's class. It also includes the
        specification as an argument.

        It is a double-dispatch operation. "Double-dispatch" simply means the
        operation that gets executed depends on the kind of request and the
        types of two receivers. Its meaning depends on two types: the Visitor's
        and the FilterSpecifications's. Double-dispatching lets visitors request
        different operations on each concrete FilterSpecification.

        The above is an abstract from GoF book on design patterns.

        :param visitor: a visitor that packages related operations
        :type visitor: :class:`everest.visitors.FilterSpecificationVisitor`
        """
        raise NotImplementedError('Abstract method')

    def and_(self, other):
        """
        Factory Method to create a ConjuctionFilterSpecification

        :param other: the other specification
        :type other: :class:`FilterSpecification`
        :returns: a new conjuction specification
        :rtype: :class:`ConjuctionFilterSpecification`
        """
        return ConjuctionFilterSpecification(self, other)

    def or_(self, other):
        """
        Factory Method to create a DisjuctionFilterSpecification

        :param other: the other specification
        :type other: :class:`FilterSpecification`
        :returns: a new disjuction specification
        :rtype: :class:`DisjuctionFilterSpecification`
        """
        return DisjuctionFilterSpecification(self, other)

    def not_(self):
        """
        Factory Method to create a NegationFilterSpecification

        :returns: a new negation specification
        :rtype: :class:`NegationFilterSpecification`
        """
        return NegationFilterSpecification(self)


class LeafFilterSpecification(FilterSpecification): # still abstract pylint:disable=W0223
    """
    Abstract base class for leaf specifications
    """

    def __init__(self):
        if self.__class__ is LeafFilterSpecification:
            raise NotImplementedError('Abstract class')
        FilterSpecification.__init__(self)


class ValueBoundFilterSpecification(LeafFilterSpecification): # still abstract pylint:disable=W0223
    """
    Abstract base class for value bound specifications
    """

    __attr_name = None
    __attr_value = None

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueBoundFilterSpecification

        :param attr_name: the candidate's attribute name
        :type attr_name: str
        :param attr_value: the value that satisfies the specification
        :type from_value: object
        """
        LeafFilterSpecification.__init__(self)
        if self.__class__ is ValueBoundFilterSpecification:
            raise NotImplementedError('Abstract class')
        self.__attr_name = attr_name
        self.__attr_value = attr_value

    def __eq__(self, other):
        """Equality operator"""
        return (isinstance(other, ValueBoundFilterSpecification) and
                self.attr_name == other.attr_name and
                self.attr_value == other.attr_value)

    def __ne__(self, other):
        """Inequality operator"""
        return not (self == other)

    def __repr__(self):
        str_format = '<%s attr_name: %s, attr_value: %s>'
        params = (self.__class__.__name__, self.attr_name, self.attr_value)
        return str_format % params

    @property
    def attr_name(self):
        return self.__attr_name

    @property
    def attr_value(self):
        return self.__attr_value

    def _get_candidate_value(self, candidate):
        return getattr(candidate, self.attr_name)


class CompositeFilterSpecification(FilterSpecification):
    """
    Abstract base class for composite specifications
    """

    __left_spec = None
    __right_spec = None

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

    def __repr__(self):
        str_format = '<%s left_spec: %s, right_spec: %s>'
        params = (self.__class__.__name__, self.left_spec, self.right_spec)
        return str_format % params

    def accept(self, visitor):
        """
        Template Method - DO NOT OVERRIDE
        """
        self._contents_accept_visitor(visitor)
        self._accept_visitor(visitor)

    @property
    def left_spec(self):
        return self.__left_spec

    @property
    def right_spec(self):
        return self.__right_spec

    def _contents_accept_visitor(self, visitor):
        self.left_spec.accept(visitor)
        self.right_spec.accept(visitor)

    def _accept_visitor(self, visitor):
        raise NotImplementedError('Abstract method')


class ConjuctionFilterSpecification(CompositeFilterSpecification):
    """
    Concrete conjuction specification
    """

    def __init__(self, left_spec, right_spec):
        """
        Constructs a ConjuctionFilterSpecification
        """
        CompositeFilterSpecification.__init__(self, left_spec, right_spec)

    def __eq__(self, other):
        """Equality operator"""
        return (isinstance(other, ConjuctionFilterSpecification) and
                self.left_spec == other.left_spec and
                self.right_spec == other.right_spec)

    def __ne__(self, other):
        """Inequality operator"""
        return not (self == other)

    def is_satisfied_by(self, candidate):
        """
        Tells if both the left and right specifications are satisfied

        :returns: True if both the left and right specifications are satisfied
        :rtype: bool
        """
        return self.left_spec.is_satisfied_by(candidate) and \
               self.right_spec.is_satisfied_by(candidate)

    def _accept_visitor(self, visitor):
        visitor.visit_conjuction(self)


class DisjuctionFilterSpecification(CompositeFilterSpecification):
    """
    Concrete disjuction specification
    """

    def __init__(self, left_spec, right_spec):
        """
        Constructs a DisjuctionFilterSpecification
        """
        CompositeFilterSpecification.__init__(self, left_spec, right_spec)

    def __eq__(self, other):
        """Equality operator"""
        return (isinstance(other, DisjuctionFilterSpecification) and
                self.left_spec == other.left_spec and
                self.right_spec == other.right_spec)

    def __ne__(self, other):
        """Inequality operator"""
        return not (self == other)

    def is_satisfied_by(self, candidate):
        """
        Tells if either the left or right specification is satisfied

        :returns: True if either the left or right specification is satisfied
        :rtype: bool
        """
        return self.left_spec.is_satisfied_by(candidate) or \
               self.right_spec.is_satisfied_by(candidate)

    def _accept_visitor(self, visitor):
        visitor.visit_disjuction(self)


class NegationFilterSpecification(FilterSpecification):
    """
    Concrete negation specification
    """

    __wrapped_spec = None

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

    def __repr__(self):
        str_format = '<%s wrapped_spec: %s>'
        params = (self.__class__.__name__, self.wrapped_spec)
        return str_format % params

    def is_satisfied_by(self, candidate):
        """
        Inverses the result of the wrapped specification

        :returns: True if the wrapped specification is not satisfied
        :rtype: bool
        """
        return not self.wrapped_spec.is_satisfied_by(candidate)

    def accept(self, visitor):
        self.wrapped_spec.accept(visitor)
        visitor.visit_negation(self)

    @property
    def wrapped_spec(self):
        return self.__wrapped_spec


class ValueStartsWithFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete value starts with specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueStartsWithFilterSpecification
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, attr_value)

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value starts with the criterion

        :returns: True if the candidate's attribute value starts with the criterion
        :rtype: bool

        :raises: `TypeError` if candidate's value is unsubscriptable
        """
        value = self._get_candidate_value(candidate)
        if isinstance(value, basestring):
            return value.startswith(self.attr_value)
        else:
            return value[0] == self.attr_value

    def accept(self, visitor):
        visitor.visit_value_starts_with(self)


class ValueEndsWithFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete value ends with specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueEndsWithFilterSpecification
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, attr_value)

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value ends with the criterion

        :returns: True if the candidate's attribute value ends with the criterion
        :rtype: bool

        :raises: `TypeError` if candidate's value is unsubscriptable
        """
        value = self._get_candidate_value(candidate)
        if isinstance(value, basestring):
            return value.endswith(self.attr_value)
        else:
            return value[-1] == self.attr_value

    def accept(self, visitor):
        visitor.visit_value_ends_with(self)


class ValueContainsFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete value contains specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueContainsFilterSpecification
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, attr_value)

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value contains the criterion

        :returns: True if the candidate's attribute value contains the criterion
        :rtype: bool

        :raises: `TypeError` if candidate's value is not iterable
        """
        value = self._get_candidate_value(candidate)
        return self.attr_value in value

    def accept(self, visitor):
        visitor.visit_value_contains(self)


class ValueContainedFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete value contained in a list of values specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueContainedFilterSpecification

        :type attr_value: any sequence
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, attr_value)

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value is contained in the
        criterion sequence

        :returns: True if the candidate's attribute value is contained in the
                  criterion sequence
        :rtype: bool

        :raises: `TypeError` if the criterion's value is not iterable
        """
        value = self._get_candidate_value(candidate)
        return  value in self.attr_value

    def accept(self, visitor):
        visitor.visit_value_contained(self)


class ValueEqualToFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete value equal to specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueEqualToFilterSpecification
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, attr_value)

    def __str__(self):
        return '<ValueEqualToFilterSpecification: %s == %s>' % (self.attr_name,
                                                          self.attr_value)

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value equals to the criterion

        :returns: True if the candidate's attribute value equals to the criterion
        :rtype: bool
        """
        value = self._get_candidate_value(candidate)
        return self.attr_value == value

    def accept(self, visitor):
        visitor.visit_value_equal_to(self)


class ValueGreaterThanFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete value greater than specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueGreaterThanFilterSpecification
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, attr_value)

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value is greater than the criterion

        :returns: True if the candidate's attribute value is greater than
                  the criterion
        :rtype: bool
        """
        value = self._get_candidate_value(candidate)
        return value > self.attr_value

    def accept(self, visitor):
        visitor.visit_value_greater_than(self)


class ValueLessThanFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete value less than specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueLessThanFilterSpecification
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, attr_value)

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value is less than the criterion

        :returns: True if the candidate's attribute value is less than
                  the criterion
        :rtype: bool
        """
        value = self._get_candidate_value(candidate)
        return value < self.attr_value

    def accept(self, visitor):
        visitor.visit_value_less_than(self)


class ValueGreaterThanOrEqualToFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete value greater than or equal to specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueGreaterThanOrEqualToFilterSpecification
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, attr_value)

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value is greater than or equal to
        the criterion

        :returns: True if the candidate's attribute value is greater than or
                  equal to the criterion
        :rtype: bool
        """
        value = self._get_candidate_value(candidate)
        return value >= self.attr_value

    def accept(self, visitor):
        visitor.visit_value_greater_than_or_equal_to(self)


class ValueLessThanOrEqualToFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete value less than or equal to specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueLessThanOrEqualToFilterSpecification
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, attr_value)

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value is less than or equal to
        the criterion

        :returns: True if the candidate's attribute value is less than or
                  equal to the criterion
        :rtype: bool
        """
        value = self._get_candidate_value(candidate)
        return value <= self.attr_value

    def accept(self, visitor):
        visitor.visit_value_less_than_or_equal_to(self)


class ValueInRangeFilterSpecification(ValueBoundFilterSpecification):
    """
    Concrete specification for a range of values
    """

    def __init__(self, attr_name, from_value, to_value):
        """
        Constructs a ValueInRangeFilterSpecification

        :param attr_name: the candidate's attribute name
        :type attr_name: str
        :param from_value: the lower limit of the range
        :type from_value: object
        :param to_value: the upper limit of the range
        :type to_value: object
        """
        ValueBoundFilterSpecification.__init__(self, attr_name, (from_value, to_value))

    def is_satisfied_by(self, candidate):
        """
        Tells if the candidate's attribute value is in range

        :returns: True if the candidate's attribute value is in range
        :rtype: bool
        """
        value = self._get_candidate_value(candidate)
        return self.from_value <= value <= self.to_value

    def accept(self, visitor):
        visitor.visit_value_in_range(self)

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

    def create_in_range(self, attr_name, from_value, to_value):
        return ValueInRangeFilterSpecification(attr_name, from_value, to_value)

    def create_conjunction(self, left_spec, right_spec):
        return ConjuctionFilterSpecification(left_spec, right_spec)

    def create_disjunction(self, left_spec, right_spec):
        return DisjuctionFilterSpecification(left_spec, right_spec)

    def create_negation(self, wrapped):
        return NegationFilterSpecification(wrapped)


class OrderSpecification(object):

    def __init__(self):
        if self.__class__ is OrderSpecification:
            raise NotImplementedError('Abstract class')

    def accept(self, visitor):
        raise NotImplementedError('Abstract method')

    def eq(self, x, y):
        raise NotImplementedError('Abstract method')

    def lt(self, x, y):
        raise NotImplementedError('Abstract method')

    def ne(self, x, y):
        return not self.eq(x, y)

    def le(self, x, y):
        return self.lt(x, y) or self.eq(x, y)

    def gt(self, x, y):
        return not self.le(x, y)

    def ge(self, x, y):
        return not self.lt(x, y)

    def and_(self, other):
        return ConjuctionOrderSpecification(self, other)

    def reverse(self):
        return ReverseOrderSpecification(self)


class ObjectOrderSpecification(OrderSpecification): # pylint: disable=W0223

    __attr_name = None

    def __init__(self, attr_name):
        if self.__class__ is ObjectOrderSpecification:
            raise NotImplementedError('Abstract class')
        OrderSpecification.__init__(self)
        self.__attr_name = attr_name

    def __repr__(self):
        str_format = '<%s attr_name: %s>'
        params = (self.__class__.__name__, self.attr_name)
        return str_format % params

    @property
    def attr_name(self):
        return self.__attr_name

    def _get_value(self, obj):
        return getattr(obj, self.attr_name)


class SimpleOrderSpecification(ObjectOrderSpecification):

    def __init__(self, attr_name):
        ObjectOrderSpecification.__init__(self, attr_name)

    def eq(self, x, y):
        return self._get_value(x) == self._get_value(y)

    def lt(self, x, y):
        return self._get_value(x) < self._get_value(y)

    def accept(self, visitor):
        visitor.visit_simple(self)


class ReverseOrderSpecification(OrderSpecification):

    __order = None

    def __init__(self, order):
        OrderSpecification.__init__(self)
        self.__order = order

    def __repr__(self):
        str_format = '<%s wrapped_order: %s>'
        params = (self.__class__.__name__, self.__order)
        return str_format % params

    def eq(self, x, y):
        return self.__order.eq(y, x)

    def lt(self, x, y):
        return self.__order.lt(y, x)

    def ne(self, x, y):
        return self.__order.ne(y, x)

    def le(self, x, y):
        return self.__order.le(y, x)

    def gt(self, x, y):
        return self.__order.gt(y, x)

    def ge(self, x, y):
        return self.__order.ge(y, x)

    def accept(self, visitor):
        self.__order.accept(visitor)
        visitor.visit_reverse(self)

    @property
    def wrapped(self):
        return self.__order


class NaturalOrderSpecification(ObjectOrderSpecification):
    """
    See http://www.codinghorror.com/blog/2007/12/sorting-for-humans-natural-sort-order.html
    """

    def __init__(self, attr_name):
        ObjectOrderSpecification.__init__(self, attr_name)

    def eq(self, x, y):
        return self._get_natural_value(x) == self._get_natural_value(y)

    def lt(self, x, y):
        return self._get_natural_value(x) < self._get_natural_value(y)

    def accept(self, visitor):
        visitor.visit_natural(self)

    def _get_natural_value(self, obj):
        value = self._get_value(obj)
        if isinstance(value, basestring):
            return [self.__convert(c) for c in re.split(r'([0-9]+)', value)]
        else:
            return value

    def __convert(self, txt):
        return int(txt) if txt.isdigit() else txt


class ConjuctionOrderSpecification(OrderSpecification):

    __left = None
    __right = None

    def __init__(self, left, right):
        OrderSpecification.__init__(self)
        self.__left = left
        self.__right = right

    def __repr__(self):
        str_format = '<%s left: %s, right: %s>'
        params = (self.__class__.__name__, self.left, self.right)
        return str_format % params

    def eq(self, x, y):
        return self.left.eq(x, y) and self.right.eq(x, y)

    def lt(self, x, y):
        return self.right.lt(x, y) if self.left.eq(x, y) else self.left.lt(x, y)

    @property
    def left(self):
        return self.__left

    @property
    def right(self):
        return self.__right

    def accept(self, visitor):
        self.__left.accept(visitor)
        self.__right.accept(visitor)
        visitor.visit_conjunction(self)


class OrderSpecificationFactory(object):
    """
    Order specification factory.
    """

    implements(IOrderSpecificationFactory)

    def create_simple(self, attr_name):
        return SimpleOrderSpecification(attr_name)

    def create_natural(self, attr_name):
        # FIXME: implement. # pylint: disable-msg=W0511
        raise NotImplementedError('TBD')

    def create_starts_with(self, attr_name):
        return NaturalOrderSpecification(attr_name)
