"""
PUT member view.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""
from everest.views.base import PutOrPatchResourceView


__docformat__ = 'reStructuredText en'
__all__ = ['PutMemberView',
           ]


class PutMemberView(PutOrPatchResourceView):
    """
    View for PUT requests on member resources.

    The client sends a PUT request to replace a member resource with a
    new, complete representation (cf. PATCH for partial updates). If the
    request is successful, the server responds with status HTTP OK.
    """
    pass