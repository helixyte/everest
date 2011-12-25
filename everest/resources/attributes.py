"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Resource attribute handling classes.

Created on Dec 2, 2011.
"""

from everest.resources.descriptors import attribute_base
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.utils import OrderedDict

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceAttributeKinds',
           'get_resource_class_attribute_names',
           'get_resource_class_attributes',
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

    def __hash__(self):
        return self.entity_name


class _ResourceClassAttributeInspector(object):
    """
    Helper class for extracting information about resource attributes from
    classes using .

    Extracts relevant information from the resource class descriptors for
    use e.g. in the representers.
    """

    __descr_cache = {}
    __attr_cache = {}

    @staticmethod
    def is_atomic(rc_cls, attr):
        """
        Checks if the given attribute of the given resource class is an
        atomic attribute.
        """
        descr_map = _ResourceClassAttributeInspector.__get_descrs(rc_cls)
        return type(descr_map[attr]) is terminal_attribute

    @staticmethod
    def is_member(rc_cls, attr):
        """
        Checks if the given attribute of the given resource class is a
        member resource attribute.
        """
        descr_map = _ResourceClassAttributeInspector.__get_descrs(rc_cls)
        return type(descr_map[attr]) is member_attribute

    @staticmethod
    def is_collection(rc_cls, attr):
        """
        Checks if the given attribute of the given resource class is an
        collection resource attribute.
        """
        descr_map = _ResourceClassAttributeInspector.__get_descrs(rc_cls)
        return type(descr_map[attr]) is collection_attribute

    @staticmethod
    def get_names(rc_cls):
        """
        Returns all attribute names of the given resource class.
        """
        return _ResourceClassAttributeInspector.__get_descrs(rc_cls).keys()

    @staticmethod
    def get_attributes(rc_cls):
        """
        Returns a dictionary mapping the attribute names of the given
        resource class to a triple containing the resource attribute kind (cf.
        :class:`ResourceAttributeKinds`), the name of the entity attribute
        and the type of the entity attribute.
        """
        return _ResourceClassAttributeInspector.__get_attrs(rc_cls)

    @staticmethod
    def __get_attrs(rc_cls):
        # Builds :class:`everest.resources.attributes.ResourceAttribute`
        # instances from resource descriptor information.
        attr_map = _ResourceClassAttributeInspector.__attr_cache.get(rc_cls)
        if attr_map is None:
            descr_map = _ResourceClassAttributeInspector.__get_descrs(rc_cls)
            attr_map = \
                _ResourceClassAttributeInspector.__attr_cache[rc_cls] = \
                OrderedDict()
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
                attr_map[attr_name] = attr
        return attr_map

    @staticmethod
    def __get_descrs(rc_cls):
        # Loops over the namespace of the given resource class and its base 
        # classes looking for descriptors inheriting from
        # :class:`everest.resources.descriptors.attribute_base`.
        descr_map = _ResourceClassAttributeInspector.__descr_cache.get(rc_cls)
        if descr_map is None:
            descr_map = \
                _ResourceClassAttributeInspector.__descr_cache[rc_cls] = {}
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

