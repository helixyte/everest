"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 17, 2010.
"""

from everest.views.base import ResourceView
from webob.exc import HTTPNotFound

__docformat__ = 'reStructuredText en'
__all__ = ['NotFoundView',
           ]


class NotFoundView(ResourceView):
    """
    """

    def __init__(self, context, request):
        ResourceView.__init__(self, context, request)

    def __call__(self):
        return HTTPNotFound()

