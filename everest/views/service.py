"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on May 4, 2010.
"""

from everest.views.base import ResourceView

__docformat__ = "reStructuredText en"
__all__ = ['ServiceView',
           ]


class ServiceView(ResourceView):
    """
    """

    def __init__(self, service, request):
        ResourceView.__init__(self, service, request)

    def __call__(self):
        return {}
