"""
Entity attributes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 2, 2011.
"""
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.entities.interfaces import IEntity
from everest.entities.utils import get_entity_class
from functools import wraps
from pyramid.compat import itervalues_
from zope.interface import implementedBy as implemented_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['get_domain_class_attribute_iterator',
           'get_domain_class_attribute',
           'get_domain_class_attribute_iterator',
           'get_domain_class_attribute_names',
           'get_domain_class_attributes',
           'get_domain_class_relationship_attribute_iterator',
           'get_domain_class_member_attribute_iterator',
           'get_domain_class_terminal_attribute_iterator',
           'is_domain_class_collection_attribute',
           'is_domain_class_domain_attribute',
           'is_domain_class_member_attribute',
           'is_domain_class_terminal_attribute',
           ]


def _arg_to_entity_class(func):
    @wraps(func)
    def wrap(ent, *args):
        if isinstance(ent, type) and IEntity in implemented_by(ent):
            ent_cls = ent
        else:
            ent_cls = get_entity_class(ent)
        return func(ent_cls, *args)
    return wrap


def is_domain_class_terminal_attribute(ent, attr_name):
    """
    Checks if the given attribute name is a terminal attribute of the given
    registered resource.
    """
    attr = get_domain_class_attribute(ent, attr_name)
    return attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL


def is_domain_class_member_attribute(ent, attr_name):
    """
    Checks if the given attribute name is a entity attribute of the given
    registered resource.
    """
    attr = get_domain_class_attribute(ent, attr_name)
    return attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER


def is_domain_class_collection_attribute(ent, attr_name):
    """
    Checks if the given attribute name is a aggregate attribute of the given
    registered resource.
    """
    attr = get_domain_class_attribute(ent, attr_name)
    return attr.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION


def is_domain_class_domain_attribute(ent, attr_name):
    """
    Checks if the given attribute name is a resource attribute (i.e., either
    a member or a aggregate attribute) of the given registered resource.
    """
    attr = get_domain_class_attribute(ent, attr_name)
    return attr != RESOURCE_ATTRIBUTE_KINDS.TERMINAL


@_arg_to_entity_class
def get_domain_class_attribute_names(ent):
    """
    Returns all attribute names of the given registered resource.
    """
    return ent.__everest_attributes__.keys()


@_arg_to_entity_class
def get_domain_class_attributes(ent):
    """
    Returns a dictionary mapping the attribute names of the given
    registered resource to :class:`ResourceAttribute` instances.
    """
    return ent.__everest_attributes__


@_arg_to_entity_class
def get_domain_class_attribute(ent, name):
    """
    Returns the specified attribute from the map of all collected attributes
    for the given registered resource or `None`, if the attribute could not
    be found.
    """
    return ent.__everest_attributes__.get(name)


@_arg_to_entity_class
def get_domain_class_attribute_iterator(ent):
    """
    Returns an iterator over all attributes in the given registered
    resource.
    """
    return itervalues_(ent.__everest_attributes__)


@_arg_to_entity_class
def get_domain_class_terminal_attribute_iterator(ent):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(ent.__everest_attributes__):
        if attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
            yield attr


@_arg_to_entity_class
def get_domain_class_relationship_attribute_iterator(ent):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(ent.__everest_attributes__):
        if attr.kind != RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
            yield attr


@_arg_to_entity_class
def get_domain_class_member_attribute_iterator(ent):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(ent.__everest_attributes__):
        if attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
            yield attr


@_arg_to_entity_class
def get_domain_class_collection_attribute_iterator(ent):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(ent.__everest_attributes__):
        if attr.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION:
            yield attr
