"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['IAtomMime',
           'IAtomEntryMime',
           'IAtomFeedMime',
           'IAtomRequest',
           'IAtomServiceMime',
           'ICqlFilterSpecificationVisitor',
           'ICqlOrderSpecificationVisitor',
           'ICsvMime',
           'ICsvRequest',
           'IFilterSpecificationVisitor',
           'IJsonMime',
           'IJsonRequest',
           'IKeyFunctionOrderSpecificationVisitor',
           'IOrderSpecificationVisitor',
           'IQueryFilterSpecificationVisitor',
           'IXmlMime',
           'IXmlRequest',
           'IXlsMime',
           'IXlsRequest'
           ]

# no self, no __init__, no args  pylint: disable=E0213,W0232,E0211
class IJsonRequest(Interface):
    """Marker interface for a JSON request."""

class IAtomRequest(Interface):
    """Marker interface for an ATOM request."""

class IXmlRequest(Interface):
    """Marker interface for an XML request."""

class ICsvRequest(Interface):
    """Marker interface for an request."""

class IXlsRequest(Interface):
    """Marker interface for an Excel request."""

class IJsonMime(Interface):
    """Marker interface for a JSON mime type."""

class IAtomMime(Interface):
    """Marker interface for an ATOM mime type."""

class IAtomFeedMime(Interface):
    """Marker interface for an ATOM feed mime type."""

class IAtomEntryMime(Interface):
    """Marker interface for an ATOM entry mime type."""

class IAtomServiceMime(Interface):
    """Marker interface for an ATOM service mime type."""

class IXmlMime(Interface):
    """Marker interface for an XML mime type."""

class ICsvMime(Interface):
    """Marker interface for an CSV mime type."""

class IXlsMime(Interface):
    """Marker interface for an Excel mime type."""

class IFilterSpecificationFactory(Interface):
    """
    Filter specification factory interface.
    """

    def create_equal_to(attr_name, attr_value):
        "Create an equal-to filter specification."

    def create_starts_with(attr_name, attr_value):
        "Create a starts-with filter specification."

    def create_ends_with(attr_name, attr_value):
        "Create an ends-with filter specification."

    def create_contains(attr_name, attr_value):
        "Create a contains filter specification."

    def create_contained(attr_name, attr_value):
        "Create a contained filter specification."

    def create_greater_than_or_equal_to(attr_name, attr_value):
        "Create a greater-than-or-equal-to filter specification."

    def create_greater_than(attr_name, attr_value):
        "Create a greater-than filter specification."

    def create_less_than_or_equal_to(attr_name, attr_value):
        "Create a less-than-or-equal-to filter specification."

    def create_less_than(attr_name, attr_value):
        "Create a less-than filter specification."

    def create_in_range(attr_name, from_value, to_value):
        "Create an in-range filter specification."
        raise NotImplementedError('Abstract method')

    def create_conjunction(left_spec, right_spec):
        "Create a conjunction of two filter specifications."

    def create_disjunction(left_spec, right_spec):
        "Create a disjunction of two filter specifications."

    def create_negation(wrapped):
        "Create a negation of a filter specification."

class IOrderSpecificationFactory(Interface):
    """
    Order specification factory interface.
    """

    def create_simple(attr_name):
        "Create a simple order specification."

    def create_natural(attr_name):
        "Create a natural order specification."

class ISpecificationDirector(Interface):
    def construct(query):
        "Construct a specification from the given query expression."

    def has_errors():
        "Checks if the call to :method:`construct` produced any errors."

    def get_errors():
        "Returns any errors the call to :method:`construct` produced."

class IFilterSpecificationDirector(ISpecificationDirector):
    "Interface for filter specification directors."

class IFilterSpecificationBuilder(Interface):
    """
    Filter specification builder interface.

    Based on the Builder Design Pattern.
    """

    def build_equal_to(attr_name, attr_values):
        "Build an equal-to specification."

    def build_not_equal_to(attr_name, attr_values):
        "Build a not-equal-to specification."

    def build_starts_with(attr_name, attr_values):
        "Build a starts-with specification."

    def build_not_starts_with(attr_name, attr_values):
        "Build a not-starts-with specification."

    def build_ends_with(attr_name, attr_values):
        "Build an ends-with specification."

    def build_not_ends_with(attr_name, attr_values):
        "Build a not-ends-with specification."

    def build_contains(attr_name, attr_values):
        "Build a contains specification."

    def build_not_contains(attr_name, attr_values):
        "Build a not-contains specification."

    def build_less_than_or_equal_to(attr_name, attr_values):
        "Build a less-than-or-equal-to specification."

    def build_less_than(attr_name, attr_values):
        "Build a less-than specification."

    def build_greater_than_or_equal_to(attr_name, attr_values):
        "Build a greater-than-or-equal-to specification."

    def build_greater_than(attr_name, attr_values):
        "Build a greater-than specification."

    def build_in_range(attr_name, attr_values):
        "Build an in-range specification."

    def build_not_in_range(attr_name, attr_values):
        "Build a not-in-range specification."

