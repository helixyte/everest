"""
Aggregate for the RDB backend.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.entities.base import RootAggregate
from everest.exceptions import NoResultsException
from everest.querying.base import EXPRESSION_KINDS

__docformat__ = 'reStructuredText en'
__all__ = ['RdbAggregate',
           ]


class RdbAggregate(RootAggregate):
    """
    Root aggregate implementation for the RDB repository.
    """
    _expression_kind = EXPRESSION_KINDS.SQL

    def get_by_slug(self, slug):
        try:
            ent = self.query().filter_by(slug=slug).one()
        except NoResultsException:
            ent = None
        if not ent is None \
           and not self._filter_spec is None \
           and not self._filter_spec.is_satisfied_by(ent):
            ent = None
        return ent

    def _query_by_id(self, id_key):
        try:
            ent = self.query().filter_by(id=id_key).one()
        except NoResultsException:
            ent = None
        return ent

    def query(self):
        # Need to perform a flush here so that filter expressions are always
        # generated correctly.
        self._session.flush()
        return RootAggregate.query(self)
