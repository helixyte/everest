"""
Aggregate for the in-memory and filesystem backends.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.entities.base import RootAggregate
from everest.querying.base import EXPRESSION_KINDS

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
