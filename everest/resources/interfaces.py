"""
Interfaces for resources.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 3, 2011.
"""
from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ICollectionResource',
           'ILocationAware',
           'IMemberResource',
           'IRelation',
           'IResource',
           'IResourceLink',
           'IResourceAttribute',
           'IResourceLink',
           'IService',
           'ITraversable',
           ]


# interfaces do not provide a constructor. pylint: disable=W0232
# interface methods do not have self pylint: disable = E0213
# interface methods may have no arguments pylint:disable = E0211
class ILocationAware(Interface):
    """
    ILocationAware Interface

    Applications which use traversal to locate the context of a view must
    ensure that the model instances that make up the model graph are
    "location aware".

    In order for location, security, URL-generation, and traversal functions
    to work properly against a instances in an object graph, all nodes in the
    object graph must be location-aware.

    The __parent__ of the root object should be None and its __name__ should be
    the empty string. For instance:

    @implementer(ILocationAware)
    class MyRootObject(object):
        __name__ = ''
        __parent__ = None
    """

    __name__ = Attribute('A string representing the name that a node\'s parent '
                         'refers to via __getitem__')

    __parent__ = Attribute('A reference to the node\'s parent model instance '
                           'in the object graph which is also an '
                           'ILocationAware.')

class ITraversable(Interface):
    """
    ITraversable Interface

    Traversal is a context finding mechanism. It is the act of finding a context
    and a view name by walking over an object graph, starting from a root object,
    using a request object as a source of path information.
    """

    def __getitem__(name):
        """
        Returns a "contained" object referenced by "name"

        :param name: a string that is used as a key to reference the contained
                     object
        :type name: string
        :returns: an instance of an ILocationAware object
        """

class IResource(ILocationAware, ITraversable):
    """
    IResource Interface

    A resource exposes an entity (model object) for interaction. While the
    model objects ensure consistent value state, the resources implement the
    business logic through atomic resource interactions.
    """

    # : The title of the resource.
    title = Attribute('Title of the resource.')

    # : A description of the resource.
    description = Attribute('Description of the resource.')

    # : The (URL) path for the resource.
    path = Attribute('The (URL) path for the resource.')

    # : The URN for the resource.
    urn = Attribute('The URN for the resource.')

    def get_url(request, **kwargs):
        """
        Returns a valid URL for this resource given a request and query
        parameters.

        :param request: request
        :type request: object implementing IRequest
        :returns: an string which is a valid URL
        """


class ICollectionResource(IResource):
    """
    Interface for collection resources.
    """

    root_name = Attribute('The name for the root collection.')

    def __len__():
        """
        Returns the number of members in the collection.
        """

    def __iter__():
        """
        Returns an iterator over the members in the collection.
        """

    def __getitem__(key):
        """
        Returns the member specified by the given key or raises a
        `KeyError` if no such member is found.
        """

    def add(member):
        """
        Adds a member to the collection.

        :param member: a member instance
        :type member: object implementing the
            :class:`everest.resources.interfaces.IMember` interface
        """

    def remove(member):
        """
        Removes a member from the collection.

        :param member: a member instance
        :type member: object implementing the
            :class:`everest.resources.interfaces.IMember` interface
        """

    def get(key, default=None):
        """
        Returns the member specified by the given name or the given default
        if no such member is found.

        :param str name: member name
        :param object default: value to return if the member is not found;
          defaults to `None`.
        """


class IMemberResource(IResource):
    """
    Interface for member resources.
    """

    # : The entity class (subclass of :class:`everest.entities.base.Entity`)
    # : associated with this member attribute. The entity class must
    # : implement an interface inheriting from
    # : :class:`everest.entities.interface.IEntity`.
    entity_class = Attribute('The entity class associated with this member '
                             'resource. Instances implement an interface '
                             'derived from '
                             ':class:`everest.entities.interfaces.IEntity`')

    def create_from_entity(entity):
        """
        Creates an instance of this resource from an associated entity.

        :param entity: entity (holds value state)
        :type entity: object implementing
            :class:`everest.entities.interfaces.IEntity`
        """

    def get_entity():
        """
        Returns the entity (domain object) associated with this resource.

        :returns: instance implementing an interface derived from
          :class:`everest.entities.interfaces.IEntity`
        """


class IResourceLink(Interface):
    """
    Interface for resource links.
    """

    href = Attribute('URL of the linked resource.')
    rel = Attribute('Relation of the linked resource.')
    type = Attribute('Media type of the linked resource.')
    length = Attribute('Indicates the size of the linked resource.')
    title = Attribute('Title for the linked resource.')


class IService(IResource):
    """
    Marker interface for the service object.
    """

    def register(irc):
        """
        Registers the given resource interface with this service.
        """

    def start(self):
        """
        Starts the service.
        """


class IRelation(Interface):
    """
    Marker interface for relations.
    """


class IResourceAttribute(Interface):
    """
    Interface for resource attributes.
    """
    kind = Attribute('The resource attribute kind. One of the constants '
                     'defined in everest.constants.RESOURCE_ATTRIBUTE_KINDS.')
    attr_type = Attribute('The type of the resource attribute. This is '
                          'typically')
    entity_attr = Attribute('The name of the resource attribute in the '
                            'entity. May be *None*.')
    index = Attribute('Unique sequential numeric ID for this resource '
                      'attribute. Used to maintain the order in which '
                      'resource attributes are iterated over.')
    resource_attr = Attribute('The name of the resource attribute in the '
                              'resource.')


# pylint: enable=W0232,E0213,E0211
