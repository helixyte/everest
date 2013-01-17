"""
Aggregate for the NoSQL backend.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from everest.entities.base import Aggregate

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlAggregate',
           ]


class NoSqlAggregate(Aggregate):
    """
    Aggregate implementation for the NoSQL data store.
    """
    def __init__(self, entity_class, session_factory):
        Aggregate.__init__(self, entity_class, session_factory)

    def count(self):
        pass

    def get_by_id(self, id_key):
        pass

    def get_by_slug(self, slug):
        pass

    def iterator(self):
        pass

    def add(self, entity):
        pass

    def remove(self, entity):
        pass

    def update(self, entity, source_entity):
        pass

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass
