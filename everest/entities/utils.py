"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Utilities for entity classes.

Created on Nov 3, 2011.
"""

from .interfaces import IAggregate
from .interfaces import IEntity
from .interfaces import IRelationAggregateImplementation
from .interfaces import IRootAggregateImplementation
from everest.resources.interfaces import IMemberResource
from everest.staging import STAGING_CONTEXT_MANAGERS
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['get_aggregate',
           'get_aggregate_class_for_collection',
           'get_entity_class_for_member',
           'get_persistent_aggregate',
           'get_transient_aggregate',
           'slug_from_string',
           'slug_from_integer',
           ]


def get_aggregate(collection, relation=None, **kw):
    """
    Returns an instance of the aggregate registered for the given
    collection.

    The entity class to manage by the aggregate is assumed to be the
    entity class registered with the member resource registered for the
    given collection resource or interface.

    :param collection: collection
    :type collection: class implementing or instance providing or subclass of
        :class:`everest.resources.interfaces.ICollectionResource`
    :param related_to: indicates that the aggregate is defined as a subset
        of the root aggregate through a relation
    :type related_to: tuple containing two elements, first the related parent
        entity and second the name of the attribute in the parent that
        references the aggregate
    :return: aggregate instance
        (object providing :class:`everest.models.interfaces.IAggregate`)
    """
    # FIXME: optimize this pylint:disable=W0511
    if isinstance(collection, type(Interface)):
        # If we were passed an interface, translate to the registered class.
        collection = get_utility(collection, 'collection-class')
    agg_cls = get_adapter(collection, IAggregate)
    mb_cls = get_adapter(collection, IMemberResource, 'member-class')
    entity_cls = get_adapter(mb_cls, IEntity)
    return agg_cls.create(entity_cls, relation=relation, **kw)


def get_transient_aggregate(collection, relation=None, **kw):
    if relation is None:
        impl_cls = get_utility(IRootAggregateImplementation,
                               STAGING_CONTEXT_MANAGERS.TRANSIENT)
    else:
        impl_cls = get_utility(IRelationAggregateImplementation,
                               STAGING_CONTEXT_MANAGERS.TRANSIENT)
    kw['implementation'] = impl_cls
    return get_aggregate(collection, relation=relation, **kw)


def get_persistent_aggregate(collection, relation=None, **kw):
    if relation is None:
        impl_cls = get_utility(IRootAggregateImplementation,
                               STAGING_CONTEXT_MANAGERS.PERSISTENT)
    else:
        impl_cls = get_utility(IRelationAggregateImplementation,
                               STAGING_CONTEXT_MANAGERS.PERSISTENT)
    kw['implementation'] = impl_cls
    return get_aggregate(collection, relation=relation, **kw)


def get_entity_class_for_member(member):
    """
    Returns the entity class registered for the given member resource or
    interface.

    :param member: member resource
    :type collection: class implementing or instance providing
        :class:`everest.resources.interfaces.IMemberResource`
    :return: entity class
        (class implementing `everest.models.interfaces.IEntity`)
    """
    return get_adapter(member, IEntity)


def get_aggregate_class_for_collection(collection):
    """
    Returns the aggregate class registered for the given collection resource
    or interface.

    :param collection: collection resource
    :type collection: class implementing or instance providing or subclass of
        :class:`everest.resources.interfaces.ICollectionResource`
    :return: entity class
        (class implementing `everest.models.interfaces.IAggregate`)
    """
    return get_adapter(collection, IAggregate)


def slug_from_string(string):
    """
    Slugs are mnemonic string identifiers for resources for use in URLs.
    
    This function replaces characters that are not allowed to occur in
    a URL with allowed characters.
    """
    # FIXME: Use regexp # pylint: disable=W0511
    return string.replace(' ', '-').replace('_', '-').lower()


def slug_from_integer(integer):
    """
    Slugs are mnemonic string identifiers for resources for use in URLs.

    This function converts an integer into a string slug.
    """
    return str(integer)
