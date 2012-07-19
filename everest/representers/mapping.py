"""
Mapping and mapping registry.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 4, 2012.
"""
from collections import OrderedDict
from everest.representers.attributes import MappedAttribute
from everest.representers.config import RepresenterConfiguration
from everest.representers.dataelements import SimpleCollectionDataElement
from everest.representers.dataelements import SimpleLinkedDataElement
from everest.representers.dataelements import SimpleMemberDataElement
from everest.representers.traversal import AttributeKey
from everest.representers.traversal import DataElementBuilderResourceTreeVisitor
from everest.representers.traversal import MappingDataElementTreeTraverser
from everest.representers.traversal import ResourceBuilderDataElementTreeVisitor
from everest.representers.traversal import ResourceTreeTraverser
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResourceLink
from everest.resources.link import Link
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['Mapping',
           'MappingRegistry',
           'SimpleMappingRegistry',
           ]


class Mapping(object):
    """
    Performs configurable resource <-> data element tree <-> representation
    mappings.
    
    :property mapped_class: The resource class mapped by this mapping.
    :property data_element_class: The data element class for this mapping
    """

    def __init__(self, mapping_registry, mapped_class, data_element_class,
                 configuration):
        """
        :param configuration: mapping configuration object.
        """
        self.__mp_reg = mapping_registry
        self.__mapped_cls = mapped_class
        self.__de_cls = data_element_class
        self.__configuration = configuration
        #
        self.__mapped_attr_cache = {}

    def clone(self, options=None, attribute_options=None):
        copied_cfg = self.__configuration.copy()
        upd_cfg = type(copied_cfg)(options=options,
                                   attribute_options=attribute_options)
        copied_cfg.update(upd_cfg)
        return self.__class__(self.__mp_reg, self.__mapped_cls,
                              self.__de_cls, copied_cfg)

    @property
    def configuration(self):
        """
        Returns this mapping's configuration object.
        """
        # We clear the cache every time the configuration is accessed since
        # we can not guarantee that it stays unchanged.
        self.__mapped_attr_cache.clear()
        return self.__configuration

    def get_attribute_map(self, mapped_class=None, key=None):
        """
        Returns a map of all attributes of the given mapped class.
        
        :param key: tuple of attribute names specifying a path to a nested
          attribute in a resource tree. If this is not given, all attributes
          in this mapping will be returned.
        """
        if mapped_class is None:
            mapped_class = self.__mapped_cls
        if key is None:
            key = AttributeKey(()) # Top level access.
        # FIXME: Investigate caching of mapped attributes.
        attrs = None # self.__mapped_attr_cache.get((mapped_class, key))
        if attrs is None:
            attrs = self.__collect_mapped_attributes(mapped_class, key)
#            self.__mapped_attr_cache[(mapped_class, key)] = attrs
        return attrs

    def attribute_iterator(self, mapped_class=None, key=None):
        attr_map = self.get_attribute_map(mapped_class=mapped_class, key=key)
        for attr in attr_map.itervalues():
            yield attr

    def terminal_attribute_iterator(self, mapped_class=None, key=None):
        for attr in self.attribute_iterator(mapped_class, key=key):
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                yield attr

    def nonterminal_attribute_iterator(self, mapped_class=None, key=None):
        for attr in self.attribute_iterator(mapped_class=mapped_class,
                                            key=key):
            if attr.kind != ResourceAttributeKinds.TERMINAL:
                yield attr

    def create_data_element(self):
        return self.__de_cls.create()

    def create_data_element_from_resource(self, resource):
        mp = self.__mp_reg.find_or_create_mapping(type(resource))
        return mp.data_element_class.create_from_resource(resource)

    def create_linked_data_element_from_resource(self, resource):
        mp = self.__mp_reg.find_or_create_mapping(Link)
        return mp.data_element_class.create_from_resource(resource)

    def map_to_resource(self, data_element, resolve_urls=True):
        trv = MappingDataElementTreeTraverser(data_element, mapping=self)
        visitor = ResourceBuilderDataElementTreeVisitor(resolve_urls)
        trv.run(visitor)
        return visitor.resource

    def map_to_data_element(self, resource):
        trv = ResourceTreeTraverser(resource, self)
        visitor = DataElementBuilderResourceTreeVisitor(self)
        trv.run(visitor)
        return visitor.data_element

    @property
    def mapped_class(self):
        return self.__mapped_cls

    @property
    def data_element_class(self):
        return self.__de_cls

    @property
    def mapping_registry(self):
        return self.__mp_reg

    def __collect_mapped_attributes(self, mapped_class, key):
        collected_mp_attrs = OrderedDict()
        if len(key) == 0:
            # Top level access - fetch resource attributes and create new
            # mapped attributes.
            rc_attrs = get_resource_class_attributes(mapped_class)
            for rc_attr in rc_attrs.itervalues():
                attr_key = key + (rc_attr.name,)
                attr_mp_opts = \
                        self.__configuration.get_attribute_options(attr_key)
                new_mp_attr = MappedAttribute(rc_attr, options=attr_mp_opts)
                collected_mp_attrs[rc_attr.name] = new_mp_attr
        else:
            # Nested access - fetch mapped attributes from mapping and
            # clone.
            if mapped_class is self.__mapped_cls:
                mp = self
            else:
                mp = self.__mp_reg.find_or_create_mapping(mapped_class)
            mp_attrs = mp.get_attribute_map()
            for mp_attr in mp_attrs.itervalues():
                attr_key = key + (mp_attr.name,)
                attr_mp_opts = \
                    dict(((k, v)
                          for (k, v) in
                            self.__configuration \
                                    .get_attribute_options(attr_key).iteritems()
                          if not v is None))
                clnd_mp_attr = mp_attr.clone(options=attr_mp_opts)
                collected_mp_attrs[mp_attr.name] = clnd_mp_attr
        return collected_mp_attrs


class MappingRegistry(object):

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
        return self.__mappings.itervalues()


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

