"""
Resource attribute handling classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 2, 2011.
"""
from collections import OrderedDict
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.resources.descriptors import attribute_base
from everest.resources.descriptors import collection_attribute \
    as collection_resource_attribute
from everest.resources.descriptors import member_attribute \
    as member_resource_attribute
from everest.resources.descriptors import terminal_attribute \
    as terminal_resource_attribute
from everest.resources.interfaces import IMemberResource
from everest.resources.utils import get_member_class
from functools import wraps
from pyramid.compat import iteritems_
from pyramid.compat import itervalues_
from zope.interface import implementedBy as implemented_by # pylint: disable=E0611,F0401
import functools

__docformat__ = 'reStructuredText en'
__all__ = ['MetaResourceAttributeCollector',
           'ResourceAttributeControllerMixin',
           'get_resource_class_attribute',
           'get_resource_class_attribute_iterator',
           'get_resource_class_attribute_names',
           'get_resource_class_attributes',
           'get_resource_class_collection_attribute_iterator',
           'get_resource_class_member_attribute_iterator',
           'get_resource_class_relationship_attribute_iterator',
           'get_resource_class_terminal_attribute_iterator',
           'is_resource_class_collection_attribute',
           'is_resource_class_member_attribute',
           'is_resource_class_resource_attribute',
           'is_resource_class_terminal_attribute',
           'resource_attributes_injector',
           ]


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
            mcs.__everest_attributes__ = attr_map
        type.__init__(mcs, name, bases, class_dict)

    def __collect_attributes(mcs, dicts):
        # Loop over the namespace of the given resource class and its base
        # classes looking for descriptors inheriting from
        # :class:`everest.resources.descriptors.attribute_base`.
        descr_map = {}
        for base_cls_namespace in dicts:
            for descr_name, descr in iteritems_(base_cls_namespace):
                if isinstance(descr, attribute_base):
                    descr_map[descr_name] = descr
        # Order by descriptor index (=sequence in which they were declared).
        ordered_descr_map = OrderedDict()
        cmp_fnc = lambda item1, item2: (item1[1].index > item2[1].index) - \
                                       (item1[1].index < item2[1].index)
        for item in sorted(descr_map.items(),
                           key=functools.cmp_to_key(cmp_fnc)):
            name, descr = item
            if not type(descr) in (terminal_resource_attribute,
                                   member_resource_attribute,
                                   collection_resource_attribute):
                raise TypeError('Unknown resource attribute type "%s".'
                                % type(descr))
            ordered_descr_map[name] = descr
            # It would be awkward to repeat the resource attribute name
            # in the parameters to the descriptor, so we set it manually
            # here.
            descr.resource_attr = name
        return ordered_descr_map


# PY3 compatible way of using the metaclass (__metaclass__ does not work).
ResourceAttributeControllerMixin = MetaResourceAttributeCollector(
                                        'ResourceAttributeControllerMixin',
                                        (object,), {})
# This is populated by the meta class.
ResourceAttributeControllerMixin.__everest_attributes__ = None


def arg_to_member_class(func):
    @wraps(func)
    def wrap(rc, *args):
        if isinstance(rc, type) and IMemberResource in implemented_by(rc):
            mb_cls = rc
        else:
            mb_cls = get_member_class(rc)
        return func(mb_cls, *args)
    return wrap


def is_resource_class_terminal_attribute(rc, attr_name):
    """
    Checks if the given attribute name is a terminal attribute of the given
    registered resource.
    """
    attr = get_resource_class_attribute(rc, attr_name)
    return attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL


def is_resource_class_member_attribute(rc, attr_name):
    """
    Checks if the given attribute name is a member attribute of the given
    registered resource.
    """
    attr = get_resource_class_attribute(rc, attr_name)
    return attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER


def is_resource_class_collection_attribute(rc, attr_name):
    """
    Checks if the given attribute name is a collection attribute of the given
    registered resource.
    """
    attr = get_resource_class_attribute(rc, attr_name)
    return attr.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION


def is_resource_class_resource_attribute(rc, attr_name):
    """
    Checks if the given attribute name is a resource attribute (i.e., either
    a member or a collection attribute) of the given registered resource.
    """
    attr = get_resource_class_attribute(rc, attr_name)
    return attr != RESOURCE_ATTRIBUTE_KINDS.TERMINAL


@arg_to_member_class
def get_resource_class_attribute(rc, name):
    """
    Returns the specified resource class attribute from the map of all
    collected attributes for the given registered resource or `None`, if the
    attribute could not be found.
    """
    return rc.__everest_attributes__.get(name)


@arg_to_member_class
def get_resource_class_attributes(rc):
    """
    Returns a dictionary mapping the attribute names of the given
    registered resource to :class:`ResourceAttribute` instances.
    """
    return rc.__everest_attributes__


@arg_to_member_class
def get_resource_class_attribute_names(rc):
    """
    Returns all attribute names of the given registered resource.
    """
    return rc.__everest_attributes__.keys()


@arg_to_member_class
def get_resource_class_attribute_iterator(rc):
    """
    Returns an iterator over all attributes in the given registered resource.
    """
    for attr in rc.__everest_attributes__.values():
        yield attr

@arg_to_member_class
def get_resource_class_terminal_attribute_iterator(rc):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(rc.__everest_attributes__):
        if attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
            yield attr


@arg_to_member_class
def get_resource_class_relationship_attribute_iterator(rc):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(rc.__everest_attributes__):
        if attr.kind != RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
            yield attr


@arg_to_member_class
def get_resource_class_member_attribute_iterator(rc):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(rc.__everest_attributes__):
        if attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
            yield attr


@arg_to_member_class
def get_resource_class_collection_attribute_iterator(rc):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(rc.__everest_attributes__):
        if attr.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION:
            yield attr


class resource_attributes_injector(object):
    """
    Attribute injector.

    This is used to inject the resource attribute descriptor map (using the
    entity attribute name as key) as "__everest_atttributes__" attribute into
    the namespace of the corresponding entity class.
    """
    def __get__(self, dummy, entity_class):
        mb_cls = get_member_class(entity_class)
        attr_map = OrderedDict()
        for rc_attr in itervalues_(mb_cls.__everest_attributes__):
            attr_map[rc_attr.entity_attr] = rc_attr
        # This replaces the injector.
        entity_class.__everest_attributes__ = attr_map
        return attr_map
