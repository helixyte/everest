"""
Representer base classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 18, 2011.
"""
from pyramid.compat import NativeIO
from pyramid.compat import bytes_
from pyramid.compat import text_

from everest.representers.utils import get_mapping_registry


__docformat__ = 'reStructuredText en'
__all__ = ['MappingResourceRepresenter',
           'RepresentationGenerator',
           'RepresentationParser',
           'Representer',
           'ResourceRepresenter',
           ]


class Representer(object):
    """
    Base class for all representers.

    A representer knows how to convert an object into a representation of a
    particular MIME type (content type) and vice versa.
    """
    #: The encoding to use to convert between bytes and string
    #: representations.
    encoding = 'utf-8'
    #: The registered MIME content type this representer is handling.
    content_type = None

    def from_string(self, string_representation, resource=None):
        """
        Extracts resource data from the given string and converts them to
        a new resource or updates the given resource from it.
        """
        stream = NativeIO(string_representation)
        return self.from_stream(stream, resource=resource)

    def from_bytes(self, bytes_representation, resource=None):
        """
        Extracts resource data from the given bytes representation and calls
        :method:`from_string` with the resulting text representation.
        """
        text = bytes_representation.decode(self.encoding)
        return self.from_string(text, resource=resource)

    def to_string(self, obj):
        """
        Converts the given resource to a string representation and returns
        it.
        """
        stream = NativeIO()
        self.to_stream(obj, stream)
        return text_(stream.getvalue(), encoding=self.encoding)

    def to_bytes(self, obj, encoding=None):
        """
        Converts the given resource to bytes representation in the encoding
        specified by :param:`encoding` and returns it.
        """
        if encoding is None:
            encoding = self.encoding
        text = self.to_string(obj)
        return bytes_(text, encoding=self.encoding)

    def from_stream(self, stream, resource=None):
        """
        Extracts resource data from the given stream and converts them to
        a new resource or updates the given resource from it.
        """
        raise NotImplementedError("Abstract method.")

    def to_stream(self, obj, stream):
        """
        Converts the given resource to a string representation and writes
        it to the given stream.
        """
        raise NotImplementedError("Abstract method.")


class ResourceRepresenter(Representer):
    """
    Abstract basee class for resource representers which know how to convert
    resource representations into resources and back.
    """
    def __init__(self, resource_class):
        Representer.__init__(self)
        self.resource_class = resource_class

    def from_stream(self, stream, resource=None):
        data_el = self.data_from_stream(stream)
        return self.resource_from_data(data_el, resource=resource)

    def to_stream(self, resource, stream):
        data_el = self.resource_to_data(resource)
        self.data_to_stream(data_el, stream)

    @classmethod
    def create_from_resource_class(cls, rc):
        """
        Factory method creating a new representer from the given registered
        resource.
        """
        raise NotImplementedError('Abstract method.')

    def data_from_stream(self, stream):
        """
        Extracts resource data from the given stream.
        """
        raise NotImplementedError('Abstract method.')

    def data_to_stream(self, data_element, stream):
        """
        Writes resource data to the given stream.
        """
        raise NotImplementedError('Abstract method.')

    def data_from_string(self, text):
        """
        Converts the given text representation to resource data.

        :returns: object implementing
            :class:`everest.representers.interfaces.IExplicitDataElement`
        """
        stream = NativeIO(text)
        return self.data_from_stream(stream)

    def data_from_bytes(self, byte_representation):
        """
        Converts the given bytes representation to resource data.
        """
        text = byte_representation.decode(self.encoding)
        return self.data_from_string(text)

    def data_to_string(self, data_element):
        """
        Converts the given data element into a string representation.

        :param data_element: object implementing
            :class:`everest.representers.interfaces.IExplicitDataElement`
        :returns: string representation (using the MIME content type
            configured for this representer)
        """
        stream = NativeIO()
        self.data_to_stream(data_element, stream)
        return stream.getvalue()

    def data_to_bytes(self, data_element, encoding=None):
        """
        Converts the given data element into a string representation using
        the :method:`data_to_string` method and encodes the resulting
        text with the given encoding.
        """
        if encoding is None:
            encoding = self.encoding
        text = self.data_to_string(data_element)
        return bytes_(text, encoding=encoding)

    def resource_from_data(self, data, resource=None):
        """
        Converts the given resource data to a resource.

        :param resource: If given, this resource will be updated from the
          given data; otherwise, a new resource will be created.
        :returns: object implementing
          :class:`everest.resources.interfaces.IResource`
        """
        raise NotImplementedError('Abstract method.')

    def resource_to_data(self, resource):
        """
        Converts the given resource to resource data.

        :returns: resource data object which can be passed to the *_from_data
            methods
        """
        raise NotImplementedError('Abstract method.')

    def configure(self, options=None):
        """
        Configures the options for this representer.
        """
        raise NotImplementedError('Abstract method.')


