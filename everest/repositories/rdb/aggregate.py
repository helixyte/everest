"""
Aggregate for the RDB backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.entities.base import RootAggregate
from everest.querying.base import EXPRESSION_KINDS

__docformat__ = 'reStructuredText en'
__all__ = ['RdbAggregate',
           ]


class RdbAggregate(RootAggregate):
    """
    Root aggregate implementation for the RDB repository.
    """
    _expression_kind = EXPRESSION_KINDS.SQL

    def query(self):
        # Need to perform a flush here so that filter expressions are always
        # generated correctly.
        self._session.flush()
        return RootAggregate.query(self)
