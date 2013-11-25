"""
Entity related utilities.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 3, 2011.
"""
from everest.entities.interfaces import IEntity
from everest.repositories.utils import as_repository
from pyramid.threadlocal import get_current_registry
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface # pylint: disable=E0611,F0401
import uuid

__docformat__ = 'reStructuredText en'
__all__ = ['get_entity_class',
           'get_root_aggregate',
           'identifier_from_slug',
           'slug_from_identifier',
           'slug_from_integer',
           'slug_from_string',
           ]


def get_root_aggregate(resource):
    """
    Returns an aggregate from the root entity repository for the given
    registered resource.

    :param resource: registered resource
    """
    repo = as_repository(resource)
    return repo.get_aggregate(resource)


def get_entity_class(resource):
    """
    Returns the entity class registered for the given registered resource.

    :param resource: registered resource
    :type collection: class implementing or instance providing a registered
        resource interface.
    :return: entity class
        (class implementing `everest.entities.interfaces.IEntity`)
    """
    reg = get_current_registry()
    if IInterface in provided_by(resource):
        ent_cls = reg.getUtility(resource, name='entity-class')
    else:
        ent_cls = reg.getAdapter(resource, IEntity, name='entity-class')
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


def new_entity_id():
    """
    Generates a new (global) ID.

    Uses the :func:`uuid.uuid1` function to generate unique string IDs
    which are sortable by creation time.

    :return: UUID string.
    """
    return str(uuid.uuid1())
