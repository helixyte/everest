"""
Interfaces for representers.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 18, 2011
"""
from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ICollectionDataElement',
           'ICollectionResourceRepresenter',
           'IDataElement',
           'IDeSerializer',
           'ILinkedDataElement',
           'IMappedClass',
           'IMappingRegistry',
           'IMemberDataElement',
           'IMemberResourceRepresenter',
           'IRepresentationConverter',
           'IRepresenter',
           'IRepresenterRegistry',
           'IResourceDataElement',
           'IResourceRepresenter',
           'ISerializer',
           ]

# interfaces do not provide a constructor. pylint: disable=W0232
# interface methods do not have self pylint: disable=E0213
# interface methods may have no argument: pylint: disable=E0211
class ISerializer(Interface):
    """
    Interface for objects performing serialization.
    """

    def to_string(obj):
        """
        Serializes the given object to a string.
        """

    def to_stream(obj, stream):
        """
        Serializes the given object to the given stream.
        """


class IDeSerializer(Interface):
    """
    Interface for objects performing deserialization.
    """

    def from_string(string_representation):
        """
        Deserializes the given string to an object.
        """

    def from_stream(stream):
        """
        Reads and deserializes the given stream to an object.
        """


class IRepresenter(IDeSerializer, ISerializer):
    """
    Interface for objects serving as representers.

    The representer interface combines the :class:`ISerializer` and
    :class:`IDeSerializer` interfaces. For a given combination of object
    type and MIME content type, a representer knows how to serialize an
    instance of the specified type into a representation of the specified
    content type and how to de-serialize such a representation into an
    object instance.
    """

    # MIME content type of the representation.
    content_type = Attribute('The MIME content type for the handled '
                             'representation.')


class IResourceRepresenter(IRepresenter):
    """
    Marker interface for resource representers.
    """


class IMemberResourceRepresenter(IResourceRepresenter):
    """
    Marker interface for member resource representers.
    """


class ICollectionResourceRepresenter(IResourceRepresenter):
    """
    Marker interface for collection resource representers.
    """


class IMappedClass(Interface):
    """
    Interface for classes with mapped attributes.
    """
    def create_from_data(data_element):
        """
        Creates an instance from the given data element.
        """


class IDataElement(Interface):
    """
    Base interface for data elements.
    """
    #: Mapping responsible for class -> attribute mapping
    mapping = Attribute("Maps classes to attributes")

    def create():
        """
        Factory class method creating a new data element.
        """


class IResourceDataElement(IDataElement):
    """
    Interface for resource data elements.
    """
    def create_from_resource(resource):
        """
        Factory class method creating a new data element from the given
        resource.
        """


class IMemberDataElement(IResourceDataElement):
    """
    Interface for member data elements.
    """
    converter_registry = Attribute("Registry of representation<->value "
                                   "converters.")

    def iterator():
        """
        Returns an iterator yielding (attribute repr name, attribute value)
        pairs for every attribute set on this data element.
        """

    data = Attribute("Ordered dictionary constructed from the return values "
                     "of the :method:`iterator` method.")

    def get_attribute(name):
        """
        Returns the value that was set for the given attribute representation
        name.

        Raises an :class:`AttributeError` if the attribute was not set.
        """

    def set_attribute(name, value):
        """
        Sets the value for the given attribute representation name to the
        given value.

        Raises an :class:`AttributeError` if the underlying mapping does not
        have an attribute with the given representation name.
        """

    def get_terminal(attr):
        """
        Returns the value for the given terminal mapped attribute or `None`
        if the data element does not have a value set for this attribute.
        """

    def set_terminal(attr, value):
        """
        Sets the given mapped terminal attribute to the given value.
        """

    def get_nested(attr):
        """
        Returns the nested data element specified by the given member or
        collection mapped attribute or `None` if the data element does not
        have a value set for this attribute.
        """

    def set_nested(attr, data_element):
        """
        Sets the given mmeber or collection mapped attribute to the given
        data element.
        """


class ICollectionDataElement(IResourceDataElement):
    """
    Interface for collection data elements.
    """
    def add_member(member_data_el):
        """
        Adds the given member data element to this collection data element.
        """

    def get_members():
        """
        Returns all member data elements.
        """

    def __len__():
        """
        Returns the number of member data elements in this collection data
        element.
        """


class ILinkedDataElement(IDataElement):
    """
    Interface for data elements containing a link to a resource.
    """
    def get_url():
        """
        Returns the URL for this data element.
        """

    def get_kind():
        """
        Returns the kind of the resource being linked to (one of the
        constants declared in :class:`everest.constants.RESOURCE_KINDS`).
        """

    def get_id():
        """
        Returns the ID of the resource being linked to.
        """

    def get_relation():
        """
        Returns the relation of the resource being linked to.
        """

    def get_title():
        """
        Returns a title for the resource being linked to.
        """


class IMappingRegistry(Interface):
    def create_mapping(mapped_class, configuration,
                       base_data_element_class=None):
        """
        Creates a new data element class for the given mapped class and
        representer configuration.
        """

    def set_data_element_class(data_element_class):
        """
        Registers the given data element class.
        """

    def get_data_element_class(mapped_class):
        """
        Returns the data element class registered for the given mapped class.
        """

    def get_data_element_classes():
        """
        Returns a list of all registered data element classes.
        """



class IRepresenterRegistry(Interface):
    """
    Marker interface for the representer registry.
    """


class IRepresentationConverter(Interface):
    def from_representation(value):
        """
        Converts the given representation string to a Python value object.
        """

    def to_representation(value):
        """
        Converts the given Python value object into a representation string.
        """

# pylint: enable=W0232,E0213,E0211
