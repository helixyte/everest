"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

The central idea of a Specification is to separate the statement of how to match
a candidate, from the candidate object that it is matched against.

Read http://en.wikipedia.org/wiki/Specification_pattern for more info and
especially http://www.martinfowler.com/apsupp/spec.pdf

Created on Jul 5, 2011.
"""

__docformat__ = 'reStructuredText en'
__all__ = ['Specification',
           'LeafSpecification',
           'ValueBoundSpecification',
           'CompositeSpecification',
           'ConjuctionSpecification',
           'DisjuctionSpecification',
           'NegationSpecification',
           'ValueStartsWithSpecification',
           'ValueEndsWithSpecification',
           'ValueContainsSpecification',
           'ValueContainedSpecification'
           'ValueEqualToSpecification',
           'ValueGreaterThanSpecification',
           'ValueLessThanSpecification',
           'ValueGreaterThanOrEqualToSpecification',
           'ValueLessThanOrEqualToSpecification',
           'ValueInRangeSpecification',
           'AbstractSpecificationFactory',
           'SpecificationFactory',
           ]


class Specification(object):
    """
    Abstract base class for all specifications
    """

    def __init__(self):
        if self.__class__ is Specification:
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
        and the Specifications's. Double-dispatching lets visitors request
        different operations on each concrete Specification.

        The above is an abstract from GoF book on design patterns.

        :param visitor: a visitor that packages related operations
        :type visitor: :class:`everest.visitors.SpecificationVisitor`
        """
        raise NotImplementedError('Abstract method')

    def and_(self, other):
        """
        Factory Method to create a ConjuctionSpecification

        :param other: the other specification
        :type other: :class:`Specification`
        :returns: a new conjuction specification
        :rtype: :class:`ConjuctionSpecification`
        """
        return ConjuctionSpecification(self, other)

    def or_(self, other):
        """
        Factory Method to create a DisjuctionSpecification

        :param other: the other specification
        :type other: :class:`Specification`
        :returns: a new disjuction specification
        :rtype: :class:`DisjuctionSpecification`
        """
        return DisjuctionSpecification(self, other)

    def not_(self):
        """
        Factory Method to create a NegationSpecification

        :returns: a new negation specification
        :rtype: :class:`NegationSpecification`
        """
        return NegationSpecification(self)


class LeafSpecification(Specification): # still abstract pylint:disable=W0223
    """
    Abstract base class for leaf specifications
    """

    def __init__(self):
        if self.__class__ is LeafSpecification:
            raise NotImplementedError('Abstract class')
        Specification.__init__(self)


