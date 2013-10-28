"""
Aggregate for the NoSQL backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from everest.entities.base import RootAggregate

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlAggregate',
           ]


class NoSqlAggregate(RootAggregate):
    """
    Aggregate implementation for the NoSQL repository.
    """
    def __init__(self, entity_class, session_factory, repository):
        RootAggregate.__init__(self, entity_class, session_factory, repository)

    def get_by_slug(self, slug):
        pass

    def _query_by_id(self, id_key):
        pass


