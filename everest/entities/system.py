"""
System entities.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 22, 2011.
"""
from datetime import datetime
from everest.entities.base import Entity
from everest.interfaces import IUserMessage
from zope.interface import implementer # pylint: disable=E0611,F0401
import uuid

__docformat__ = 'reStructuredText en'
__all__ = ['UserMessage',
           ]


@implementer(IUserMessage)
class UserMessage(Entity):
    """
    A user message holding a text, a GUID and a time stamp.
    """
    def __init__(self, text, guid=None, time_stamp=None, **kw):
        msg_id = kw.pop('id', None)
        if msg_id is None:
            if guid is None:
                guid = str(uuid.uuid4())
            msg_id = guid
        elif not guid is None and msg_id != guid:
            raise ValueError('Can not pass different values for "guid" and '
                             '"id" parameter.')
        else:
            guid = msg_id
        kw['id'] = msg_id
        Entity.__init__(self, **kw)
        if time_stamp is None:
            time_stamp = datetime.now()
        self.text = text
        self.guid = guid
        self.time_stamp = time_stamp

    @property
    def slug(self):
        return self.guid
