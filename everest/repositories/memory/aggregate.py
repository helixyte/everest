"""
Aggregate for the in-memory and filesystem backends.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.entities.base import RootAggregate
from everest.exceptions import NoResultsException
from everest.querying.base import EXPRESSION_KINDS
from functools import partial

__docformat__ = 'reStructuredText en'
__all__ = ['MemoryAggregate',
           ]


class MemoryAggregate(RootAggregate):
    """
    Root aggregate implementation for the in-memory repository. 

    :note: When entities without a slug are added to a memory aggregate, they
           can not be retrieved using the :meth:`get_by_slug` method.
    """
    _expression_kind = EXPRESSION_KINDS.EVAL

    def get_by_slug(self, slug):
        ent = self._session.get_by_slug(self.entity_class, slug)
        if ent is None:
            query = self.query()
            query = query.filter(partial(self.__evaluator, 'slug', slug))
            try:
                ent = query.one()
            except NoResultsException:
                ent = None
            return ent
        if not ent is None \
           and not self._filter_spec is None \
           and not self._filter_spec.is_satisfied_by(ent):
            ent = None
        return ent

    def _query_by_id(self, id_key):
        query = self.query()
        query = query.filter(partial(self.__evaluator, 'id', id_key))
        try:
            ent = query.one()
        except NoResultsException:
            ent = None
        return ent

    def __evaluator(self, attr, value, entities):
        return (ent for ent in entities if getattr(ent, attr) == value)
