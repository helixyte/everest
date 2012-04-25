"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Representers for resources and entities.

Created on May 18, 2011.
"""

from StringIO import StringIO
from everest.representers.utils import get_data_element_registry
from everest.resources.attributes import ResourceAttributeKinds
import inspect

__docformat__ = 'reStructuredText en'
__all__ = ['RepresentationHandler',
           'Representer',
           'RepresenterConfiguration',
           'RepresenterRegistry',
           'ResourceRepresenter',
           ]


class RepresenterConfiguration(object):
    """
    Base class for containers declaring representer configuration data as
    static class attributes.

    Only public attributes declared in the :cvar:`config_attributes`
    attribute are allowed as configuration value names.

    Sharing of common data is supported through inheritance. Configuration
    values declared in classes higher in the inheritance hierarchy will
    replace previous declarations with the same name. The exception from
    this rule is the `mapping` configuration option, which is a dictionary
    that will be updated rather than replaced.

    Allowed configuration attribute names:

    mapping :
        Allows declaration of configuration dictionaries for each mapped
        attribute, e.g. ::

        mapping = dict(my_attribute_to_ignore=dict(ignore=True))

    The mapping allows the following options to be configured:

    representation_name :
        The name to use in the mapped representation.
    write_as_link :
        Write this mapped attribute as a link rather than as a full
        representation.
    ignore :
        Ignore this attribute when creating a representation.
    """

    #: List of configuration attribute names for this configuration class
    _config_attributes = ['mapping']
    #: Allowed options for attribute mappings.
    _mapping_options = ['repr_name', 'write_as_link', 'ignore']

    def __init__(self, config=None):
        self.__config = self.__build_config()
        if not config is None:
            for option_name, option_value in config.iteritems():
                self.set_option(option_name, option_value)

    def get_option(self, name):
        """
        Returns the value for the specified configuration option.

        :returns: configuration option value or `None`, if the option was not
          set.
        """
        self.__validate_option_name(name)
        return self.__config.get(name, None)

    def set_option(self, name, value):
        """
        Sets the specified option to the given value.
        """
        self.__validate_option_name(name)
        self.__config[name] = value

    def get_mapping(self, name):
        """
        Returns the mapping options for the given attribute name. All options
        that were not explicitly configured are given a default value of
        `None`.

        :returns: mapping options dictionary (including default `None` values)
        """
        cls_mapping = dict([(k, None) for k in self._mapping_options])
        cls_mapping.update(self.__config.get('mapping', {}).get(name, {}))
        return cls_mapping

    def __build_config(self):
        config = {}
        for base in self.__class__.__mro__[::-1]:
            for attr, value in base.__dict__.items():
                # Ignore protected/private/magic class attributes.
                if attr.startswith('_'):
                    continue
                # Ignore attributes that are public methods.
                if inspect.isfunction(value):
                    continue
                # Validate all others.
                self.__validate_option_name(attr)
                # The mapping is updated rather than replaced.
                if attr == 'mapping':
                    cnf = config.setdefault(attr, {})
                    # Check that all mapping option dictionaries have only
                    # valid option keys.
                    for mapping_options in value.values():
                        for name in mapping_options.keys():
                            self.__validate_mapping_option_name(name)
                    cnf.update(value.items())
                else:
                    config[attr] = value
        return config

    def __validate_option_name(self, name):
        if not name in self._config_attributes:
            raise ValueError('Invalid configuration option name "%s" for '
                             '%s representer.' %
                             (name, self.__class__.__name__))

    def __validate_mapping_option_name(self, name):
        if not name in self._mapping_options:
            raise ValueError('Invalid mapping option "%s" '
                             'for %s representer.'
                             % (name, self.__class__.__name__))


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

    def __init__(self, resource_class, data_element_registry):
        Representer.__init__(self)
        self.resource_class = resource_class
        self.__reference_converter = None
        self._data_element_registry = data_element_registry

    @classmethod
    def create_from_resource(cls, rc):
        de_reg = get_data_element_registry(cls.content_type)
        return cls(type(rc), de_reg)

    @classmethod
    def make_data_element_registry(cls):
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

    def resource_from_data(self, data_element, resolve_urls=True):
        """
        Extracts serialized data from the given data element and constructs
        a resource from it.

        :returns: object implementing
            :class:`everest.resources.interfaces.IResource`
        """
        parser = self._make_data_element_parser(resolve_urls=resolve_urls)
        return parser.run(data_element)

    def data_from_resource(self, resource, mapping_info=None):
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
        objects (:class:`RepresenterConfiguration`).
        """
        generator = self._make_data_element_generator()
        return generator.run(resource, mapping_info=mapping_info)

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

    def _make_data_element_parser(self, resolve_urls=True):
        """
        Creates a data element parser the `run` method of which converts
        a data element tree into the resource it represents.
        """
        raise NotImplementedError('Abstract method.')

    def _make_data_element_generator(self):
        """
        Creates a data element generator the `run` method of which converts
        a resource into a data element tree.
        """
        raise NotImplementedError('Abstract method.')


class RepresentationHandler(object):
    """
    Base class for representation handlers (parsers and generators) responsible
    for the conversion resource <-> representation.
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
        self.__de_regs = {}
        self.__rpr_factories = {}

    def register_representer_class(self, representer_class):
        if representer_class in self.__rpr_classes:
            raise ValueError('The representer class "%s" has already been '
                             'registered.' % representer_class)
        self.__rpr_classes[representer_class.content_type] = representer_class
        # Create and store a data element registry for the registered resource 
        # representer class.
        de_reg = representer_class.make_data_element_registry()
        self.__de_regs[representer_class.content_type] = de_reg

    def is_registered_representer_class(self, representer_class):
        return representer_class in self.__rpr_classes

    def get_data_element_registry(self, content_type):
        return self.__de_regs.get(content_type)

    def register(self, resource_class, content_type,
                 configuration=None, mapping_info=None):
        if not issubclass(type(resource_class), type):
            raise ValueError('Representers can only be registered for '
                             'resource classes (got: %s).' % resource_class)
        # If we were passed a configuration class, instantiate it.
        if type(configuration) is type:
            configuration = configuration()
        # Register customized data element class for the representer
        # class registered for the given content type.
        rpr_cls = self.__rpr_classes[content_type]
        de_reg = self.__de_regs[content_type]
        de_cls = de_reg.create_data_element_class(resource_class, configuration)
        de_reg.set_data_element_class(de_cls)
        if not mapping_info is None:
            mapping = de_cls.mapper.get_config_option('mapping')
            if mapping is None:
                de_cls.mapper.set_config_option('mapping', mapping_info)
            else:
                mapping.update(mapping_info)
        # Register factory resource -> representer for the given resource
        # class, content type combination.
        self.__rpr_factories[(resource_class, content_type)] = \
                                            rpr_cls.create_from_resource

    def get(self, resource, content_type):
        for rc_cls in type(resource).__mro__:
            try:
                rpr_fac = self.__rpr_factories[(rc_cls, content_type)]
            except KeyError:
                rpr = None
            else:
                rpr = rpr_fac(resource)
                break
        return rpr


def data_element_tree_to_string(data_element):
    """
    Creates a string representation of the given data element tree.
    """
    def __dump(data_el, stream, offset):
        name = data_el.__class__.__name__
        stream.write("%s(" % name)
        offset = offset + len(name) + 1
        first_attr = True
        attrs = \
            data_el.mapper.get_mapped_attributes(data_el.mapped_class)
        for attr in attrs.values():
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
