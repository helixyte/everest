"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 11, 2010.
"""

from everest.views.base import MemberView
import logging

__docformat__ = "reStructuredText en"
__all__ = ['GetMemberView',
           ]


class GetMemberView(MemberView):
    """
    """

    __logger = logging.getLogger(__name__)

    def __init__(self, member, request):
        MemberView.__init__(self, member, request)

    def __call__(self):
        self.__logger.debug('Request URL: %s' % self.request.url)
        return {}
