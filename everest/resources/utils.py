"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Utilities for dealing with resources.

Created on Nov 3, 2011.
"""

from everest.repository import REPOSITORY_DOMAINS
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IPersister
from everest.resources.interfaces import IResource
from everest.resources.interfaces import IResourceRepository
from repoze.bfg.threadlocal import get_current_registry
from repoze.bfg.traversal import model_path
from urlparse import urlparse
from urlparse import urlunparse
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['as_member',
           'get_collection_class',
           'get_member_class',
           'get_resource_url',
           'get_root_collection',
           'get_stage_collection',
           'is_resource_url',
           'provides_collection_resource',
           'provides_member_resource',
           'provides_resource',
           ]


def get_root_collection(rc):
    """
    Returns a clone of the collection in the root repository matching the 
    given registered resource.

    :param rc: registered resource
    :type rc: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    rc_repo = get_utility(IResourceRepository, name=REPOSITORY_DOMAINS.ROOT)
    return rc_repo.get(rc)


def get_stage_collection(rc):
    """
    Returns a clone of the collection in the stage repository matching the 
    given registered resource.

    :param rc: registered resource
    :type rc: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    rc_repo = get_utility(IResourceRepository, name=REPOSITORY_DOMAINS.STAGE)
    return rc_repo.get(rc)


def new_stage_collection(rc):
    """
    Returns a new, empty collection from the stage repository matching the 
    given registered resource.

    :param rc: registered resource
    :type rc: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    rc_repo = get_utility(IResourceRepository, name=REPOSITORY_DOMAINS.STAGE)
    return rc_repo.new(rc)


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
    """
    Returns the URL for the given resource.
    """
    path = model_path(resource)
    parsed = list(urlparse(path))
    parsed[1] = ""
    return urlunparse(parsed)


def provides_resource(obj):
    """
    Checks if the given type or instance provides the
    :class:`everest.resources.interfaces.IResource` interface.
    """
    if isinstance(obj, type):
        obj = object.__new__(obj)
    return IResource in provided_by(obj)


def provides_member_resource(obj):
    """
    Checks if the given type or instance provides the
    :class:`everest.resources.interfaces.IMemberResource` interface.
    """
    if isinstance(obj, type):
        obj = object.__new__(obj)
    return IMemberResource in provided_by(obj)


def provides_collection_resource(obj):
    """
    Checks if the given type or instance provides the
    :class:`everest.resources.interfaces.ICollectionResource` interface.
    """
    if isinstance(obj, type):
        obj = object.__new__(obj)
    return ICollectionResource in provided_by(obj)


def get_registered_collection_resources():
    """
    Returns a list of all registered collection resource classes.
    """
    reg = get_current_registry()
    return [util.component
            for util in reg.getRegisteredUtilities()
            if util.name == 'collection-class']


def get_persister(name):
    """
    Get the persister registered under the given name.
    """
    return get_utility(IPersister, name)


def as_persister(rc):
    """
    Adaptrs the given registered resource to a persister.
    
    :return: object implementing 
      :class:`everest.resources.interfaces.IPersister`.
    """
    if IInterface in provided_by(rc):
        rc = get_utility(rc, name='entity-class')
    return get_adapter(rc, IPersister)
