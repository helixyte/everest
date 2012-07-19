"""
View related utilities.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 4, 2011.
"""
from everest.mime import CSV_MIME

__docformat__ = 'reStructuredText en'
__all__ = ['accept_csv_only',
           ]


def accept_csv_only(context, request): # pylint: disable-msg=W0613
    """
    This can be used as a custom predicate for view configurations with a
    CSV renderer that should only be invoked if this has been explicitly
    requested in the ACCEPT header by the client.
    """
    return CSV_MIME in [acc.lower() for acc in request.accept]
