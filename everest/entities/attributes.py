"""
Entity attributes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 2, 2011.
"""
from everest.attributes import AttributeValueMap
from everest.constants import DEFAULT_CASCADE
from everest.constants import DomainAttributeKinds
from everest.entities.interfaces import IEntity
from everest.entities.relationship import DomainRelationship
from everest.entities.utils import get_entity_class
from functools import wraps
from pyramid.compat import itervalues_
from zope.interface import implementedBy as implemented_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['DomainAttributeValueMap',
           'aggregate_attribute',
           'attribute_base',
           'entity_attribute',
           'get_domain_class_attribute_iterator',
           'get_domain_class_attribute',
           'get_domain_class_attribute_iterator',
           'get_domain_class_attribute_names',
           'get_domain_class_attributes',
           'get_domain_class_domain_attribute_iterator',
           'get_domain_class_entity_attribute_iterator',
           'get_domain_class_terminal_attribute_iterator',
           'is_domain_class_aggregate_attribute',
           'is_domain_class_domain_attribute',
           'is_domain_class_entity_attribute',
           'is_domain_class_terminal_attribute',
           'terminal_attribute',
           ]


class attribute_base(object):
    """
    Abstract base class for all domain attribute classes.

    :cvar kind: the domain attribute kind.
    :ivar attr_type: the type of the domain attribute.
    :ivar int index: unique serial ID (or ordering purposes).
    :ivar entity_attr: the entity attribute the domain attribute references.
    :ivar resource_attr: the resource attribute the domain attribute is
        mapped to.
    """
    #: The domain attribute kind (one of the constants defined in
    #: :class:`everest.constants.DomainAttributeKinds`). Set in derived
    #: classes.
    kind = None

    def __init__(self, attr_type, index, entity_attr, resource_attr):
        self.attr_type = attr_type
        self.index = index
        self.entity_attr = entity_attr
        self.resource_attr = resource_attr

    def __str__(self):
        return "%s: ent attr %s, type %s" \
               % (self.__class__.__name__, self.entity_attr, self.attr_type)


class terminal_attribute(attribute_base):
    """
    Terminal domain attribute.
    """
    kind = DomainAttributeKinds.TERMINAL


class _relation_attribute(attribute_base):
    """
    Base class for relation (non-terminal) domain attributes.
    """
    def __init__(self, attr_type, index, entity_attr=None, resource_attr=None,
                 cardinality=None, cascade=DEFAULT_CASCADE,
                 entity_backref=None, resource_backref=None):
        attribute_base.__init__(self, attr_type, index, entity_attr,
                                 resource_attr)
        self.cardinality = cardinality
        self.cascade = cascade
        self.entity_backref = entity_backref
        self.resource_backref = resource_backref

    def make_relationship(self, relator):
        """
        Creates a relationship object for this domain attribute with the
        given relator.

        :param relator: entity or aggregate object serving as the source end
            of the relationship.
        :returns: :class:`everest.entities.relationship.DomainRelationship`
        """
        return DomainRelationship(relator, self)


class entity_attribute(_relation_attribute):
    """
    Entity domain attribute.
    """
    kind = DomainAttributeKinds.ENTITY


class aggregate_attribute(_relation_attribute):
    """
    Aggregate domain attribute.
    """
    kind = DomainAttributeKinds.AGGREGATE


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
    return attr.kind == DomainAttributeKinds.TERMINAL


def is_domain_class_entity_attribute(ent, attr_name):
    """
    Checks if the given attribute name is a entity attribute of the given
    registered resource.
    """
    attr = get_domain_class_attribute(ent, attr_name)
    return attr.kind == DomainAttributeKinds.ENTITY


def is_domain_class_aggregate_attribute(ent, attr_name):
    """
    Checks if the given attribute name is a aggregate attribute of the given
    registered resource.
    """
    attr = get_domain_class_attribute(ent, attr_name)
    return attr.kind == DomainAttributeKinds.AGGREGATE


def is_domain_class_domain_attribute(ent, attr_name):
    """
    Checks if the given attribute name is a resource attribute (i.e., either
    a member or a aggregate attribute) of the given registered resource.
    """
    attr = get_domain_class_attribute(ent, attr_name)
    return attr != DomainAttributeKinds.TERMINAL


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
        if attr.kind == DomainAttributeKinds.TERMINAL:
            yield attr


@_arg_to_entity_class
def get_domain_class_domain_attribute_iterator(ent):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(ent.__everest_attributes__):
        if attr.kind != DomainAttributeKinds.TERMINAL:
            yield attr


@_arg_to_entity_class
def get_domain_class_entity_attribute_iterator(ent):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(ent.__everest_attributes__):
        if attr.kind == DomainAttributeKinds.ENTITY:
            yield attr


@_arg_to_entity_class
def get_domain_class_aggregate_attribute_iterator(ent):
    """
    Returns an iterator over all terminal attributes in the given registered
    resource.
    """
    for attr in itervalues_(ent.__everest_attributes__):
        if attr.kind == DomainAttributeKinds.AGGREGATE:
            yield attr


class DomainAttributeValueMap(AttributeValueMap):
    def _get_attribute_attribute(self, attr):
        return attr.entity_attr
