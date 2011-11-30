"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Utilities for entity classes.

Created on Nov 3, 2011.
"""

from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.entities.interfaces import IRelationAggregateImplementation
from everest.entities.interfaces import IRootAggregateImplementation
from everest.staging import STAGING_CONTEXT_MANAGERS
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['get_aggregate',
           'get_aggregate_class_for_collection',
           'get_entity_class',
           'get_persistent_aggregate',
           'get_transient_aggregate',
           'slug_from_string',
           'slug_from_integer',
           ]


def get_aggregate(rc, relation=None, **kw):
    """
    Returns an instance of the aggregate registered for the given
    registered resource.

    The entity class to manage by the aggregate is assumed to be the
    entity class registered with the member resource registered for the
    given collection resource or interface.

    :param rc: registered resource
    :type rc: class implementing or instance providing or subclass of
        a registered resource interface.
    :param related_to: indicates that the aggregate is defined as a subset
        of the root aggregate through a relation
    :type related_to: tuple containing two elements, first the related parent
        entity and second the name of the attribute in the parent that
        references the aggregate
    :return: aggregate instance
        (object providing :class:`everest.entities.interfaces.IAggregate`)
    """
    if IInterface in provided_by(rc):
        agg_cls = get_utility(rc, name='aggregate-class')
        entity_cls = get_utility(rc, name='entity-class')
    else:
        agg_cls = get_adapter(rc, IAggregate, name='aggregate-class')
        entity_cls = get_adapter(rc, IEntity, name='entity-class')
    return agg_cls.create(entity_cls, relation=relation, **kw)


def get_transient_aggregate(rc, relation=None, **kw):
    if relation is None:
        impl_cls = get_utility(IRootAggregateImplementation,
                               STAGING_CONTEXT_MANAGERS.TRANSIENT)
    else:
        impl_cls = get_utility(IRelationAggregateImplementation,
                               STAGING_CONTEXT_MANAGERS.TRANSIENT)
    kw['implementation'] = impl_cls
    return get_aggregate(rc, relation=relation, **kw)


def get_persistent_aggregate(rc, relation=None, **kw):
    if relation is None:
        impl_cls = get_utility(IRootAggregateImplementation,
                               STAGING_CONTEXT_MANAGERS.PERSISTENT)
    else:
        impl_cls = get_utility(IRelationAggregateImplementation,
                               STAGING_CONTEXT_MANAGERS.PERSISTENT)
    kw['implementation'] = impl_cls
    return get_aggregate(rc, relation=relation, **kw)


def get_entity_class(rc):
    """
    Returns the entity class registered for the given registered resource.

    :param member: registered resource
    :type collection: class implementing or instance providing a registered
        resource interface.
    :return: entity class
        (class implementing `everest.entities.interfaces.IEntity`)
    """
    if IInterface in provided_by(rc):
        ent_cls = get_utility(rc, name='entity-class')
    else:
        ent_cls = get_adapter(rc, IEntity, name='entity-class')
    return ent_cls


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
