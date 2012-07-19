"""
Get member view.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 11, 2010.
"""
from everest.views.base import GetResourceView

__docformat__ = "reStructuredText en"
__all__ = ['GetMemberView',
           ]


class GetMemberView(GetResourceView):
    """
    View for GET requests on member resources.
    """

    def __call__(self):
        self._logger.debug('Request URL: %s' % self.request.url)
        return {}
