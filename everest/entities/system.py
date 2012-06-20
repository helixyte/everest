"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 22, 2011.
"""
from everest.entities.base import Entity
from everest.interfaces import IUserMessage
from zope.interface import implements # pylint: disable=E0611,F0401
import uuid

__docformat__ = 'reStructuredText en'
__all__ = ['UserMessage',
           ]


class UserMessage(Entity):
    implements(IUserMessage)
    def __init__(self, text, **kw):
        Entity.__init__(self, **kw)
        self.text = text
        self.__uuid4 = uuid.uuid4()

    @property
    def slug(self):
        return str(self.__uuid4)
