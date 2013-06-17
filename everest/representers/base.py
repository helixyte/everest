"""
Representer base classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 18, 2011.
"""
from everest.representers.utils import get_mapping_registry
from pyramid.compat import NativeIO
from everest.resources.base import Resource

__docformat__ = 'reStructuredText en'
__all__ = ['RepresentationGenerator',
           'RepresentationParser',
           'Representer',
           'RepresenterRegistry',
           'ResourceRepresenter',
           ]


class Representer(object):
    """
    Base class for all representers.

    A representer knows how to convert an object into a representation of a
    particular MIME type (content type) and vice versa.
    """

    content_type = None

    def from_string(self, string_representation):
        """
        Extracts resource data from the given string and converts them to
        a new resource or updates the given resource from it.
        """
        stream = NativeIO(string_representation)
        return self.from_stream(stream)

    def to_string(self, obj):
        """
        Converts the given resource to a string representation and returns
        it.
        """
        stream = NativeIO()
        self.to_stream(obj, stream)
        return stream.getvalue()

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
    Base class for resource representers which know how to convert resource
    representations into resources and back.
    """

    def __init__(self, resource_class):
        Representer.__init__(self)
        self.resource_class = resource_class

    @classmethod
    def create_from_resource(cls, rc):
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

    def data_from_representation(self, representation):
        """
        Converts the given representation to resource data.
        
        :returns: resource data object which can be passed to the *_from_data
            methods
        """
        raise NotImplementedError('Abstract method.')

    def representation_from_data(self, data):
        """
        Creates a representation from the given resource data.
        
        :returns: string representation (using the MIME content type
            configured for this representer)
        """
        raise NotImplementedError('Abstract method.')

    def resource_from_data(self, data):
        """
        Converts the given resource data to a resource.

        :returns: object implementing
          :class:`everest.resources.interfaces.IResource`
        """
        raise NotImplementedError('Abstract method.')

    def data_from_resource(self, resource):
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
    def create_from_resource(cls, rc):
        mp_reg = get_mapping_registry(cls.content_type)
        rc_cls = type(rc)
        mp = mp_reg.find_or_create_mapping(rc_cls)
        return cls(rc_cls, mp)

    @classmethod
    def make_mapping_registry(cls):
        raise NotImplementedError('Abstract method.')

    def from_stream(self, stream, resource=None):
        parser = self._make_representation_parser(stream, self.resource_class,
                                                  self._mapping)
        data_el = parser.run()
        return self.resource_from_data(data_el, resource=resource)

    def to_stream(self, resource, stream):
        data_el = self.data_from_resource(resource)
        generator = \
            self._make_representation_generator(stream, self.resource_class,
                                                self._mapping)
        generator.run(data_el)

    def data_from_stream(self, stream):
        """
        Creates a data element reading a representation from the given stream.
        
        :returns: object implementing 
            :class:`everest.representers.interfaces.IExplicitDataElement`
        """
        parser = self._make_representation_parser(stream, self.resource_class,
                                                  self._mapping)
        return parser.run()

    def data_from_representation(self, representation):
        """
        Creates a data element from the given representation.
        
        :returns: object implementing 
            :class:`everest.representers.interfaces.IExplicitDataElement`
        """
        stream = NativeIO(representation)
        return self.data_from_stream(stream)

    def representation_from_data(self, data_element):
        """
        Converts the given data element into a representation.
        
        :param data_element: Source data element.
        """
        stream = NativeIO()
        generator = \
            self._make_representation_generator(stream, self.resource_class,
                                                self._mapping)
        generator.run(data_element)
        return stream.getvalue()

    def resource_from_data(self, data_element, resource=None):
        """
        Converts the given data element into a resource.

        :param data_element: Source data element.
        :param resource: If given, this resource will be updated from the
          given :param:`data_element`; otherwise, a new resource will be
          created.
        :returns: object implementing
          :class:`everest.resources.interfaces.IResource`
        """
        return self._mapping.map_to_resource(data_element, resource=resource)

    def data_from_resource(self, resource):
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
        Configures the options and attribute options for the mapping
        associated with this representer.
        
        :param dict options: configuration options for the mapping associated
          with this representer.
        :param dict attribute_options: attribute options for the mapping
          associated with this representer.
        """
        self._mapping = \
                self._mapping.clone(options=options,
                                    attribute_options=attribute_options)

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