class MappingResourceRepresenter(ResourceRepresenter):
    """
    Base class for resource representers that use configurable attribute
    mappings to perform conversions from resource representations and back.

    The conversion is performed using four independent and highly customizable
    helper objects:

     1. The *representation parser* responsible for converting the
        representation into a data element tree;
     2. The *data element parser* responsible for converting a data element
        tree into a resource;
     3. The *data element generator* responsible for converting a resource
        into a data element tree; and
     4. the *representation generator* responsible for converting the data
        element tree into a representation.
    """
    def __init__(self, resource_class, mapping):
        ResourceRepresenter.__init__(self, resource_class)
        self._mapping = mapping

    @classmethod
    def create_from_resource_class(cls, resource_class):
        """
        Creates a new representer for the given resource class.

        The representer obtains a reference to the (freshly created or looked
        up) mapping for the resource class.
        """
        mp_reg = get_mapping_registry(cls.content_type)
        mp = mp_reg.find_or_create_mapping(resource_class)
        return cls(resource_class, mp)

    @classmethod
    def make_mapping_registry(cls):
        raise NotImplementedError('Abstract method.')

    def data_from_stream(self, stream):
        """
        Creates a data element reading a representation from the given stream.

        :returns: object implementing
            :class:`everest.representers.interfaces.IExplicitDataElement`
        """
        parser = self._make_representation_parser(stream, self.resource_class,
                                                  self._mapping)
        return parser.run()

    def data_to_stream(self, data_element, stream):
        """
        Writes the given data element to the given stream.
        """
        generator = \
            self._make_representation_generator(stream, self.resource_class,
                                                self._mapping)
        generator.run(data_element)

    def resource_from_data(self, data_element, resource=None):
        """
        Converts the given data element to a resource.

        :param data_element: object implementing
            :class:`everest.representers.interfaces.IExplicitDataElement`
        """
        return self._mapping.map_to_resource(data_element, resource=resource)

    def resource_to_data(self, resource):
        """
        Extracts managed attributes from a resource and constructs a data
        element for serialization from it.

        Default representer behavior:
         * Top-level member and collections resource attributes are
           represented as links.
         * Nested member resource attributes are represented as links,
           nested collection resource attributes are ignored (building a link
           may require iterating over the collection).

        The default behavior can be configured with the "representer"
        directive (:func:`everest.configuration.representer`) by means of the
        "write_as_link" and "ignore" options of representer configuration
        objects (:class:`everest.representers.config.RepresenterConfiguration`).
        """
        return self._mapping.map_to_data_element(resource)

    def configure(self, options=None, attribute_options=None): # pylint: disable=W0221
        """
        Configures the options and attribute options of the mapping associated
        with this representer with the given dictionaries.

        :param dict options: configuration options for the mapping associated
          with this representer.
        :param dict attribute_options: attribute options for the mapping
          associated with this representer.
        """
        self._mapping.update(options=options,
                             attribute_options=attribute_options)
#        self._mapping = \
#                self._mapping.clone(options=options,
#                                    attribute_options=attribute_options)

    def with_updated_configuration(self, options=None,
                                   attribute_options=None):
        """
        Returns a context in which this representer is updated with the
        given options and attribute options.
        """
        return self._mapping.with_updated_configuration(options=options,
                                                        attribute_options=
                                                            attribute_options)

    def _make_representation_parser(self, stream, resource_class, mapping):
        """
        Creates a representation parser from the given arguments. This parser
        has a `run` method which reads and parses the serialized resource from
        the given stream.
        """
        raise NotImplementedError('Abstract method.')

    def _make_representation_generator(self, stream, resource_class, mapping):
        """
        Creates a representation generator from the given arguments. This
        generator has a `run` method which writes out the serialized
        resource representation to the given stream.
        """
        raise NotImplementedError('Abstract method.')


class _RepresentationHandler(object):
    """
    Base class for classes handling a representation stream.
    """
    def __init__(self, stream, resource_class, mapping):
        """
        :param stream: stream object for the representation data.
        :param resource_class: registered member or collection resource
          class.
        :param mapping: attribute mapping for the given resource class,
          instance of :class:`everest.representers.mapping.Mapping`.
        """
        self._stream = stream
        self._resource_class = resource_class
        self._mapping = mapping
        self.__config = {}

    def get_option(self, option, default=None):
        """
        Returns the specified representer configuration option or the given
        default, if the option was not configured.
        """
        return self.__config.get(option, default)

    def set_option(self, option, value):
        """
        Sets the specified representer configuration option to the given
        value.
        """
        self.__config[option] = value


class RepresentationParser(_RepresentationHandler):
    """
    Abstract base class for classes that parse representations.
    """
    def run(self):
        """
        :return: The data element tree parsed from the handled stream.
        """
        raise NotImplementedError('Abstract method.')


class RepresentationGenerator(_RepresentationHandler):
    """
    Abstract base class for classes that generate representations.
    """
    def run(self, data_element):
        """
        :param data_element: The data element tree to be serialized.
        """
        raise NotImplementedError('Abstract method.')
