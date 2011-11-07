"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Representers for resources and entities.

Created on May 18, 2011.
"""

from StringIO import StringIO
from everest.entities.utils import get_entity_class_for_member
from everest.entities.utils import get_transient_aggregate
from everest.mime import CsvMime
from everest.representers.attributes import CollectionAttributeMapper
from everest.representers.attributes import LinkAttributeMapper
from everest.representers.attributes import MemberAttributeMapper
from everest.representers.attributes import ResourceAttributeKinds
from everest.representers.interfaces import ICustomDataElement
from everest.representers.interfaces import IDataElementRegistry
from everest.representers.interfaces import IExplicitDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.utils import data_element_tree_to_string
from everest.representers.utils import get_data_element_registry
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResourceLink
from everest.resources.link import Link
from everest.resources.utils import provides_member_resource
from everest.url import resource_to_url
from everest.url import url_to_resource
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
import inspect

__docformat__ = 'reStructuredText en'
__all__ = ['CollectionResourceRepresenter',
           'DataElement',
           'MemberResourceRepresenter',
           'ResourceRepresenter',
           ]


class DataElement(object):
    """
    Abstract base class for data element classes.

    Data elements manage value state during serialization and deserialization.
    Implementations may need to be adapted to the format of the external
    representation they manage.
    """

    implements(IExplicitDataElement)

    #: The class to be mapped to a representation.
    mapped_class = None
    #: Static attribute mapper.
    mapper = None

    @classmethod
    def create(cls):
        """
        Basic factory method.
        """
        inst = cls()
        return inst

    def __str__(self):
        return data_element_tree_to_string(self)

    @classmethod
    def create_from_resource(cls, resource):
        """
        (Abstract) factory method taking a resource as input.
        """
        raise NotImplementedError('Abstract method.')

    def get_terminal(self, attr):
        """
        Returns the value for the given mapped terminal resource attribute.

        @return: attribute value or `None` if no value is found for the given
            attribute name.
        """
        raise NotImplementedError('Abstract method.')

    def set_terminal(self, attr, value):
        """
        Sets the value for the given mapped terminal resource attribute.
        """
        raise NotImplementedError('Abstract method.')

    def get_nested(self, attr):
        """
        Returns the mapped nested resource attribute (either a member or a
        collection resource attribute).

        @returns: object implementing `:class:IDataelement` or
          `None` if no nested resource is found for the given attribute name.
        """
        raise NotImplementedError('Abstract method.')

    def set_nested(self, attr, data_element):
        """
        Sets the value for the given mapped nested resource attribute (either
        a member or a collection resource attribute).

        @param data_element: a :class:DataElement or :class:LinkedDataElement
          object containing nested resource data.
        """
        raise NotImplementedError('Abstract method.')

    def add_member(self, data_element):
        """
        Adds the given member data element to this data element.
        """
        raise NotImplementedError('Abstract method.')

    def get_members(self):
        """
        Returns all member data elements added to this data element.
        """
        raise NotImplementedError('Abstract method.')


class SimpleDataElement(DataElement):
    """
    Basic implementation of a data element.
    """
    __nested = None
    __members = None

    @classmethod
    def create_from_resource(cls, resource): # ignore resource pylint:disable=W0613,W0221
        return cls()

    def get_terminal(self, attr):
        # The ID attribute is optional, so we can not assume it is there.
        try:
            value = getattr(self, attr.representation_name)
        except AttributeError, err:
            if attr.representation_name == 'id':
                value = None
            else:
                raise err
        return value

    def set_terminal(self, attr, value):
        setattr(self, attr.representation_name, value)

    def get_nested(self, attr):
        nested = self.__get_nested()
        return nested.get(attr.representation_name)

    def set_nested(self, attr, data_element):
        nested = self.__get_nested()
        nested[attr.representation_name] = data_element

    def add_member(self, data_element):
        members = self.__get_members()
        members.append(data_element)

    def get_members(self):
        return self.__get_members()

    def __get_nested(self):
        if self.__nested is None:
            self.__nested = {}
        return self.__nested

    def __get_members(self):
        if self.__members is None:
            self.__members = []
        return self.__members


class LinkedDataElement(object):
    """
    Data element managing a linked resource during serialization and
    deserialization.
    """

    implements(ILinkedDataElement)

    mapped_class = Link

    @classmethod
    def create(cls, linked_data_element_class, url,
               relation=None, title=None):
        raise NotImplementedError('Abstract method.')

    @classmethod
    def create_from_resource(cls, resource):
        raise NotImplementedError('Abstract method.')

    def get_url(self):
        raise NotImplementedError('Abstract method.')

    def get_relation(self):
        raise NotImplementedError('Abstract method.')

    def get_title(self):
        raise NotImplementedError('Abstract method.')


class SimpleLinkedDataElement(LinkedDataElement):
    """
    Basic implementation of a linked data element.
    """
    __url = None
    __relation = None
    __title = None

    @classmethod
    def create(cls, linked_data_element_class, url,
               relation=None, title=None):
        inst = cls()
        inst.__url = url
        inst.__relation = relation
        inst.__title = title
        return inst

    @classmethod
    def create_from_resource(cls, resource):
        de_reg = get_data_element_registry(CsvMime)
        rc_de_cls = de_reg.get_data_element_class(type(resource))
        return cls.create(rc_de_cls, resource_to_url(resource),
                          relation=resource.relation,
                          title=resource.title)

    def get_url(self):
        return self.__url

    def get_relation(self):
        return self.__relation

    def get_title(self):
        return self.__title


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


class DataElementRegistry(object):

    implements(IDataElementRegistry)

    data_element_class = None
    linked_data_element_class = None
    configuration_class = None

    def __init__(self):
        self.__de_map = {}
        # Perform static initializations.
        self._initialize()

    def create_data_element_class(self, mapped_class, configuration,
                                  base_class=None):
        """
        Creates a new data element class for the given mapped class and
        representer configuration.

        :param configuration: configuration for the new data element class.
        :type configuration: :class:`RepresenterConfiguration`
        :returns: new type implementing :class:`IDataElement`
        """
        if configuration is None:
            configuration = self.configuration_class() # pylint: disable=E1102
        if base_class is None:
            base_class = self.data_element_class
        name = "%s%s" % (mapped_class.__name__, base_class.__name__)
        provided_ifcs = provided_by(object.__new__(mapped_class))
        if IMemberResource in provided_ifcs:
            mapper = MemberAttributeMapper(configuration)
        elif ICollectionResource in provided_ifcs:
            mapper = CollectionAttributeMapper(configuration)
        elif IResourceLink in provided_ifcs:
            mapper = LinkAttributeMapper(configuration)
        else:
            raise ValueError('Mapped class for data element class does not '
                             'implement one of the required interfaces.')
        custom_de_cls = type(name, (base_class,), {})
        custom_de_cls.mapper = mapper
        custom_de_cls.mapped_class = mapped_class
        return custom_de_cls

    def set_data_element_class(self, data_element_class):
        """
        Registers the given data element class.

        :param data_element_class: type implementing :class:`IDataElement`
        :type data_element_class: type
        """
        if self.__de_map.has_key(data_element_class.mapped_class):
            raise ValueError('Class "%s" has already been registered.'
                             % data_element_class.mapped_class)
        self.__de_map[data_element_class.mapped_class] = data_element_class

    def get_data_element_class(self, mapped_class):
        """
        Returns the data element class registered for the given mapped class.

        :param mapped_class: mapped type
        :type mapped_class: type
        :returns: type implementing :class:`IDataElement`
        """
        for base_cls in mapped_class.__mro__:
            try:
                return self.__de_map[base_cls]
            except KeyError:
                continue
        raise KeyError('No data element class registered for "%s" or any '
                       'of its base classes.' % mapped_class)

    def get_data_element_classes(self):
        """
        Returns a list of all registered data element classes.

        :returns: list of types implementing :class:`IDataElement`
        """
        return self.__de_map.iteritems()

    def _initialize(self):
        # Implement this for static initializations.
        raise NotImplementedError('Abstract method.')


class SimpleDataElementRegistry(DataElementRegistry):
    data_element_class = SimpleDataElement
    linked_data_element_class = SimpleLinkedDataElement
    configuration_class = RepresenterConfiguration

    def _initialize(self):
        # Create and register the linked data element class.
        configuration = self.configuration_class()
        de_cls = \
            self.create_data_element_class(Link, configuration,
                                           base_class=
                                            self.linked_data_element_class)
        self.set_data_element_class(de_cls)


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


class DataElementParser(object):
#    def _extract_member_resource(self, data_element):
#        mapped_attributes = data_element.mapper.get_mapped_attributes(
#                                                    data_element.mapped_class)
#        rc = self._extract_member_content(data_element, mapped_attributes)
#        return rc

#    def _extract_member_content(self, data_element, mapped_attributes):
#        # Custom resource extraction.
#        if ICustomDataElement in provided_by(data_element):
#            rc = data_element.extract()
#        else:
#            data = {}
#            for attr in mapped_attributes:
#                value = self._extract_attribute(data_element, attr)
#                if not value is None:
#                    data[attr.representation_name] = value
#            rc = data_element.mapped_class.create_from_data(data)
#        return rc
#
#    def _extract_attribute(self, data_element, attr):
#        """
#        Extracts the given attribute from the given data element (inverse
#        operation to `_inject_attribute`). Note that this method returns
#        resources as entities or entity collections.
#
#        Returns `None` if the attribute is not found.
#
#        :param data_element: data element to extract an attribute from
#          (:class:`DataElement` instance)
#        :param attr: mapped attribute (:class:`MappedAttribute` instance)
#        :return: attribute value or `None`
#        """
#        if attr.kind == ResourceAttributeKinds.TERMINAL:
#            value = data_element.get_terminal(attr)
#        else:
#            rc_el = data_element.get_nested(attr)
#            if rc_el is None:
#                value = None
#            else:
#                if attr.kind == ResourceAttributeKinds.MEMBER:
#                    # Member resource. Extract entity.
#                    if not attr.write_as_link is False:
#                        rc = self._extract_link(rc_el)
#                    else:
#                        rc = self._extract_member_resource(rc_el)
#                    value = rc.get_entity()
#                else:
#                    # Collection resource. Extract list of entities.
#                    if not attr.write_as_link is False:
#                        rc = self._extract_link(rc_el)
#                    else:
#                        rc = self._extract_collection_resource(rc_el)
#                    value = [member.get_entity() for member in rc]
#        return value
#
#    def _extract_link(self, link_el):
#        url = link_el.get_url()
#        return url_to_resource(url)

    def run(self, data_element):
        if provides_member_resource(data_element.mapped_class):
            rc = self.extract_member_resource(data_element, 0)
        else:
            rc = self.extract_collection_resource(data_element, 0)
        return rc

    def extract_member_resource(self, member_data_element, nesting_level=0):
        """
        Extracts a member resource from the given data element.

        Since all value state of a resource is held in its underlying entity,
        the latter is constructed from the incoming data and then converted
        to a resource.
        """
        data = {}
        mb_cls = member_data_element.mapped_class
        attrs = member_data_element.mapper.get_mapped_attributes(mb_cls)
        for attr in attrs.values():
            if attr.ignore is True \
               or (attr.kind == ResourceAttributeKinds.COLLECTION
                   and nesting_level > 0 and not attr.ignore is False):
                continue
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                value = member_data_element.get_terminal(attr)
            elif attr.kind in (ResourceAttributeKinds.MEMBER,
                               ResourceAttributeKinds.COLLECTION):
                rc_data_el = member_data_element.get_nested(attr)
                if rc_data_el is None:
                    # Optional attribute.
                    value = None
                else:
                    if attr.kind == ResourceAttributeKinds.MEMBER:
                        if ILinkedDataElement in provided_by(rc_data_el):
                            url = rc_data_el.get_url()
                            rc = url_to_resource(url)
                        else:
                            rc = self.extract_member_resource(rc_data_el,
                                                              nesting_level + 1)
                        value = rc.get_entity()
                    else:
                        if ILinkedDataElement in provided_by(rc_data_el):
                            url = rc_data_el.get_url()
                            rc = url_to_resource(url)
                        else:
                            rc = \
                              self.extract_collection_resource(rc_data_el,
                                                               nesting_level + 1)
                        value = [mb.get_entity() for mb in rc]
            else:
                raise ValueError('Invalid resource attribute kind.')
            if not value is None:
                data[attr.entity_name] = value
        entity = get_entity_class_for_member(mb_cls).create_from_data(data)
        return mb_cls.create_from_entity(entity)

    def extract_collection_resource(self, rc_data_el, nesting_level=0):
        """
        Extracts a collection resource from the given data element.
        """
        coll_cls = rc_data_el.mapped_class
        agg = get_transient_aggregate(coll_cls)
        coll = coll_cls.create_from_aggregate(agg)
        for member_el in rc_data_el.get_members():
            mb = self.extract_member_resource(member_el, nesting_level + 1)
            coll.add(mb)
        return coll


