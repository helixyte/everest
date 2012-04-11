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
from everest.resources.utils import get_member_class
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


class MetaResourceAttributeCollector(type):
    """
    Meta class for member resource classes managing declared attributes.

    Extracts relevant information from the resource class descriptors for
    use e.g. in the representers.
    """

    def __init__(mcs, name, bases, class_dict):
        # Skip classes that are direct subclasses of the base mixin class.
        if name != 'ResourceAttributeControllerMixin' \
           and not ResourceAttributeControllerMixin in bases:
            dicts = []
            for cls in mcs.__mro__[::-1]:
                if cls in ResourceAttributeControllerMixin.__mro__:
                    continue
                dicts.append(cls.__dict__)
            attr_map = mcs.__collect_attributes(dicts)
            # Store in class namespace.
            mcs._attributes = attr_map
        type.__init__(mcs, name, bases, class_dict)

    def __collect_attributes(mcs, dicts):
        # Loop over the namespace of the given resource class and its base 
        # classes looking for descriptors inheriting from
        # :class:`everest.resources.descriptors.attribute_base`.
        descr_map = {}
        for base_cls_namespace in dicts:
            for descr_name, descr in base_cls_namespace.iteritems():
                if isinstance(descr, attribute_base):
                    descr_map[descr_name] = descr
        # Order by descriptor ID (=sequence in which they were declared).
        ordered_descr_map = OrderedDict()
        cmp_fnc = lambda item1, item2: cmp(item1[1].id, item2[1].id)
        for item in sorted(descr_map.items(), cmp=cmp_fnc):
            ordered_descr_map[item[0]] = item[1]
        # Builds :class:`everest.resources.attributes.ResourceAttribute`
        # instances from resource descriptor information. Also, sets the
        # `resource_name` attribute in the collected descriptors.
        attr_map = OrderedDict()
        for attr_name, descr in ordered_descr_map.items():
            # It would be awkward to repeat the resource attribute name 
            # in the parameters to the descriptor, so we set it manually
            # here.
            descr.resource_attr = attr_name
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
                                     entity_name=descr.entity_attr,
                                     is_nested=is_nested)
            attr_map[attr_name] = attr
        return attr_map


class ResourceAttributeControllerMixin(object):
    __metaclass__ = MetaResourceAttributeCollector

    # Populated by the meta class.
    _attributes = None

    @classmethod
    def is_terminal(cls, attr):
        """
        Checks if the given attribute of the given resource class is an
        terminal attribute.
        """
        return cls._attributes[attr].kind == ResourceAttributeKinds.TERMINAL

    @classmethod
    def is_member(cls, attr):
        """
        Checks if the given attribute of the given resource class is a
        member resource attribute.
        """
        return cls._attributes[attr].kind == ResourceAttributeKinds.MEMBER

    @classmethod
    def is_collection(cls, attr):
        """
        Checks if the given attribute of the given resource class is an
        collection resource attribute.
        """
        return cls._attributes[attr].kind == ResourceAttributeKinds.COLLECTION

    @classmethod
    def get_attribute_names(cls):
        """
        Returns all attribute names of the given resource class.
        """
        return cls._attributes.keys()

    @classmethod
    def get_attributes(cls):
        """
        Returns a dictionary mapping the attribute names of the given
        resource class to :class:`ResourceAttribute` instances.
        """
        return cls._attributes


def is_terminal_attribute(rc, attr_name):
    mb_cls = get_member_class(rc)
    return mb_cls.is_terminal(attr_name)


def is_member_attribute(rc, attr_name):
    mb_cls = get_member_class(rc)
    return mb_cls.is_atomic(attr_name)


def is_collection_attribute(rc, attr_name):
    mb_cls = get_member_class(rc)
    return mb_cls.is_collection(attr_name)


def get_resource_class_attribute_names(rc):
    mb_cls = get_member_class(rc)
    return mb_cls.get_attribute_names()


def get_resource_class_attributes(rc):
    mb_cls = get_member_class(rc)
    return mb_cls.get_attributes()
