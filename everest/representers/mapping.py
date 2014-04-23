"""
Mapping and mapping registry.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 4, 2012.
"""
from collections import OrderedDict

from pyramid.compat import iteritems_
from pyramid.compat import itervalues_

from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.representers.attributes import MappedAttribute
from everest.representers.attributes import MappedAttributeKey
from everest.representers.config import RepresenterConfiguration
from everest.representers.dataelements import SimpleCollectionDataElement
from everest.representers.dataelements import SimpleLinkedDataElement
from everest.representers.dataelements import SimpleMemberDataElement
from everest.representers.interfaces import IDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.representers.traversal import DataElementBuilderResourceTreeVisitor
from everest.representers.traversal import ResourceTreeTraverser
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResourceLink
from everest.resources.link import Link
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import provides_collection_resource
from everest.resources.utils import provides_member_resource
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['Mapping',
           'MappingRegistry',
           'PruningMapping',
           'SimpleMappingRegistry',
           ]


class Mapping(object):
    """
    Performs configurable resource <-> data element tree <-> representation
    attribute mappings.

    :property mapped_class: The resource class mapped by this mapping.
    :property data_element_class: The data element class for this mapping.
    """
    #: Flag indicating if this mapping should prune the attribute tree
    #: according to the IGNORE settings.
    is_pruning = False

    def __init__(self, mapping_registry, mapped_class, data_element_class,
                 configuration):
        """
        :param configuration: Mapping configuration object.
        """
        self.__mp_reg = mapping_registry
        self.__mapped_cls = mapped_class
        self.__is_collection_mapping = \
                                provides_collection_resource(mapped_class)
        self.__de_cls = data_element_class
        # List of configurations; the last one added is the active one.
        self.__configurations = [configuration]
        #
        self.__mapped_attr_cache = {}

    def clone(self, options=None, attribute_options=None):
        """
        Returns a clone of this mapping that is configured with the given
        option and attribute option dictionaries.

        :param dict options: Maps representer options to their values.
        :param dict attribute_options: Maps attribute names to dictionaries
          mapping attribute options to their values.
        """
        copied_cfg = self.__configurations[-1].copy()
        upd_cfg = type(copied_cfg)(options=options,
                                   attribute_options=attribute_options)
        copied_cfg.update(upd_cfg)
        return self.__class__(self.__mp_reg, self.__mapped_cls,
                              self.__de_cls, copied_cfg)

    def update(self, options=None, attribute_options=None):
        """
        Updates this mapping with the given option and attribute option maps.

        :param dict options: Maps representer options to their values.
        :param dict attribute_options: Maps attribute names to dictionaries
          mapping attribute options to their values.
        """
        attr_map = self.__get_attribute_map(self.__mapped_cls, None, 0)
        for attributes in attribute_options:
            for attr_name in attributes:
                if not attr_name in attr_map:
                    raise AttributeError('Trying to configure non-existing '
                                         'resource attribute "%s"'
                                         % (attr_name))
        cfg = RepresenterConfiguration(options=options,
                                       attribute_options=attribute_options)
        self.configuration.update(cfg)

    @property
    def configuration(self):
        """
        Returns this mapping's current configuration object.
        """
        # We clear the cache every time the configuration is accessed since
        # we can not guarantee that it stays unchanged.
        self.__mapped_attr_cache.clear()
        return self.__configurations[-1]

    def get_attribute_map(self, mapped_class=None, key=None):
        """
        Returns an ordered map of the mapped attributes for the given mapped
        class and attribute key.

        :param key: Tuple of attribute names specifying a path to a nested
          attribute in a resource tree. If this is not given, all attributes
          in this mapping will be returned.
        """
        if mapped_class is None:
            mapped_class = self.__mapped_cls
        if key is None:
            key = MappedAttributeKey(())
        return OrderedDict([(attr.resource_attr, attr)
                            for attr in self._attribute_iterator(mapped_class,
                                                                 key)])

    def get_attribute(self, attribute_name, mapped_class=None, key=None):
        """
        Returns the specified attribute from the map of all mapped attributes
        for the given mapped class and attribute key. See
        :method:`get_attribute_map` for details.
        """
        attr_map = self.__get_attribute_map(mapped_class, key, 0)
        try:
            return attr_map[attribute_name]
        except KeyError:
            raise AttributeError(attribute_name)

    def has_attribute(self, attribute_name):
        """
        Checks if this mapping has an attribute of the given name.

        :returns: Check result (Boolean)
        """
        return attribute_name in self.__get_attribute_map(None, None, 0)

    def get_attribute_by_repr(self, attribute_repr_name, mapped_class=None,
                              key=None):
        """
        Returns the attribute (specified by its representation name) from
        the map of all mapped attributes for the given mapped class and
        attribute key. See :method:`get_attribute_map` for details.
        """
        attr_map = self.__get_attribute_map(mapped_class, key, 1)
        try:
            return attr_map[attribute_repr_name]
        except KeyError:
            raise AttributeError(attribute_repr_name)

    def has_attribute_repr(self, attribute_repr_name):
        """
        Checks if this mapping has an attribute of the given representation
        name.

        :returns: Check result (Boolean)
        """
        return attribute_repr_name in self.__get_attribute_map(None, None, 1)

    def attribute_iterator(self, mapped_class=None, key=None):
        """
        Returns an iterator over all mapped attributes for the given mapped
        class and attribute key. See :method:`get_attribute_map` for details.
        """
        for attr in self._attribute_iterator(mapped_class, key):
            yield attr

    def terminal_attribute_iterator(self, mapped_class=None, key=None):
        """
        Returns an iterator over all terminal mapped attributes for the given
        mapped class and attribute key. See :method:`get_attribute_map` for
        details.
        """
        for attr in self._attribute_iterator(mapped_class, key):
            if attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                yield attr

    def nonterminal_attribute_iterator(self, mapped_class=None, key=None):
        """
        Returns an iterator over all non-terminal mapped attributes for the
        given mapped class and attribute key. See :method:`get_attribute_map`
        for details.
        """
        for attr in self._attribute_iterator(mapped_class, key):
            if attr.kind != RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                yield attr

    def create_data_element(self, mapped_class=None):
        """
        Returns a new data element for the given mapped class.

        :returns: object implementing :class:`IResourceDataElement`.
        """
        if not mapped_class is None and mapped_class != self.__mapped_cls:
            mp = self.__mp_reg.find_or_create_mapping(mapped_class)
            data_el = mp.create_data_element()
        else:
            data_el = self.__de_cls.create()
        return data_el

    def create_linked_data_element(self, url, kind, id=None, # pylint: disable=W0622
                                   relation=None, title=None):
        """
        Returns a new linked data element for the given url and kind.

        :param str url: URL to assign to the linked data element.
        :param str kind: kind of the resource that is linked. One of the
          constantes defined by :class:`everest.constants.RESOURCE_KINDS`.
        :returns: object implementing :class:`ILinkedDataElement`.
        """
        mp = self.__mp_reg.find_or_create_mapping(Link)
        return mp.data_element_class.create(url, kind, id=id,
                                            relation=relation, title=title)

    def create_data_element_from_resource(self, resource):
        """
        Returns a new data element for the given resource object.

        :returns: object implementing :class:`IResourceDataElement`.
        """
        mp = self.__mp_reg.find_or_create_mapping(type(resource))
        return mp.data_element_class.create_from_resource(resource)

    def create_linked_data_element_from_resource(self, resource):
        """
        Returns a new linked data element for the given resource object.

        :returns: object implementing :class:`ILinkedDataElement`.
        """
        mp = self.__mp_reg.find_or_create_mapping(Link)
        return mp.data_element_class.create_from_resource(resource)

    def map_to_resource(self, data_element, resource=None):
        """
        Maps the given data element to a new resource or updates the given
        resource.

        :raises ValueError: If :param:`data_element` does not provide
          :class:`everest.representers.interfaces.IDataElement`.
        """
        if not IDataElement.providedBy(data_element): # pylint:disable=E1101
            raise ValueError('Expected data element, got %s.' % data_element)
        if resource is None:
            coll = \
                create_staging_collection(data_element.mapping.mapped_class)
            agg = coll.get_aggregate()
            agg.add(data_element)
            if IMemberDataElement.providedBy(data_element): # pylint: disable=E1101
                ent = next(iter(agg))
                resource = \
                    data_element.mapping.mapped_class.create_from_entity(ent)
            else:
                resource = coll
        else:
            resource.update(data_element)
        return resource

    def map_to_data_element(self, resource):
        """
        Maps the given resource to a data element tree.
        """
        trv = ResourceTreeTraverser(resource, self.as_pruning())
        visitor = DataElementBuilderResourceTreeVisitor(self)
        trv.run(visitor)
        return visitor.data_element

    def as_pruning(self):
        """
        Returns a clone of this mapping with the `is_pruning` flag set to
        *True*.
        """
        return PruningMapping(self.__mp_reg, self.__mapped_cls, self.__de_cls,
                              self.__configurations[-1])

    def push_configuration(self, configuration):
        """
        Pushes the given configuration object on the stack of configurations
        managed by this mapping and makes it the active configuration.
        """
        self.__mapped_attr_cache.clear()
        self.__configurations.append(configuration)

    def pop_configuration(self):
        """
        Pushes the currently active configuration from the stack of
        configurations managed by this mapping.

        :raises IndexError: If there is only one configuration in the stack.
        """
        if len(self.__configurations) == 1:
            raise IndexError('Can not pop the last configuration from the '
                             'stack of configurations.')
        self.__configurations.pop()
        self.__mapped_attr_cache.clear()

    def with_updated_configuration(self, options=None,
                                   attribute_options=None):
        """
        Returns a context in which this mapping is updated with the given
        options and attribute options.
        """
        new_cfg = self.__configurations[-1].copy()
        if not options is None:
            for o_name, o_value in iteritems_(options):
                new_cfg.set_option(o_name, o_value)
        if not attribute_options is None:
            for attr_name, ao_opts in iteritems_(attribute_options):
                for ao_name, ao_value in iteritems_(ao_opts):
                    new_cfg.set_attribute_option(attr_name, ao_name, ao_value)
