"""
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
from everest.representers.traversal import DataElementBuilderResourceTreeVisitor
from everest.representers.traversal import DataElementTreeTraverser
from everest.representers.traversal import ResourceBuilderDataElementTreeVisitor
from everest.representers.traversal import ResourceTreeTraverser
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResourceLink
from everest.resources.link import Link
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['Mapping',
           'MappingRegistry',
           'SimpleMappingRegistry',
           ]


class Mapping(object):
    """
    Performs configurable resource <-> data element tree mappings.
    
    :property mapped_class: The resource class mapped by this mapping.
    :property data_element_class: The data element class for this mapping
    """

    def __init__(self, mapping_registry, mapped_class, data_element_class,
                 options, mapping_options):
        """
        :param options: configuration options dictionary.
        :param mapping_options: mapping options dictionary (keys are attribute
          names, values are dictionaries holding mapping option name : value 
          pairs.
        """
        self.__mp_reg = mapping_registry
        self.__mapped_cls = mapped_class
        self.__de_cls = data_element_class
        # {generic config option name : option value}
        self.__options = options
        # {attr key : { attr name : {{option name : option value}}}
        self.__mapping_options = mapping_options
        #
        self.__mapped_attr_cache = {}

    def clone(self, options=None, mapping_options=None):
        opts = self.__options.copy()
        if not options is None:
            opts.update(options)
        mp_opts = self.__mapping_options.copy()
        if not mapping_options is None:
            for attr, opts in mapping_options.iteritems():
                mp_opts[attr].update(opts)
        return self.__class__(self.__mp_reg, self.__mapped_cls, self.__de_cls,
                              opts, mp_opts)

    def get_config_option(self, name):
        """
        Returns the value for the specified generic configuration option
        from the underlying configuration object or `None`, if that option 
        was not set.
        """
        return self.__options.get(name)

    def get_attribute_map(self, key=None):
        """
        Returns a map of all attributes or of the nested attributes of an
        attribute in this mapping.
        
        :param key: tuple of attribute names specifying a path to a nested
          attribute in a resource tree. If this is not given, all attributes
          in this mapping will be returned.
        """
        if key is None:
            key = () # Top level access.
        attrs = self.__mapped_attr_cache.get(key)
        if attrs is None:
            attrs = self.__collect_mapped_attributes(key)
            self.__mapped_attr_cache[key] = attrs
        return attrs

    def attribute_iterator(self, key=None):
        attr_map = self.get_attribute_map(key=key)
        for attr in attr_map.itervalues():
            yield attr

    def terminal_attribute_iterator(self, key=None):
        for attr in self.attribute_iterator(key=key):
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                yield attr

    def nonterminal_attribute_iterator(self, key=None):
        for attr in self.attribute_iterator(key=key):
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
        trv = DataElementTreeTraverser(self, data_element)
        visitor = ResourceBuilderDataElementTreeVisitor(resolve_urls)
        trv.run_post_order(visitor)
        return visitor.resource

    def map_to_data_element(self, resource):
        trv = ResourceTreeTraverser(self, resource)
        visitor = DataElementBuilderResourceTreeVisitor(self)
        trv.run_post_order(visitor)
        return visitor.data_element

    @property
    def mapped_class(self):
        return self.__mapped_cls

    @property
    def data_element_class(self):
        return self.__de_cls

    def __collect_mapped_attributes(self, key):
        new_mp_attrs = OrderedDict()
        if key == ():
            # Top level access - fetch resource attributes.
            attrs = get_resource_class_attributes(self.__mapped_cls)
        else:
            # Nested access - fetch mapped attributes from other mapping.
            child_attr_cls = self.__resolve(self.__mapped_cls, key)
            mp = self.__mp_reg.find_or_create_mapping(child_attr_cls)
            attrs = mp.get_attribute_map()
        for attr in attrs.values():
            mp_opts = self.__mapping_options[key + (attr.name,)]
            if key == ():
                # Top level access - create new mapped attribute.
                new_mp_attr = MappedAttribute(attr, options=mp_opts)
            else:
                # Nested access - clone mapped attribute with new options.
                new_mp_attr = attr.clone(options=mp_opts)
            new_mp_attrs[attr.name] = new_mp_attr
        return new_mp_attrs

    def __resolve(self, mapped_cls, attr_key):
        if len(attr_key) > 1:
            child_attr_name = attr_key[0]
            tail = attr_key[1:]
            child_attr = \
                get_resource_class_attributes(mapped_cls)[child_attr_name]
            child_mapped_cls = self.__get_type_from_attr(child_attr)
            if child_mapped_cls is None:
                raise ValueError('Can not resolve attribute for terminal '
                                 'attribute.')
            attr_cls = self.__resolve(child_mapped_cls, tail)
        else:
            child_attr = get_resource_class_attributes(mapped_cls)[attr_key[0]]
            attr_cls = self.__get_type_from_attr(child_attr)
        return attr_cls

    def __get_type_from_attr(self, attr):
        if attr.kind == ResourceAttributeKinds.MEMBER:
            attr_type = get_member_class(attr.value_type)
        elif attr.kind == ResourceAttributeKinds.COLLECTION:
            attr_type = get_collection_class(attr.value_type)
        else:
            # For terminals, we do not descend any further.
            attr_type = None
        return attr_type


class MappingRegistry(object):

    member_data_element_base_class = None
    collection_data_element_base_class = None
    linked_data_element_base_class = None
    configuration_class = None
    mapping_class = Mapping

    def __init__(self):
        self.configuration_class = self.__class__.configuration_class.clone()
        self.__mappings = {}
        self.__is_initialized = False

    def _initialize(self):
        # Implement this for static initializations.
        raise NotImplementedError('Abstract method.')

    def create_mapping(self, mapped_class, configuration=None):
        """
        Creates a new mapping for the given mapped class and representer 
        configuration.

        :param configuration: configuration for the new data element class.
        :type configuration: :class:`RepresenterConfiguration`
        :returns: newly created instance of :class:`Mapping`
        """
        if configuration is None:
            configuration = self.configuration_class() # pylint: disable=E1102
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
        mp = self.mapping_class(self, mapped_class, de_cls,
                                configuration.get_options(),
                                configuration.get_mapping_options())
        # Set the mapping attribute for the new data element class.
        de_cls.mapping = mp
        return mp

    def set_mapping(self, mapping):
        """
        Registers the given mapping.

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
        First calls :method:`find_mapping` to check if a mapping for the given
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
        Returns an iterator over all registered mapped class : mapping pairs.

        :returns: iterator yielding tuples containing a mapped class as the 
          first and a :class:`Mapping` instance as the second item.
        """
        return self.__mappings.iteritems()


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