class RepresenterRegistry(object):
    """
    Registry for representer classes and representer factories.
    """

    def __init__(self):
        self.__rpr_classes = {}
        self.__mp_regs = {}
        self.__rpr_factories = {}

    def register_representer_class(self, representer_class):
        if representer_class in self.__rpr_classes.values():
            raise ValueError('The representer class "%s" has already been '
                             'registered.' % representer_class)
        self.__rpr_classes[representer_class.content_type] = representer_class
        if issubclass(representer_class, MappingResourceRepresenter):
            # Create and hold a mapping registry for the registered resource
            # representer class.
            mp_reg = representer_class.make_mapping_registry()
            self.__mp_regs[representer_class.content_type] = mp_reg

    def is_registered_representer_class(self, representer_class):
        return representer_class in self.__rpr_classes.values()

    def get_mapping_registry(self, content_type):
        return self.__mp_regs.get(content_type)

    def register(self, resource_class, content_type, configuration=None):
        """
        Registers a representer factory for the given combination of resource
        class and content type.
        
        :param configuration: representer configuration. A default instance
          will be created if this is not given.
        :type configuration: 
            :class:`everest.representers.config.RepresenterConfiguration`
        """
        if not issubclass(resource_class, Resource):
            raise ValueError('Representers can only be registered for '
                             'resource classes (got: %s).' % resource_class)
        if not content_type in self.__rpr_classes:
            raise ValueError('No representer class has been registered for '
                             'content type "%s".' % content_type)
        # Register a factory resource -> representer for the given combination
        # of resource class and content type.
        rpr_cls = self.__rpr_classes[content_type]
        self.__rpr_factories[(resource_class, content_type)] = \
                                            rpr_cls.create_from_resource
        if issubclass(rpr_cls, MappingResourceRepresenter):
            # Create or update an attribute mapping.
            mp_reg = self.__mp_regs[content_type]
            mp = mp_reg.find_mapping(resource_class)
            if mp is None:
                # No mapping was registered yet for this resource class or any
                # of its base classes; create a new one on the fly.
                new_mp = mp_reg.create_mapping(resource_class, configuration)
            elif not configuration is None:
                if resource_class is mp.mapped_class:
                    # We have additional configuration for an existing mapping.
                    mp.configuration.update(configuration)
                    new_mp = mp
                else:
                    # We have a derived class with additional configuration.
                    new_mp = mp_reg.create_mapping(
                                            resource_class,
                                            configuration=mp.configuration)
                    new_mp.configuration.update(configuration)
            elif not resource_class is mp.mapped_class:
                # We have a derived class without additional configuration.
                new_mp = mp_reg.create_mapping(resource_class,
                                               configuration=mp.configuration)
            else:
                # We found a dynamically created mapping for the right class
                # without additional configuration; do not create a new one.
                new_mp = None
            if not new_mp is None:
                # Store the new (or updated) mapping.
                mp_reg.set_mapping(new_mp)

    def create(self, resource, content_type):
        """
        Creates a representer for the given combination of resource and 
        content type. This will also find representer factories that were
        registered for a base class of the given resource.
        """
        rc_cls = type(resource)
        for base_rc_cls in rc_cls.__mro__:
            try:
                rpr_fac = self.__rpr_factories[(base_rc_cls, content_type)]
            except KeyError:
                rpr = None
            else:
                rpr = rpr_fac(resource)
                break
        return rpr


class _RepresentationHandler(object):
    """
    Base class for objects handling a representation stream.
    """
    def __init__(self, stream, resource_class, mapping):
        self._stream = stream
        self._resource_class = resource_class
        self._mapping = mapping
        self.__config = {}

    def get_option(self, option, default=None):
        return self.__config.get(option, default)

    def set_option(self, option, value):
        self.__config[option] = value


class RepresentationParser(_RepresentationHandler):

    def run(self):
        """
        :return: The data element tree parsed from the handled stream.
        """
        raise NotImplementedError('Abstract method.')


class RepresentationGenerator(_RepresentationHandler):

    def run(self, data_element):
        """
        :param data_element: The data element tree to be serialized.
        """
        raise NotImplementedError('Abstract method.')
