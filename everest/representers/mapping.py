"""
Mapping and mapping registry.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 4, 2012.
"""
from collections import OrderedDict
from everest.constants import MAPPING_DIRECTIONS
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.representers.attributes import AttributeKey
from everest.representers.attributes import MappedAttribute
from everest.representers.attributes import MappedAttributeKey
from everest.representers.config import RepresenterConfiguration
from everest.representers.dataelements import SimpleCollectionDataElement
from everest.representers.dataelements import SimpleLinkedDataElement
from everest.representers.dataelements import SimpleMemberDataElement
from everest.representers.traversal import DataElementBuilderResourceTreeVisitor
from everest.representers.traversal import ResourceTreeTraverser
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResourceLink
from everest.resources.link import Link
from everest.resources.utils import get_collection_class
from everest.resources.utils import provides_collection_resource
from everest.resources.utils import provides_member_resource
from pyramid.compat import iteritems_
from pyramid.compat import itervalues_
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from everest.resources.staging import create_staging_collection

__docformat__ = 'reStructuredText en'
__all__ = ['Mapping',
           'MappingRegistry',
           'SimpleMappingRegistry',
           ]


class Mapping(object):
    """
    Performs configurable resource <-> data element tree <-> representation
    attribute mappings.

    :property mapped_class: The resource class mapped by this mapping.
    :property data_element_class: The data element class for this mapping
    """
    #: Flag indicating if this mapping should prune the attribute tree
    #: according to the IGNORE settings.
    is_pruning = False

    def __init__(self, mapping_registry, mapped_class, data_element_class,
                 configuration):
        """
        :param configuration: mapping configuration object.
        """
        self.__mp_reg = mapping_registry
        self.__mapped_cls = mapped_class
        self.__is_collection_mapping = \
                                provides_collection_resource(mapped_class)
        self.__de_cls = data_element_class
        self.__configuration = configuration
        #
        self.__mapped_attr_cache = {}

    def clone(self, options=None, attribute_options=None):
        """
        Returns a clone of this mapping that is configured with the given
        option and attribute option dictionaries.
        """
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
        Returns an ordered map of the mapped attributes for the given mapped
        class and attribute key.

        :param key: tuple of attribute names specifying a path to a nested
          attribute in a resource tree. If this is not given, the attributes
          in this mapping will be returned.
        """
        if mapped_class is None:
            mapped_class = self.__mapped_cls
        return OrderedDict([(attr.resource_attr, attr)
                            for attr in self._attribute_iterator(mapped_class,
                                                                 key)])

    def get_attribute(self, attribute_name, mapped_class=None, key=None):
        """
        Returns the specified attribute from the map of all mapped attributes
        for the given mapped class and attribute key.
        """
        return self.__get_attribute_map(mapped_class, key)[attribute_name]

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

    def create_linked_data_element(self, url, kind,
                                   relation=None, title=None):
        """
        Returns a new linked data element for the given url and kind.

        :param str url: URL to assign to the linked data element.
        :param str kind: kind of the resource that is linked. One of the
          constantes defined by :class:`everest.constants.RESOURCE_KINDS`.
        :returns: object implementing :class:`ILinkedDataElement`.
        """
        mp = self.__mp_reg.find_or_create_mapping(Link)
        return mp.data_element_class.create(url, kind,
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
        if resource is None:
            resource = \
                create_staging_collection(data_element.mapping.mapped_class)
            agg = resource.get_aggregate()
            agg.add(data_element)
        else:
            resource.update(data_element)
        return resource

#    def map_to_resource(self, data_element, resource=None):
#        ifcs = provided_by(data_element)
#        if IMemberDataElement in ifcs:
#            is_sequence = False
#        elif ICollectionDataElement in ifcs:
#            is_sequence = True
#        else:
#            raise ValueError('"data_element" argument must provide '
#                             'IMemberResource or ICollectionResource.')
#        if resource is None:
##            trv = DataElementTreeTraverser(data_element, self,
##                                           direction=
##                                                MAPPING_DIRECTIONS.READ)
##            visitor = ResourceBuilderDataElementTreeVisitor(resource=resource)
##            trv.run(visitor)
##            result = visitor.resource
#            rel_op = RELATION_OPERATIONS.ADD
#            acc = None
#            coll = create_staging_collection(data_element.mapping.mapped_class)
#        else:
#            rel_op = RELATION_OPERATIONS.UPDATE
#            ifcs = provided_by(resource)
#            if IMemberResource in ifcs:
#                coll = resource.__parent__
#            elif ICollectionResource in ifcs:
#                coll = resource
#            else:
#                raise ValueError('"resource" argument must provide '
#                                 'IMemberResource or ICollectionResource.')
#            acc = get_root_collection(resource)
#        trv = SourceTargetDataTreeTraverser.make_traverser(
#                    data_element,
#                    rel_op,
#                    accessor=acc,
#                    target=resource,
#                    source_proxy_options=dict(mapping=self))
#        sess = coll.get_aggregate()
#        visitor = AruVisitor(data_element.mapping.mapped_class,
#                             root_is_sequence=is_sequence,
#                             add_callback=lambda ent_cls, ent:
#                                sess.get_root_aggregate(ent_cls).add(ent),
#                             remove_callback=lambda ent_cls, ent:
#                                sess.get_root_aggregate(ent_cls).remove(ent))
#        trv.run(visitor)
#        if resource is None:
#            if is_sequence:
#                resource = coll
#            else:
#                resource = data_element.mapping.mapped_class.create_from_entity(visitor.root)
#        return resource

    def map_to_data_element(self, resource):
        trv = ResourceTreeTraverser(resource, self.as_pruning(),
                                    direction=MAPPING_DIRECTIONS.WRITE)
        visitor = DataElementBuilderResourceTreeVisitor(self)
        trv.run(visitor)
        return visitor.data_element

    def as_pruning(self):
        return PruningMapping(self.__mp_reg, self.__mapped_cls, self.__de_cls,
                              self.__configuration)

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

        If this is a pruning mapping, the default behavior for ignoring
        nested attributes are applied as well as the configured ignore
        options.
        """
        for attr in itervalues_(self.__get_attribute_map(mapped_class, key)):
            if self.is_pruning:
                do_ignore = attr.should_ignore(key)
            else:
                do_ignore = False
            if not do_ignore:
                yield attr

    def __get_attribute_map(self, mapped_class, key):
        if mapped_class is None:
            mapped_class = self.__mapped_cls
        if key is None:
            key = MappedAttributeKey(()) # Top level access.
        attr_map = self.__mapped_attr_cache.get((mapped_class, key))
        if attr_map is None:
            attr_map = self.__collect_mapped_attributes(mapped_class, key)
            self.__mapped_attr_cache[(mapped_class, key)] = attr_map
        return attr_map

    def __collect_mapped_attributes(self, mapped_class, key):
        if isinstance(key, AttributeKey):
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
                        self.__configuration.get_attribute_options(attr_key)
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
                            iteritems_(self.__configuration
                                       .get_attribute_options(attr_key))
                          if not v is None))
                clnd_mp_attr = mp_attr.clone(options=attr_mp_opts)
                collected_mp_attrs[mp_attr.name] = clnd_mp_attr
        return collected_mp_attrs


class PruningMapping(Mapping):
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

