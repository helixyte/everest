"""
Resource related utilities.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 3, 2011.
"""
from pyramid.compat import string_types
from pyramid.compat import urlparse
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.traversal import model_path

from everest.interfaces import IResourceUrlConverter
from everest.repositories.utils import as_repository
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IRelation
from everest.resources.interfaces import IResource
from everest.resources.interfaces import IService
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['as_member',
           'get_collection_class',
           'get_member_class',
           'get_registered_collection_resources',
           'get_resource_class_for_relation',
           'get_resource_url',
           'get_root_collection',
           'get_service',
           'is_resource_url',
           'provides_collection_resource',
           'provides_member_resource',
           'provides_resource',
           'resource_to_url',
           'url_to_resource',
           ]


def get_root_collection(resource):
    """
    Returns a clone of the collection from the repository registered for the
    given registered resource.

    :param resource: registered resource
    :type resource: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    repo = as_repository(resource)
    return repo.get_collection(resource)


def get_member_class(resource):
    """
    Returns the registered member class for the given resource.

    :param resource: registered resource
    :type resource: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    reg = get_current_registry()
    if IInterface in provided_by(resource):
        member_class = reg.getUtility(resource, name='member-class')
    else:
        member_class = reg.getAdapter(resource, IMemberResource,
                                      name='member-class')
    return member_class


def get_collection_class(resource):
    """
    Returns the registered collection resource class for the given marker
    interface or member resource class or instance.

    :param rc: registered resource
    :type rc: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    reg = get_current_registry()
    if IInterface in provided_by(resource):
        coll_class = reg.getUtility(resource, name='collection-class')
    else:
        coll_class = reg.getAdapter(resource, ICollectionResource,
                                    name='collection-class')
    return coll_class


def get_resource_class_for_relation(relation):
    """
    Returns the resource class that was registered for the given
    relation.

    :param str relation: relation string.
    """
    reg = get_current_registry()
    return reg.getUtility(IRelation, name=relation)


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
    reg = get_current_registry()
    rc = reg.getAdapter(entity, IMemberResource)
    if not parent is None:
        rc.__parent__ = parent # interface method pylint: disable=E1121
    return rc


def is_resource_url(url_string):
    """
    Checks if the given URL string is a resource URL.

    Currently, this check only looks if the URL scheme is either "http" or
    "https".
    """
    return isinstance(url_string, string_types) \
           and urlparse.urlparse(url_string).scheme in ('http', 'https') # pylint: disable=E1101


def get_resource_url(resource):
    """
    Returns the URL for the given resource.
    """
    path = model_path(resource)
    parsed = list(urlparse.urlparse(path))
    parsed[1] = ""
    return urlparse.urlunparse(parsed)


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
            for util in reg.registeredUtilities()
            if util.name == 'collection-class']


def get_service():
    """
    Registers the object registered as the service utility.

    :returns: object implementing
        :class:`everest.interfaces.IService`
    """
    reg = get_current_registry()
    return reg.getUtility(IService)


def resource_to_url(resource, request=None, quote=False):
    """
    Converts the given resource to a URL.

    :param request: Request object (required for the host name part of the
      URL). If this is not given, the current request is used.
    :param bool quote: If set, the URL returned will be quoted.
    """
    if request is None:
        request = get_current_request()
#    cnv = request.registry.getAdapter(request, IResourceUrlConverter)
    reg = get_current_registry()
    cnv = reg.getAdapter(request, IResourceUrlConverter)
    return cnv.resource_to_url(resource, quote=quote)


def url_to_resource(url, request=None):
    """
    Converts the given URL to a resource.

    :param request: Request object (required for the host name part of the
      URL). If this is not given, the current request is used.
    """
    if request is None:
        request = get_current_request()
#    cnv = request.registry.getAdapter(request, IResourceUrlConverter)
    reg = get_current_registry()
    cnv = reg.getAdapter(request, IResourceUrlConverter)
    return cnv.url_to_resource(url)
