"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Resource attribute handling classes.

Created on June 8, 2011.
"""

from everest.resources.descriptors import attribute_base
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.utils import OrderedDict

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceAttributeKinds',
           'get_resource_class_attribute_names',
           'get_resourcd_class_attributes',
           'is_atomic_attribute',
           'is_collection_attribute',
           'is_member_attribute',
           ]


class ResourceAttributeKinds(object):
    """
    Static container for resource attribute kind constants.

    We have three kinds of resource attribute:
        MEMBER :
            a member resource attribute
        COLLECTION :
            a collection resource attribute
        TERMINAL :
            an attribute that is not a resource
    """
    MEMBER = 'MEMBER'
    COLLECTION = 'COLLECTION'
    TERMINAL = 'TERMINAL'


class ResourceAttribute(object):
    """
    Value object holding information about a resource attribute.
    """
    def __init__(self, name, kind, value_type,
                 entity_name=None, is_nested=None):
        #: The name of the attribute in the resource.
        self.name = name
        #: The kind of the attribute.
        self.kind = kind
        #: The type or interface of the attribute in the underlying entity.
        self.value_type = value_type
        #: The name of the attribute in the underlying entity.
        self.entity_name = entity_name
        #: For member and collection resource attributes, this indicates if
        #: the referenced resource is subordinate to this one. This is
        #: always `None` for terminal resource attributes.
        self.is_nested = is_nested


class _ResourceClassAttributeInspector(object):
    """
    Helper class for extracting information about resource attributes from
    classes using .

    Extracts relevant information from the resource class descriptors for
    use e.g. in the representers.
    """
    __cache = {}

    @staticmethod
    def is_atomic(rc_cls, attr):
        """
        Checks if the given attribute of the given resource class is an
        atomic attribute.
        """
        descr_map = _ResourceClassAttributeInspector.__get_map(rc_cls)
        return type(descr_map[attr]) is terminal_attribute

    @staticmethod
    def is_member(rc_cls, attr):
        """
        Checks if the given attribute of the given resource class is a
        member resource attribute.
        """
        descr_map = _ResourceClassAttributeInspector.__get_map(rc_cls)
        return type(descr_map[attr]) is member_attribute

    @staticmethod
    def is_collection(rc_cls, attr):
        """
        Checks if the given attribute of the given resource class is an
        collection resource attribute.
        """
        descr_map = _ResourceClassAttributeInspector.__get_map(rc_cls)
        return type(descr_map[attr]) is collection_attribute

    @staticmethod
    def get_names(rc_cls):
        """
        Returns all attribute names of the given resource class.
        """
        return _ResourceClassAttributeInspector.__get_map(rc_cls).keys()

    @staticmethod
    def get_attributes(rc_cls):
        """
        Returns a dictionary mapping the attribute names of the given
        resource class to a triple containing the resource attribute kind (cf.
        :class:`ResourceAttributeKinds`), the name of the entity attribute
        and the type of the entity attribute.
        """
        descr_map = _ResourceClassAttributeInspector.__get_map(rc_cls)
        attrs = OrderedDict()
        for attr_name, descr in descr_map.items():
            if type(descr) is terminal_attribute:
                attr_kind = ResourceAttributeKinds.TERMINAL
                is_nested = None
            else:
                is_nested = descr.is_nested
                if type(descr) is member_attribute:
                    attr_kind = ResourceAttributeKinds.MEMBER
                elif type(descr) is collection_attribute:
                    attr_kind = ResourceAttributeKinds.COLLECTION
                else:
                    raise ValueError('Unknown resource attribute type.')
            attr = ResourceAttribute(attr_name, attr_kind,
                                     descr.attr_type,
                                     entity_name=descr.attr_name,
                                     is_nested=is_nested)
            attrs[attr_name] = attr
        return attrs

    @staticmethod
    def __get_map(rc_cls):
        # Loops over the class namespace of this class and its base classes
        # looking for descriptors inheriting from
        # :class:`everest.resources.descriptors.attribute_base`.
        descr_map = _ResourceClassAttributeInspector.__cache.get(rc_cls)
        if descr_map is None:
            descr_map = _ResourceClassAttributeInspector.__cache[rc_cls] = {}
            for base_cls in rc_cls.__mro__[::-1]:
                for descr_name, descr in base_cls.__dict__.iteritems():
                    if isinstance(descr, attribute_base):
                        descr_map[descr_name] = descr
        # We order by descriptor ID (=sequence in which they were declared).
        ordered_map = OrderedDict()
        cmp_fnc = lambda item1, item2: cmp(item1[1].id, item2[1].id)
        for item in sorted(descr_map.items(), cmp=cmp_fnc):
            ordered_map[item[0]] = item[1]
        return ordered_map

is_atomic_attribute = _ResourceClassAttributeInspector.is_atomic
is_member_attribute = _ResourceClassAttributeInspector.is_member
is_collection_attribute = _ResourceClassAttributeInspector.is_collection
get_resource_class_attribute_names = _ResourceClassAttributeInspector.get_names
get_resource_class_attributes = _ResourceClassAttributeInspector.get_attributes


class MappedAttribute(object):
    """
    Represents an attribute mapped from a class into a representation.

    This is a simple value object.
    """
    def __init__(self, name, kind, value_type, entity_name, **options):
        """
        :param str name: The attribute name.
        :param str kind: The attribute kind. One of the constants
          defined in :class:`ResourceAttributeKinds`.
        """
        self.name = name
        self.kind = kind
        self.value_type = value_type
        self.entity_name = entity_name
        # Make sure we have a valid representation name.
        representation_name = options.pop('repr_name', None)
        if representation_name is None:
            representation_name = name
        self.representation_name = representation_name
        # All other options are made available as attributes.
        for option_name, option_value in options.iteritems():
            setattr(self, option_name, option_value)

    def __str__(self):
        return '%s(%s -> %s, type %s)' % \
               (self.__class__.__name__, self.name,
                self.representation_name, self.kind)


class _AttributeMapper(object):
    """
    Performs attribute mapping between a mapped class and its representation.
    """

    def __init__(self, configuration):
        """
        :param configuration: representer configuration class
        """
        self.__mapped_attr_cache = {}
        self.__config = configuration

    def get_config_option(self, name):
        return self.__config.get_option(name)

    def set_config_option(self, name, value):
        self.__config.set_option(name, value)

    def get_mapped_attributes(self, mapped_class, info=None):
        cache = self.__mapped_attr_cache
        self._collect_mapped_attributes(cache, mapped_class, info)
        return cache[mapped_class]

    def _collect_mapped_attributes(self, cache, mapped_class, info):
        if info is None:
            info = {}
        else:
            # Discard the cache if we have dynamic mapping info.
            cache.pop(mapped_class, None)
        mapped_attrs = OrderedDict()
        attrs = get_resource_class_attributes(mapped_class)
        for attr in attrs.values():
            map_options = self.__config.get_mapping(attr.name)
#            if attr.kind == ResourceAttributeKinds.COLLECTION \
#               and map_options['ignore'] is None:
#                # By default, ignore if attribute references root collection.
#                map_options['ignore'] = not attr.is_nested
            runtime_map_options = info.get(attr.name, {})
            map_options.update(runtime_map_options)
            mapped_attr = MappedAttribute(attr.name, # ** pylint:disable=W0142
                                          attr.kind,
                                          attr.value_type,
                                          attr.entity_name,
                                          **map_options)
            mapped_attrs[attr.name] = mapped_attr
        cache[mapped_class] = mapped_attrs


class MemberAttributeMapper(_AttributeMapper):
    pass


class CollectionAttributeMapper(_AttributeMapper):
    pass


class CompositeValueAttributeMapper(_AttributeMapper):
    pass


class LinkAttributeMapper(_AttributeMapper):
    pass
