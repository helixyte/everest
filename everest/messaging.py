"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 24, 2011.
"""

from repoze.bfg.threadlocal import get_current_registry
from repoze.bfg.threadlocal import get_current_request
from zope.component import adapter # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['IUserMessageEvent',
           'IUserMessageEventNotifier',
           'UserMessageEvent',
           'UserMessageEventNotifier',
           'UserMessageHandler',
           ]


# begin interface pylint: disable=W0232
class IUserMessageEvent(Interface):
    pass

class IUserMessageEventNotifier(Interface):
    pass
# end interface pylint: enable=W0232


class UserMessageEvent(object):
    """
    Simple user message.
    """
    implements(IUserMessageEvent)

    def __init__(self, request, message):
        self.request = request
        self.message = message


class UserMessageEventNotifier(object):
    """
    User Message Event notifier service.
    """
    implements(IUserMessageEventNotifier)

    def notify(self, message):
        """
        Notifies all handlers registered to :class:`IUserMessageEvent` events
        of the given message.
        """
        reg = get_current_registry()
        reg.handle(UserMessageEvent(get_current_request(), message))


class UserMessageHandler(object):
    """
    Handler for user messages delivered through the 
    :class:`IUserMessageEventNotifier` service.
    """
    __handler_map = {}

    def __init__(self):
        self.__messages = []

    def has_messages(self):
        return len(self.__messages) > 0

    def add_message(self, message):
        self.__messages.append(message)

    def get_messages(self):
        return self.__messages[:]

    @classmethod
    def register(cls, handler, request):
        cls.__handler_map[request] = handler

    @classmethod
    def unregister(cls, request):
        cls.__handler_map.pop(request, None)

    @classmethod
    @adapter(IUserMessageEvent)
    def handle_user_message_event(cls, event):
        handler = cls.__handler_map[event.request]
        handler.add_message(event.message)
