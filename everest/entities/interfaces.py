"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Marker interfaces for entities and aggregates.

Created on Nov 3, 2011.
"""

from everest.interfaces import IRepository
from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['IAggregate',
           'IEntity',
           'IEntityRepository',
           'IRelationAggregateImplementation',
           'IRootAggregateImplementation',
           ]


# begin interfaces pylint: disable=W0232, E0213, E0211

class IEntity(Interface):
    """
    Marker interface for all entities.
    """

    id = Attribute('Provides a unique ID for this entity instance.')
    slug = Attribute('A unique string identifier for this entity within '
                     'its aggregate. The slug will be used to build URLs.')


class IAggregate(Interface):
    """
    Marker interface for all aggregates.

    An aggregate is to an entity what a collection resource is to a member
    resource.
    """

    def create(entity_class, relation=None, ** kw):
        """
        """

    def clone():
        """
        """

    def count():
        """
        """

    def get_by_id(id_key):
        """
        """

    def get_by_slug(slug):
        """
        """

    def iterator():
        """
        """

    def add(entity):
        """
        """

    def remove(entity):
        """
        """


class IAggregateImplementationRegistry(Interface):
    """
    Interface for the aggregate implementation registry.
    """
    def register(implementation_class):
        """
        Registers the given implementation class with the registry.
        """

    def unregister(implementation_class):
        """
        Removes the specified registered implementation class from the 
        registry.
        """

    def is_registered(implementation_class):
        """
        Checks if the given implementation class was registered with this
        registry.
        """

    def get_registered():
        """
        Returns a list of all registered implementation classes.
        """


class IEntityRepository(IRepository):
    """
    Marker interface for entity repositories.
    """


class IStagingContextManager(Interface):
    def __enter__():
        """Enters the context."""
    def __exit__():
        """Exits the context."""


class IAggregateImplementation(Interface):
    """
    Marker interface for aggregate implementations.
    """

# pylint: enable=W0232, E0213, E0211
