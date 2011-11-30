"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

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
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['as_member',
           'as_representer',
           'get_collection',
           'get_collection_class',
           'get_member_class',
           'get_resource_url',
           'get_root_collection',
           'get_root_collection',
           'get_transient_collection',
           'is_resource_url',
           'provides_collection_resource',
           'provides_member_resource',
           'provides_resource',
           ]


def get_collection(rc):
    """
    Returns a new collection for the given registered resource.

    :param rc: registered resource
    :type rc: class implementing or instance providing or subclass of
        a registered resource interface.
    :returns: an object implementing
        :class:`everest.resources.interfaces.ICollection`
    """
    agg = get_aggregate(rc)
    return get_adapter(agg, ICollectionResource)


def get_transient_collection(rc):
    """
    Returns a collection that uses a transient aggregate for the given
    collection interface.
    """
    agg = get_transient_aggregate(rc)
    return get_adapter(agg, ICollectionResource)


def get_root_collection(rc):
    """
    Returns a clone of the root collection for the given registered resource.

    :param rc: registered resource
    :type rc: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    if IInterface in provided_by(rc):
        rc = get_utility(rc, name='collection-class')
    else:
        rc = get_adapter(rc, ICollectionResource, name='collection-class')
    req = get_current_request()
    return req.root[rc]


def get_member_class(rc):
    """
    Returns the registered member class for the given resource.

    :param rc: registered resource
    :type rc: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    if IInterface in provided_by(rc):
        member_class = get_utility(rc, name='member-class')
    else:
        member_class = get_adapter(rc, IMemberResource, name='member-class')
    return member_class


def get_collection_class(rc):
    """
    Returns the registered collection resource class for the given marker
    interface or member resource class or instance.

    :param rc: registered resource
    :type rc: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    if IInterface in provided_by(rc):
        coll_class = get_utility(rc, name='collection-class')
    else:
        coll_class = get_adapter(rc, ICollectionResource,
                                 name='collection-class')
    return coll_class


def as_member(entity, parent=None):
    """
    Adapts an object to a location aware member resource.

    :param entity: a domain object for which a resource adapter has been
        registered
    :type entity: an object implementing
        :class:`everest.entities.interfaces.IEntity`
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
