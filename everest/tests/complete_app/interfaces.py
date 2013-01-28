"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 1, 2011.
"""
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = []


# pylint: disable=W0232
class IMyEntityParent(Interface):
    pass


class IMyEntity(Interface):
    pass


class IMyEntityChild(Interface):
    pass


class IMyEntityGrandchild(Interface):
    pass
# pylint: enable=W0232
