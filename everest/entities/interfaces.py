"""
Interfaces for entity and aggregate classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 3, 2011.
"""
from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['IAggregate',
           'IEntity',
           ]


# begin interfaces pylint: disable=W0232, E0213, E0211

class IEntity(Interface):
    """
    Marker interface for all entities.
    """

    id = Attribute('Provides a unique ID for this entity instance.')

    slug = Attribute('A unique string identifier for this entity within '
                     'its aggregate. The slug will be used to build URLs.')

    def create_from_data(data):
        """
        """


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

    def query(**options):
        """
        """

# pylint: enable=W0232, E0213, E0211
