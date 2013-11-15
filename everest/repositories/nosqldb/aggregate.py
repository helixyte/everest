"""
Aggregate for the NoSQL backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from everest.entities.base import RootAggregate
from everest.querying.base import EXPRESSION_KINDS

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlAggregate',
           ]


class NoSqlAggregate(RootAggregate):
    """
    Aggregate implementation for the NoSQL repository.
    """
    _expression_kind = EXPRESSION_KINDS.NOSQL

