"""
System entities.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 22, 2011.
"""
from datetime import datetime
from everest.entities.base import Entity
from everest.interfaces import IUserMessage
from zope.interface import implements # pylint: disable=E0611,F0401
import uuid

__docformat__ = 'reStructuredText en'
__all__ = ['UserMessage',
           ]


class UserMessage(Entity):
    implements(IUserMessage)
    def __init__(self, text, guid=None, time_stamp=None, **kw):
        Entity.__init__(self, **kw)
        if guid is None:
            guid = str(uuid.uuid4())
        if time_stamp is None:
            time_stamp = datetime.now()
        self.text = text
        self.guid = guid
        self.time_stamp = time_stamp

    @property
    def slug(self):
        return self.guid
