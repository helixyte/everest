"""
Interfaces for representers.

FOG May 18, 2011
"""

from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'

__author__ = 'F Oliver Gathmann'
__date__ = '$Date: 2011-10-07 12:52:11 +0200 (Fri, 07 Oct 2011) $'
__revision__ = '$Rev: 12174 $'
__source__ = '$URL:: http://svn/cenix/TheLMA/trunk/thelma/resources/represent#$'

__all__ = ["IDeSerializer",
           "ISerializer",
           "IRepresenter"
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
    #: Mapped type - class-implements :class:`IMappedClass`
    mapped_class = Attribute("Type mapped to this data element class.")
    #: Mapper responsible for class -> attribute mapping
    mapper = Attribute("Maps classes to attributes")

    def create():
        """
        Factory class method creating a new data element.
        """

class IExplicitDataElement(IDataElement):
    """
    Interface for data elements containing explicit resource data.
    """

    def create_from_resource(resource):
        """
        Factory class method creating a new data element from the given
        resource.
        """

    def get_value(attr):
        """
        Returns the value for the given mapped attribute.
        """

    def set_value(attr, value):
        """
        Sets the given mapped attribute to the given value.
        """

    def get_child(attr):
        """
        Returns the data element child specified by the given mapped attribute.
        """

    def set_child(attr, data_element):
        """
        Sets the given mapped attribute to the given data element child.
        """

    def get_children():
        """
        Returns all data element children.
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


class IDataElementRegistry(Interface):
    def create_data_element_class(mapped_class, configuration):
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

# pylint: enable=W0232,E0213,E0211