#        upd_cfg = type(new_cfg)(options=options,
#                                attribute_options=attribute_options)
#        new_cfg.update(upd_cfg)
        return MappingConfigurationContext(self, new_cfg)

    @property
    def mapped_class(self):
        return self.__mapped_cls

    @property
    def data_element_class(self):
        return self.__de_cls

    @property
    def mapping_registry(self):
        return self.__mp_reg

    def _attribute_iterator(self, mapped_class, key):
        """
        Returns an iterator over the attributes in this mapping for the
        given mapped class and attribute key.

        If this is a pruning mapping, attributes that are ignored because
        of a custom configuration or because of the default ignore rules
        are skipped.
        """
        for attr in \
          itervalues_(self.__get_attribute_map(mapped_class, key, 0)):
            if self.is_pruning:
                do_ignore = attr.should_ignore(key)
            else:
                do_ignore = False
            if not do_ignore:
                yield attr

    def __get_attribute_map(self, mapped_class, key, index):
        if mapped_class is None:
            mapped_class = self.__mapped_cls
        if key is None:
            key = MappedAttributeKey(()) # Top level access.
        attr_maps = self.__mapped_attr_cache.get((mapped_class, key))
        if attr_maps is None:
            attr_maps = self.__cache_attributes(mapped_class, key)
        return attr_maps[index]

    def __cache_attributes(self, mapped_class, key):
        attr_map = self.__collect_mapped_attributes(mapped_class, key)
        # For lookup by repr attribute name, we keep another map.
        repr_attr_map = dict([(attr.repr_name, attr)
                              for attr in itervalues_(attr_map)])
        self.__mapped_attr_cache[(mapped_class, key)] = (attr_map,
                                                         repr_attr_map)
        return (attr_map, repr_attr_map)

    def __collect_mapped_attributes(self, mapped_class, key):
        if isinstance(key, MappedAttributeKey):
            names = key.names
        else:
            names = key
        collected_mp_attrs = OrderedDict()
        is_mapped_cls = mapped_class is self.__mapped_cls
        if len(names) == 0 and is_mapped_cls:
            # Bootstrapping: fetch resource attributes and create new
            # mapped attributes.
            rc_attrs = get_resource_class_attributes(self.__mapped_cls)
            for rc_attr in itervalues_(rc_attrs):
                attr_key = names + (rc_attr.resource_attr,)
                attr_mp_opts = \
                    self.__configurations[-1].get_attribute_options(attr_key)
                new_mp_attr = MappedAttribute(rc_attr, options=attr_mp_opts)
                collected_mp_attrs[new_mp_attr.resource_attr] = new_mp_attr
        else:
            # Indirect access - fetch mapped attributes from some other
            # class' mapping and clone.
            if is_mapped_cls:
                mp = self
            elif len(names) == 0 and self.__is_collection_mapping:
                if provides_member_resource(mapped_class):
                    # Mapping a polymorphic member class.
                    mapped_coll_cls = get_collection_class(mapped_class)
                else:
                    # Mapping a derived collection class.
                    mapped_coll_cls = mapped_class
                mp = self.__mp_reg.find_or_create_mapping(mapped_coll_cls)
            else:
                mp = self.__mp_reg.find_or_create_mapping(mapped_class)
            mp_attrs = mp.get_attribute_map()
            for mp_attr in itervalues_(mp_attrs):
                attr_key = names + (mp_attr.name,)
                attr_mp_opts = \
                    dict(((k, v)
                          for (k, v) in
                            iteritems_(self.__configurations[-1]
                                       .get_attribute_options(attr_key))
                          if not v is None))
                clnd_mp_attr = mp_attr.clone(options=attr_mp_opts)
                collected_mp_attrs[mp_attr.resource_attr] = clnd_mp_attr
        return collected_mp_attrs


