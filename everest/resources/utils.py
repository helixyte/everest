"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Utilities for dealing with resources.

Created on Nov 3, 2011.
"""

from everest.entities.utils import get_aggregate
from everest.entities.utils import get_transient_aggregate
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResource
from repoze.bfg.threadlocal import get_current_request
from repoze.bfg.traversal import model_path
from urlparse import urlparse
from urlparse import urlunparse
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['as_member',
           'as_representer',
           'get_collection',
           'get_collection_class',
           'get_member_class',
           'get_resource_url',
           'get_root_collection',
           'get_root_collection_for_member',
           'get_transient_collection',
           'is_resource_url',
           'provides_collection_resource',
           'provides_member_resource',
           'provides_resource',
           ]


def get_collection(collection):
    """
    Returns a new collection for the given collection.

    :param collection: collection resource
    :type collection: class implementing or instance providing or subclass of
        :class:`everest.resources.interfaces.ICollectionResource`
    :returns: an object implementing
        :class:`everest.resources.interfaces.ICollection`
    """
    agg = get_aggregate(collection)
    return get_adapter(agg, ICollectionResource)


def get_transient_collection(collection):
    """
    Returns a collection that uses a transient aggregate for the given
    collection interface.
    """
    agg = get_transient_aggregate(collection)
    return get_adapter(agg, ICollectionResource)


def get_root_collection(collection):
    """
    Returns a clone of the root collection for the given collection interface.

    :param collection: collection interface
    :type collection: subclass of
        :class:`everest.resources.interfaces.ICollectionResource`
    """
    if isinstance(collection, type(Interface)):
        # If we were passed an interface, translate to the registered class.
        collection = get_utility(collection, 'collection-class')
    req = get_current_request()
    return req.root[collection]


def get_root_collection_for_member(member):
    """
    Returns a new collection for the given member.

    :param member: member resource
    :type member: class implementing or instance providing or subclass of
        :class:`everest.resources.interfaces.IMemberResource`
    """
    if isinstance(member, type(Interface)):
        # If we were passed an interface, translate to the registered class.
        member = get_utility(member, 'member-class')
    coll = get_adapter(member, ICollectionResource, 'collection-class')
    return get_root_collection(coll)


def get_member_class(adaptee):
    """
    Returns the registered member resource class for the given marker
    interface or collection resource class or instance.

    :param collection: object to look up
    :type collection: marker interface or class implementing or instance
         providing :class:`everest.resources.interfaces.IMemberResource`
    """
    return get_adapter(adaptee, IMemberResource, 'member-class')


def get_collection_class(adaptee):
    """
    Returns the registered collection resource class for the given marker
    interface or member resource class or instance.

    :param adaptee: object to look up
    :type collection: marker interface or instance implementing
        :class:`everest.resources.interfaces.IMemberResource`
    """
    return get_adapter(adaptee, ICollectionResource, 'collection-class')


def as_member(entity, parent=None):
    """
    Adapts an object to a location aware member resource.

    :param entity: a domain object for which a resource adapter has been
        registered
    :type entity: an object implementing
        :class:`everest.models.interfaces.IEntity`
    :param parent: optional parent collection resource to make the new member
        a child of
    :type parent: an object implementing
        :class:`everest.resources.interfaces.ICollectionResource`
    :returns: an object implementing
        :class:`everest.resources.interfaces.IMemberResource`
    """
    rc = get_adapter(entity, IMemberResource)
    if not parent is None:
        rc.__parent__ = parent # interface method pylint: disable=E1121
    return rc


def is_resource_url(url_string):
    """
    Checks if the given URL string is a resource URL.

    Currently, this check only looks if the URL scheme is either "http" or
    "https".
    """
    return isinstance(url_string, basestring) \
           and urlparse(url_string).scheme in ('http', 'https') # pylint: disable=E1101


def get_resource_url(resource):
    path = model_path(resource)
    parsed = list(urlparse(path))
    parsed[1] = ""
    return urlunparse(parsed)


def provides_resource(type_):
    """
    Checks if the given type provides the
    :class:`everest.resources.interfaces.IResource` interface.
    """
    return IResource in provided_by(object.__new__(type_))


def provides_member_resource(type_):
    """
    Checks if the given type provides the
    :class:`everest.resources.interfaces.IMemberResource` interface.
    """
    return IMemberResource in provided_by(object.__new__(type_))


def provides_collection_resource(type_):
    """
    Checks if the given type provides the
    :class:`everest.resources.interfaces.ICollectionResource` interface.
    """
    return ICollectionResource in provided_by(object.__new__(type_))
