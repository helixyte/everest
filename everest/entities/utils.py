"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Utilities for entity classes.

Created on Nov 3, 2011.
"""

from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.interfaces import IRepository
from everest.repository import REPOSITORIES
from everest.repository import as_repository
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['get_aggregate_class',
           'get_entity_class',
           'get_root_aggregate',
           'get_stage_aggregate',
           'identifier_from_slug',
           'slug_from_identifier',
           'slug_from_integer',
           'slug_from_string',
           ]


def get_root_aggregate(rc):
    """
    Returns an aggregate from the root entity repository for the given 
    registered resource.
    """
    repo = as_repository(rc)
    coll = repo.get(rc)
    return coll.get_aggregate()


def get_stage_aggregate(rc):
    """
    Returns an aggregate from the stage entity repository for the given 
    registered resource.
    """
    repo = get_utility(IRepository, name=REPOSITORIES.MEMORY)
    coll = repo.get(rc)
    return coll.get_aggregate()


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


def get_aggregate_class(rc):
    """
    Returns the aggregate class registered for the given registered resource.

    :param member: registered resource
    :type collection: class implementing or instance providing a registered
        resource interface.
    :return: aggregate class
        (class implementing `everest.entities.interfaces.IAggregate`)
    """
    if IInterface in provided_by(rc):
        agg_cls = get_utility(rc, name='aggregate-class')
    else:
        agg_cls = get_adapter(rc, IAggregate, name='aggregate-class')
    return agg_cls


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


def slug_from_identifier(id_string):
    """
    Converts the given identifier string into a slug.

    :param str id_string: identifier string
    """
    return id_string.replace('_', '-')


def identifier_from_slug(slug):
    """
    Converts the given slug into an identifier string.
    
    :param str slug: slug string
    """
    return slug.replace('-', '_')