class ValueBoundSpecification(LeafSpecification): # still abstract pylint:disable=W0223
    """
    Abstract base class for value bound specifications
    """

    __attr_name = None
    __attr_value = None

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueBoundSpecification

        :param attr_name: the candidate's attribute name
        :type attr_name: str
        :param attr_value: the value that satisfies the specification
        :type from_value: object
        """
        LeafSpecification.__init__(self)
        if self.__class__ is ValueBoundSpecification:
            raise NotImplementedError('Abstract class')
        self.__attr_name = attr_name
        self.__attr_value = attr_value

    def __eq__(self, other):
        """Equality operator"""
        return (isinstance(other, ValueBoundSpecification) and
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


class CompositeSpecification(Specification):
    """
    Abstract base class for composite specifications
    """

    __left_spec = None
    __right_spec = None

    def __init__(self, left_spec, right_spec):
        """
        Constructs a CompositeSpecification

        :param left_spec: the left part of the composite specification
        :type left_spec: :class:`Specification`
        :param right_spec: the right part of the composite specification
        :type right_spec: :class:`Specification`
        """
        if self.__class__ is CompositeSpecification:
            raise NotImplementedError('Abstract class')
        Specification.__init__(self)
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


class ConjuctionSpecification(CompositeSpecification):
    """
    Concrete conjuction specification
    """

    def __init__(self, left_spec, right_spec):
        """
        Constructs a ConjuctionSpecification
        """
        CompositeSpecification.__init__(self, left_spec, right_spec)

    def __eq__(self, other):
        """Equality operator"""
        return (isinstance(other, ConjuctionSpecification) and
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


class DisjuctionSpecification(CompositeSpecification):
    """
    Concrete disjuction specification
    """

    def __init__(self, left_spec, right_spec):
        """
        Constructs a DisjuctionSpecification
        """
        CompositeSpecification.__init__(self, left_spec, right_spec)

    def __eq__(self, other):
        """Equality operator"""
        return (isinstance(other, DisjuctionSpecification) and
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


class NegationSpecification(Specification):
    """
    Concrete negation specification
    """

    __wrapped_spec = None

    def __init__(self, wrapped_spec):
        """
        Constructs a NegationSpecification

        :param wrapped: the wrapped specification
        :type wrapped: :class:`Specification`
        """
        Specification.__init__(self)
        self.__wrapped_spec = wrapped_spec

    def __eq__(self, other):
        """Equality operator"""
        return (isinstance(other, NegationSpecification) and
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


class ValueStartsWithSpecification(ValueBoundSpecification):
    """
    Concrete value starts with specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueStartsWithSpecification
        """
        ValueBoundSpecification.__init__(self, attr_name, attr_value)

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


class ValueEndsWithSpecification(ValueBoundSpecification):
    """
    Concrete value ends with specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueEndsWithSpecification
        """
        ValueBoundSpecification.__init__(self, attr_name, attr_value)

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


class ValueContainsSpecification(ValueBoundSpecification):
    """
    Concrete value contains specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueContainsSpecification
        """
        ValueBoundSpecification.__init__(self, attr_name, attr_value)

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


class ValueContainedSpecification(ValueBoundSpecification):
    """
    Concrete value contained in a list of values specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueContainedSpecification

        :type attr_value: any sequence
        """
        ValueBoundSpecification.__init__(self, attr_name, attr_value)

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


class ValueEqualToSpecification(ValueBoundSpecification):
    """
    Concrete value equal to specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueEqualToSpecification
        """
        ValueBoundSpecification.__init__(self, attr_name, attr_value)

    def __str__(self):
        return '<ValueEqualToSpecification: %s == %s>' % (self.attr_name,
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


class ValueGreaterThanSpecification(ValueBoundSpecification):
    """
    Concrete value greater than specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueGreaterThanSpecification
        """
        ValueBoundSpecification.__init__(self, attr_name, attr_value)

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


class ValueLessThanSpecification(ValueBoundSpecification):
    """
    Concrete value less than specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueLessThanSpecification
        """
        ValueBoundSpecification.__init__(self, attr_name, attr_value)

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


class ValueGreaterThanOrEqualToSpecification(ValueBoundSpecification):
    """
    Concrete value greater than or equal to specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueGreaterThanOrEqualToSpecification
        """
        ValueBoundSpecification.__init__(self, attr_name, attr_value)

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


class ValueLessThanOrEqualToSpecification(ValueBoundSpecification):
    """
    Concrete value less than or equal to specification
    """

    def __init__(self, attr_name, attr_value):
        """
        Constructs a ValueLessThanOrEqualToSpecification
        """
        ValueBoundSpecification.__init__(self, attr_name, attr_value)

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


class ValueInRangeSpecification(ValueBoundSpecification):
    """
    Concrete specification for a range of values
    """

    def __init__(self, attr_name, from_value, to_value):
        """
        Constructs a ValueInRangeSpecification

        :param attr_name: the candidate's attribute name
        :type attr_name: str
        :param from_value: the lower limit of the range
        :type from_value: object
        :param to_value: the upper limit of the range
        :type to_value: object
        """
        ValueBoundSpecification.__init__(self, attr_name, (from_value, to_value))

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


class AbstractSpecificationFactory(object):
    """
    Abstract base class for all specification factories
    """

    def __init__(self):
        if self.__class__ is AbstractSpecificationFactory:
            raise NotImplementedError('Abstract class')

    def create_equal_to(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')

    def create_starts_with(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')

    def create_ends_with(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')

    def create_contains(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')

    def create_contained(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')

    def create_greater_than_or_equal_to(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')

    def create_greater_than(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')

    def create_less_than_or_equal_to(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')

    def create_less_than(self, attr_name, attr_value):
        raise NotImplementedError('Abstract method')

    def create_in_range(self, attr_name, from_value, to_value):
        raise NotImplementedError('Abstract method')

    def create_conjunction(self, left_spec, right_spec):
        raise NotImplementedError('Abstract method')

    def create_disjunction(self, left_spec, right_spec):
        raise NotImplementedError('Abstract method')

    def create_negation(self, wrapped):
        raise NotImplementedError('Abstract method')


class SpecificationFactory(AbstractSpecificationFactory):
    """
    Concrete specification factory
    """

    def __init__(self):
        AbstractSpecificationFactory.__init__(self)

    def create_equal_to(self, attr_name, attr_value):
        return ValueEqualToSpecification(attr_name, attr_value)

    def create_starts_with(self, attr_name, attr_value):
        return ValueStartsWithSpecification(attr_name, attr_value)

    def create_ends_with(self, attr_name, attr_value):
        return ValueEndsWithSpecification(attr_name, attr_value)

    def create_contains(self, attr_name, attr_value):
        return ValueContainsSpecification(attr_name, attr_value)

    def create_contained(self, attr_name, attr_value):
        return ValueContainedSpecification(attr_name, attr_value)

    def create_greater_than_or_equal_to(self, attr_name, attr_value):
        return ValueGreaterThanOrEqualToSpecification(attr_name, attr_value)

    def create_greater_than(self, attr_name, attr_value):
        return ValueGreaterThanSpecification(attr_name, attr_value)

    def create_less_than_or_equal_to(self, attr_name, attr_value):
        return ValueLessThanOrEqualToSpecification(attr_name, attr_value)

    def create_less_than(self, attr_name, attr_value):
        return ValueLessThanSpecification(attr_name, attr_value)

    def create_in_range(self, attr_name, from_value, to_value):
        return ValueInRangeSpecification(attr_name, from_value, to_value)

    def create_conjunction(self, left_spec, right_spec):
        return ConjuctionSpecification(left_spec, right_spec)

    def create_disjunction(self, left_spec, right_spec):
        return DisjuctionSpecification(left_spec, right_spec)

    def create_negation(self, wrapped):
        return NegationSpecification(wrapped)


specification_factory = SpecificationFactory()