class DataElementGenerator(object):
    def __init__(self, data_element_registry):
        self._data_element_registry = data_element_registry

    def run(self, resource, mapping_info=None):
        if provides_member_resource(type(resource)):
            data_el = self._inject_member_resource(resource, 0,
                                                   mapping_info)
        else:
            data_el = self._inject_collection_resource(resource, 0,
                                                       mapping_info)
        return data_el

    def _inject_member_resource(self, member, nesting_level, mapping_info):
        de_reg = self._data_element_registry
        de_cls = de_reg.get_data_element_class(type(member))
        mb_data_el = de_cls.create_from_resource(member)
        mapped_attrs = mb_data_el.mapper.get_mapped_attributes(
                                                    mb_data_el.mapped_class,
                                                    info=mapping_info)
        self._inject_member_content(mb_data_el, member, mapped_attrs.values(),
                                    nesting_level)
        return mb_data_el

    def _inject_collection_resource(self, collection, nesting_level,
                                    mapping_info):
        de_reg = self._data_element_registry
        coll_de_cls = de_reg.get_data_element_class(type(collection))
        coll_data_el = coll_de_cls.create_from_resource(collection)
        if ICustomDataElement in provided_by(coll_data_el):
            # Custom resource injection.
            coll_data_el.inject(collection)
        else:
            for member in collection:
                mapped_attrs = \
                  coll_data_el.mapper.get_mapped_attributes(type(member),
                                                            info=mapping_info)
                mb_de_cls = de_reg.get_data_element_class(type(member))
                mb_data_el = mb_de_cls.create_from_resource(member)
                self._inject_member_content(mb_data_el, member,
                                            mapped_attrs.values(),
                                            nesting_level + 1)
                coll_data_el.add_member(mb_data_el)
        return coll_data_el

    def _inject_member_content(self, data_element, member, mapped_attributes,
                               nesting_level):
        if ICustomDataElement in provided_by(data_element):
            # Custom resource injection.
            data_element.inject(member)
        else:
            for attr in mapped_attributes:
                if self._is_ignored_attr(attr, nesting_level):
                    continue
                value = getattr(member, attr.name)
                if value is None:
                    # None values are ignored.
                    continue
                self._inject_attribute(data_element, attr, value,
                                       nesting_level)

    def _inject_attribute(self, data_element, attr, value, nesting_level):
        """
        Injects the given value as attribute of the given name into the given
        data element (inverse operation to `_extract_attribute`).

        :param data_element: data element to inject an attribute into
          (:class:`DateElement` instance).
        :param attr: mapped attribute (:class:`MappedAttribute` instance).
        :param value: value to inject.
        :param int nesting_level: nesting level of this data element in the
          tree
        """
        if attr.kind == ResourceAttributeKinds.TERMINAL:
            data_element.set_terminal(attr, value)
        else:
            if not attr.write_as_link is False:
                rc_data_el = self._inject_link(value)
            else:
                if attr.kind == ResourceAttributeKinds.MEMBER:
                    rc_data_el = self._inject_member_resource(value,
                                                              nesting_level + 1,
                                                              None)
                else:
                    rc_data_el = \
                            self._inject_collection_resource(value,
                                                             nesting_level + 1,
                                                             None)
            data_element.set_nested(attr, rc_data_el)

    def _inject_link(self, rc):
        de_reg = self._data_element_registry
        link_de_cls = de_reg.get_data_element_class(Link)
        return link_de_cls.create_from_resource(rc)