class IOrderSpecificationDirector(ISpecificationDirector):
    "Interface for order specification directors."

class IOrderSpecificationBuilder(Interface):
    """
    Abstract base class for all order specification builders.

    Based on the Builder Design Pattern.
    """

    def build_asc(self, attr_name):
        """
        """
        pass

    def build_desc(self, attr_name):
        """
        """
        pass

    def get_sort_order(self):
        "Returns the built order specification."

class IFilterSpecificationVisitor(Interface):
    """
    Interface for filter specification visitors.
    """

    def visit_conjuction(spec):
        """
        Visit a conjuction filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.ConjuctionFilterSpecification`
        """

    def visit_disjuction(spec):
        """
        Visit a disjuction filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.DisjuctionFilterSpecification`
        """

    def visit_negation(spec):
        """
        Visit a negation filter specification.

        :param spec: filter specification
        :type spec: :class:`everest.specifications.NegationFilterSpecification`
        """

    def visit_value_starts_with(spec):
        """
        Visit a value starts-with filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.ValueStartsWithFilterSpecification`
        """

    def visit_value_ends_with(spec):
        """
        Visit a value ends-with filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.ValueEndsWithFilterSpecification`
        """

    def visit_value_contains(spec):
        """
        Visit a value contains filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.ValueContainsFilterSpecification`
        """

    def visit_value_contained(spec):
        """
        Visit a value contained filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.ValueContainedFilterSpecification`
        """

    def visit_value_equal_to(spec):
        """
        Visit a value equal-to filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.ValueEqualToFilterSpecification`
        """

    def visit_value_less_than(spec):
        """
        Visit a value less-than filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.ValueLessThanFilterSpecification`
        """

    def visit_value_greater_than(spec):
        """
        Visit a value greater-than filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.ValueGreaterThanFilterSpecification`
        """

    def visit_value_less_than_or_equal_to(spec):
        """
        Visit a value less-than-or-equal-to filter specification.

        :param spec: filter specification
        :type spec:  
          :class:`everest.specifications.ValueLessThanOrEqualToFilterSpecification`
        """

    def visit_value_greater_than_or_equal_to(spec):
        """
        Visit a value greater-than-or-equal-to filter specification.

        :param spec: filter specification
        :type spec: 
          :class:`everest.specifications.ValueGreaterThanOrEqualToFilterSpecification`
        """

    def visit_value_in_range(spec):
        """
        Visit a value in-range filter specification.

        :param spec: filter specification
        :type spec: 
            :class:`everest.specifications.ValueInRangeFilterSpecification`
        """

class ICqlFilterSpecificationVisitor(IFilterSpecificationVisitor):
    """
    Marker interface for filter specification visitors that generate a CQL
    expression.
    """

class IQueryFilterSpecificationVisitor(IFilterSpecificationVisitor):
    """
    Marker interface for filter specification visitors that generate a query
    expression.
    """

class IOrderSpecificationVisitor(Interface):
    """
    Interface for order specification visitors that generate a query 
    expression.
    """

    def visit_simple(order):
        """
        Visit simple order.

        :param order: an order instance
        :type order: :class:`everest.ordering.SimpleOrderSpecification`
        """

    def visit_natural(order):
        """
        Visit natural order.

        :param spec: an order instance
        :type spec: :class:`everest.ordering.NaturalOrderSpecification`
        """

    def visit_reverse(order):
        """
        Visit order in reverse.

        :param spec: an order instance
        :type spec: :class:`everest.ordering.OrderSpecification`
        """

    def visit_conjunction(order):
        """
        Visit conjunction with order.

        :param spec: an order instance
        :type spec: :class:`everest.ordering.OrderSpecification`
        """

class IQueryOrderSpecificationVisitor(IOrderSpecificationVisitor):
    """
    Marker interface for order specification visitors that generate a query
    expression.
    """

class IKeyFunctionOrderSpecificationVisitor(IOrderSpecificationVisitor):
    """
    Marker interface for order specification visitors that generate a key
    function to pass to __cmp__.
    """

class ICqlOrderSpecificationVisitor(IOrderSpecificationVisitor):
    """
    Marker interface for order specification visitors that generate a CQL
    expression.
    """

class IResourceUrlConverter(Interface):
    def url_to_resource(url):
        """Performs URL -> resource conversion."""
    def resource_to_url(resource):
        """Performs URL -> resource conversion."""

class IStagingContextManager(Interface):
    root_aggregate_impl = Attribute("Root aggregate implementation class.")
    relation_aggregate_impl = \
            Attribute("Relation aggregate implementation class.")
    def __enter__():
        """Enters the context."""
    def __exit__():
        """Exits the context."""

# pylint: enable=E0213,W0232,E0211
