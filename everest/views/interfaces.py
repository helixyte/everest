"""
Interfaces for views.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 22, 2010.
"""
from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['IResourceView',
           ]


# interfaces do not provide a constructor. pylint: disable=W0232
# interface methods may have no arguments pylint:disable = E0211
# interface methods may have different arguments pylint:disable = W0221

class IResourceView(Interface):
    """
    Interface for resource views.
    """

    context = Attribute("The request's context")
    request = Attribute("The context from the object graph")

    def __call__():
        """
        """

# pylint: disable=W0232,E0211,W0221
