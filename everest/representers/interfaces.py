"""
Interfaces for representers.

FOG May 18, 2011
"""
from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['IDeSerializer',
           'ISerializer',
           'IRepresentationConverter',
           'IRepresenter'
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

    def create_from_data(data_element):
        """
        Creates an instance from the given data element.
        """


class IDataElement(Interface):
    """
    Base interface for data element classes.
    """
    #: Mapping responsible for class -> attribute mapping
    mapping = Attribute("Maps classes to attributes")

    def create():
        """
        Factory class method creating a new data element.
        """


class IResourceDataElement(IDataElement):
    def create_from_resource(resource):
        """
        Factory class method creating a new data element from the given
        resource.
        """


class IMemberDataElement(IResourceDataElement):
    """
    Interface for member data elements.
    """

    def get_mapped_terminal(attr):
        """
        Returns the value for the given terminal mapped attribute.
        """

    def set_mapped_terminal(attr, value):
        """
        Sets the given mapped terminal attribute to the given value.
        """

    def get_mapped_nested(attr):
        """
        Returns the nested data element specified by the given member or
        collection mapped attribute.
        """

    def set_mapped_child(attr, data_element):
        """
        Sets the given mmeber or collection mapped attribute to the given 
        data element.
        """


class ICollectionDataElement(IResourceDataElement):
    """
    Interface for collection data elements.
    """

    def get_members():
        """
        Returns all member data elements.
        """

    def add_member(member_data_el):
        """
        Adds the given member data element to this collection data element.
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


class ICustomDataElement(Interface):

    def extract():
        """
        """

    def inject(obj):
        """
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