class MappingConfigurationContext(object):
    def __init__(self, mapping, configuration):
        self.__mapping = mapping
        self.__configuration = configuration

    def __enter__(self):
        self.__mapping.push_configuration(self.__configuration)

    def __exit__(self, ext_type, value, tb):
        self.__mapping.pop_configuration()


class PruningMapping(Mapping):
    """
    Specialized mapping that applies ignore rules when iterating over
    mapped attributes.
    """
    is_pruning = True


class MappingRegistry(object):
    """
    The mapping registry manages resource attribute mappings by resource
    class.
    """
    member_data_element_base_class = None
    collection_data_element_base_class = None
    linked_data_element_base_class = None
    configuration_class = None
    mapping_class = Mapping

    def __init__(self):
        self.__configuration = self.configuration_class() # pylint: disable=E1102
        self.__mappings = {}
        self.__is_initialized = False

    def _initialize(self):
        # Implement this for static initializations.
        raise NotImplementedError('Abstract method.')

    def set_default_config_option(self, name, value):
        """
        Sets the option of the given name to the given value in the
        registry configuration. This setting then serves as the default for
        future mappings created by this registry.
        """
        self.__configuration.set_option(name, value)

    def create_mapping(self, mapped_class, configuration=None):
        """
        Creates a new mapping for the given mapped class and representer
        configuration.

        :param configuration: configuration for the new data element class.
        :type configuration: :class:`RepresenterConfiguration`
        :returns: newly created instance of :class:`Mapping`
        """
        cfg = self.__configuration.copy()
        if not configuration is None:
            cfg.update(configuration)
        provided_ifcs = provided_by(object.__new__(mapped_class))
        if IMemberResource in provided_ifcs:
            base_data_element_class = self.member_data_element_base_class
        elif ICollectionResource in provided_ifcs:
            base_data_element_class = self.collection_data_element_base_class
        elif IResourceLink in provided_ifcs:
            base_data_element_class = self.linked_data_element_base_class
        else:
            raise ValueError('Mapped class for data element class does not '
                             'implement one of the required interfaces.')
        name = "%s%s" % (mapped_class.__name__,
                         base_data_element_class.__name__)
        de_cls = type(name, (base_data_element_class,), {})
        mp = self.mapping_class(self, mapped_class, de_cls, cfg)
        # Set the data element class' mapping.
        # FIXME: This looks like a hack.
        de_cls.mapping = mp
        return mp

    def set_mapping(self, mapping):
        """
        Registers the given mapping, using the mapped class as key.

        :param mapping: mapping
        :type mapping: :class:`Mapping`
        """
        self.__mappings[mapping.mapped_class] = mapping

    def find_mapping(self, mapped_class):
        """
        Returns the mapping registered for the given mapped class or any of
        its base classes. Returns `None` if no mapping can be found.

        :param mapped_class: mapped type
        :type mapped_class: type
        :returns: instance of :class:`Mapping` or `None`
        """
        if not self.__is_initialized:
            self.__is_initialized = True
            self._initialize()
        mapping = None
        for base_cls in mapped_class.__mro__:
            try:
                mapping = self.__mappings[base_cls]
            except KeyError:
                continue
            else:
                break
        return mapping

    def find_or_create_mapping(self, mapped_class):
        """
        First calls :meth:`find_mapping` to check if a mapping for the given
        mapped class or any of its base classes has been created. If not, a
        new one is created with a default configuration, registered
        automatically and returned.
        """
        mapping = self.find_mapping(mapped_class)
        if mapping is None:
            mapping = self.create_mapping(mapped_class)
            self.set_mapping(mapping)
        return mapping

    def get_mappings(self):
        """
        Returns an iterator over all registered mappings.

        :returns: iterator yielding tuples containing a mapped class as the
          first and a :class:`Mapping` instance as the second item.
        """
        return itervalues_(self.__mappings)


class SimpleMappingRegistry(MappingRegistry):
    """
    Default implementation for a mapping registry using default data element
    and configuration classes.
    """
    member_data_element_base_class = SimpleMemberDataElement
    collection_data_element_base_class = SimpleCollectionDataElement
    linked_data_element_base_class = SimpleLinkedDataElement
    configuration_class = RepresenterConfiguration

    def _initialize(self):
        # Create and register the linked data element class.
        configuration = self.configuration_class()
        mapping = self.create_mapping(Link, configuration)
        self.set_mapping(mapping)