#        url = resource_to_url(rc)
#        de_reg = self._data_element_registry
#        linked_de_cls = de_reg.get_data_element_class(type(rc))
#        link_de_cls = de_reg.get_data_element_class(Link)
#        if attr.kind == ResourceAttributeKinds.MEMBER:
#            link_data_el = link_de_cls.create(linked_de_cls, url,
#                                              title=rc.title, id=rc.id)
#        else:
#            link_data_el = link_de_cls.create(linked_de_cls, url,
#                                              title=rc.title)
#        return link_data_el

#    def _is_link_attr(self, attr, nesting_level):
#        """
#        Checks whether the given attribute should be interpreted as a link
#        at the given nesting level.
#
#        The default behavior is to interpret all nested attributes as links.
#        """
#        return attr.write_as_link is True \
#                or (not attr.write_as_link is False and nesting_level > 0)

    def _is_ignored_attr(self, attr, nesting_level):
        """
        Checks whether the given attribute should be ignored at the given
        nesting level.

        The default behavior is to ignore nested collection attributes.
        """
        return attr.ignore is True \
                or (attr.kind == ResourceAttributeKinds.COLLECTION
                    and nesting_level > 0 and not attr.ignore is False)


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

    def data_from_representation(self, representation):
        stream = StringIO(representation)
        parser = self._make_representation_parser(stream, self.resource_class)
        return parser.run()

    def representation_from_data(self, data_element):
        stream = StringIO()
        generator = \
            self._make_representation_generator(stream, self.resource_class)
        return generator.run(data_element)

    def resource_from_data(self, data_element):
        """
        Extracts serialized data from the given data element and constructs
        a resource from it.

        @return: an object implementing
                :class:`everest.resources.interfaces.IResource`
        """
        parser = self._make_data_element_parser()
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

    def _make_data_element_parser(self):
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


class _RepresentationHandler(object):
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
        :return: the parsed resource.
        """
        raise NotImplementedError('Abstract method.')


class RepresentationGenerator(_RepresentationHandler):

    def run(self, data_element):
        """
        :param data_element: the `class:`DataElement` to be serialized.
        """
        raise NotImplementedError('Abstract method.')
