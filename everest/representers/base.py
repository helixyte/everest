"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Representers for resources and entities.

Created on May 18, 2011.
"""
from StringIO import StringIO
from everest.representers.utils import get_mapping_registry
from everest.resources.attributes import ResourceAttributeKinds

__docformat__ = 'reStructuredText en'
__all__ = ['RepresentationHandler',
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
        stream = StringIO(string_representation)
        return self.from_stream(stream)

    def to_string(self, obj):
        stream = StringIO()
        self.to_stream(obj, stream)
        return stream.getvalue()

    def from_stream(self, stream):
        raise NotImplementedError("Abstract method.")

    def to_stream(self, obj, stream):
        raise NotImplementedError("Abstract method.")


class ResourceRepresenter(Representer):
    """
    Base class for resource representers which know how to convert resource
    representations into resources and back.

    This conversion is performed using four customizable, independent helper
    objects:
     1. The *representation parser* responsible for converting the
        representation into a data element tree;
     2. The *data element parser* responsible for converting a data element
        tree into a resource;
     3. The *data element generator* responsible for converting a resource
        into a data element tree; and
     4. the *representation generator* responsible for converting the data
        element tree into a representation.
    """

    def __init__(self, resource_class, mapping_registry):
        Representer.__init__(self)
        self.resource_class = resource_class
        self._mapping_registry = mapping_registry

    @classmethod
    def create_from_resource(cls, rc):
        mp_reg = get_mapping_registry(cls.content_type)
        return cls(type(rc), mp_reg)

    @classmethod
    def make_mapping_registry(cls):
        raise NotImplementedError('Abstract method.')

    def from_stream(self, stream):
        parser = self._make_representation_parser(stream, self.resource_class)
        return self._parse(parser)

    def to_stream(self, resource, stream):
        generator = \
            self._make_representation_generator(stream, self.resource_class)
        return self._generate(generator, resource)

    def data_from_stream(self, stream):
        """
        Creates a data element reading a representation from the given stream.
        
        :returns: object implementing 
            :class:`everest.representers.interfaces.IExplicitDataElement`
        """
        parser = self._make_representation_parser(stream, self.resource_class)
        return parser.run()

    def data_from_representation(self, representation):
        """
        Creates a data element from the given representation.
        
        :returns: object implementing 
            :class:`everest.representers.interfaces.IExplicitDataElement`
        """
        stream = StringIO(representation)
        return self.data_from_stream(stream)

    def representation_from_data(self, data_element):
        """
        Creates a representation from the given data element.
        
        :param data_element: 
        """
        stream = StringIO()
        generator = \
            self._make_representation_generator(stream, self.resource_class)
        generator.run(data_element)
        return stream.getvalue()

    def resource_from_data(self, data_element,
                           resolve_urls=True, mapping_options=None):
        """
        Extracts serialized data from the given data element and constructs
        a resource from it.

        :param resolve_urls: If this is set to `False`, resolving URLs in the
          data element tree will be delayed until after loading has completed.
        :returns: object implementing
          :class:`everest.resources.interfaces.IResource`
        """
        mp = data_element.mapping
        if not mapping_options is None:
            mp = mp.clone(mapping_options=mapping_options)
        return mp.map_to_resource(data_element, resolve_urls=resolve_urls)

    def data_from_resource(self, resource, mapping_options=None):
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
        mp = self._mapping_registry.find_or_create_mapping(type(resource))
        if not mapping_options is None:
            mp = mp.clone(mapping_options=mapping_options)
        return mp.map_to_data_element(resource)

    def _parse(self, parser):
        data_el = parser.run()
        return self.resource_from_data(data_el)

    def _generate(self, generator, resource):
        data_el = self.data_from_resource(resource)
        return generator.run(data_el)

    def _make_representation_parser(self, stream, resource_class):
        """
        Creates a representation parser from the given arguments. This parser
        has a `run` method which reads and parses the serialized resource from
        the given stream.
        """
        raise NotImplementedError('Abstract method.')

    def _make_representation_generator(self, stream, resource_class):
        """
        Creates a representation generator from the given arguments. This
        generator has a `run` method which writes out the serialized
        resource representation to the given stream.
        """
        raise NotImplementedError('Abstract method.')


class RepresentationHandler(object):
    """
    Base class for representation handlers (parsers and generators) responsible
    for the conversion data element tree <-> representation.
    """
    def __init__(self, stream, resource_class):
        self._stream = stream
        self._resource_class = resource_class
        self.__config = {}

    def configure(self, **config):
        self.__config.update(config)

    def get_option(self, option, default=None):
        return self.__config.get(option, default)

    def set_option(self, option, value):
        self.__config[option] = value


class RepresenterRegistry(object):
    """
    Registry for representer classes and representer factories.
    """

    def __init__(self):
        self.__rpr_classes = {}
        self.__mp_regs = {}
        self.__rpr_factories = {}

    def register_representer_class(self, representer_class):
        if representer_class in self.__rpr_classes:
            raise ValueError('The representer class "%s" has already been '
                             'registered.' % representer_class)
        self.__rpr_classes[representer_class.content_type] = representer_class
        # Create and hold a mapping registry for the registered resource 
        # representer class.
        mp_reg = representer_class.make_mapping_registry()
        self.__mp_regs[representer_class.content_type] = mp_reg

    def is_registered_representer_class(self, representer_class):
        return representer_class in self.__rpr_classes

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
        if not issubclass(type(resource_class), type):
            raise ValueError('Representers can only be registered for '
                             'resource classes (got: %s).' % resource_class)
        if not content_type in self.__rpr_classes:
            raise ValueError('No representer class has been registered for '
                             'content type "%s".' % content_type)
        # Create or update a mapping.
        mp_reg = self.__mp_regs[content_type]
        mp = mp_reg.find_mapping(resource_class)
        if mp is None:
            # No mapping was registered yet for this resource class or any
            # of its base classes; create a new one on the fly.
            mp = mp_reg.create_mapping(resource_class, configuration)
            mp_reg.set_mapping(mp)
        elif not configuration is None:
            if resource_class is mp.mapped_class:
                # We have additional configuration for an existing mapping. 
                mp.configuration.update(configuration)
            else:
                # We have a derived class with additional configuration.
                new_mp = mp_reg.create_mapping(resource_class,
                                               configuration=mp.configuration)
                new_mp.configuration.update(configuration)
                mp_reg.set_mapping(new_mp)
        elif not resource_class is mp.mapped_class:
            # We have a derived class without additional configuration.
            new_mp = mp_reg.create_mapping(resource_class,
                                           configuration=mp.configuration)
            mp_reg.set_mapping(new_mp)
        # Register factory resource -> representer for the given resource
        # class, content type combination.
        rpr_cls = self.__rpr_classes[content_type]
        self.__rpr_factories[(resource_class, content_type)] = \
                                            rpr_cls.create_from_resource

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
    def __init__(self, stream, resource_class):
        self._stream = stream
        self._resource_class = resource_class
        self.__config = {}

    def configure(self, **config):
        self.__config.update(config)

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


def data_element_tree_to_string(data_element):
    """
    Creates a string representation of the given data element tree.
    """
    def __dump(data_el, stream, offset):
        name = data_el.__class__.__name__
        stream.write("%s(" % name)
        offset = offset + len(name) + 1
        first_attr = True
        for attr in data_el.mapping.attribute_iterator():
            if first_attr:
                first_attr = False
            else:
                stream.write(',\n' + ' ' * offset)
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                stream.write("%s=%s" % (attr.name,
                                        str(data_el.get_terminal(attr)))
                             )
            else:
                nested_el = data_el.get_nested(attr)
                if attr.kind == ResourceAttributeKinds.COLLECTION:
                    stream.write('%s=[' % attr.name)
                    first_member = True
                    for member_el in nested_el.get_members():
                        if first_member:
                            stream.write('\n' + ' ' * (offset + 2))
                            first_member = False
                        else:
                            stream.write(',\n' + ' ' * (offset + 2))
                        __dump(member_el, stream, offset + 2)
                    stream.write('\n' + ' ' * (offset + 2) + ']')
                else:
                    stream.write("%s=" % attr.name)
                    __dump(nested_el, stream, offset)
        stream.write(')')
    stream = StringIO()
    __dump(data_element, stream, 0)
    return stream.getvalue()
