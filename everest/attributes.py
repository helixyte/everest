"""
General attribute access functions.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 22, 2013.
"""
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import RESOURCE_ATTRIBUTE_KINDS

__docformat__ = 'reStructuredText en'
__all__ = ['get_attribute_cardinality',
           'is_terminal_attribute',
           ]


def is_terminal_attribute(attribute):
    """
    Checks if the given resource attribute is a terminal attribute.
    """
    return attribute.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL


def get_attribute_cardinality(attribute):
    """
    Returns the cardinality of the given resource attribute.

    :returns: One of the constants defined in
      :class:`evererst.constants.CARDINALITY_CONSTANTS`.
    :raises ValueError: If the given attribute is not a relation attribute
      (i.e., if it is a terminal attribute).
    """
    if attribute.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
        card = CARDINALITY_CONSTANTS.ONE
    elif attribute.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION:
        card = CARDINALITY_CONSTANTS.MANY
    else:
        raise ValueError('Can not determine cardinality for non-terminal '
                         'attributes.')
    return card
