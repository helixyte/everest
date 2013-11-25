"""
Interfaces for views.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 22, 2010.
"""
from zope.interface import Interface, Attribute # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['IResourceView',
           ]


# no __init__, no self. pylint: disable=W0232,E0211

class IResourceView(Interface):
    """
    Interface for resource views.
    """

    context = Attribute("The request's context")
    request = Attribute("The context from the object graph")

    def __call__():
        """
        """
# pylint: disable=W0232,E0211
