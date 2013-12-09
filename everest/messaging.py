"""
Message notification and handling.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 24, 2011.
"""
from everest.entities.system import UserMessage
from everest.interfaces import IUserMessage
from everest.interfaces import IUserMessageChecker
from everest.interfaces import IUserMessageNotifier
from pyramid.threadlocal import get_current_registry
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['MESSENGER_KINDS',
           'UserMessageChecker',
           'UserMessageNotifier',
           'UserMessageHandlingContextManager',
           ]


class MESSENGER_KINDS(object):
    TRANSIENT = 'transient'
    PERSISTENT = 'persistent'


@implementer(IUserMessageNotifier)
class UserMessageNotifier(object):
    """
    Notifier for user messages.
    """
    def notify(self, message_text):
        msg = UserMessage(message_text)
        reg = get_current_registry()
        vote = True
        checkers = reg.subscribers([msg], IUserMessageChecker)
        for checker in checkers:
            vote = checker.check()
            if vote is False:
                # No further processing.
                break
            elif vote is None:
                # Unconditional further processing.
                vote = True
                break
        # Inform all checkers of the final vote.
        for checker in checkers:
            checker.vote = vote
        return vote


@implementer(IUserMessageChecker)
class UserMessageChecker(object):
    """
    Abstract base class for user message checkers.

    User message checkers can be used to decide if further processing
    should be stopped in response to a non-critical event reported through
    a user message.
    """
    def __init__(self):
        self.__message = None
        # The default vote is True, i.e., continue processing.
        self.vote = True

    def __call__(self, message):
        self.vote = True
        self.__message = message
        return self

    @property
    def message(self):
        return self.__message

    def check(self):
        raise NotImplementedError('Abstract method.')


class UserMessageHandlingContextManager(object):
    """
    A context which sets up a user message checker as a subscriber to
    user messages.
    """
    def __init__(self, checker):
        """
        Constructor.

        :param checker: The user message checker to subscribe to user messages.
        :type checker: :class:`everest.messaging.UserMessageChecker` instance.
        """
        self.__checker = checker

    def __enter__(self):
        reg = get_current_registry()
        reg.registerSubscriptionAdapter(self.__checker, (IUserMessage,),
                                        IUserMessageChecker)

    def __exit__(self, ext_type, value, tb):
        reg = get_current_registry()
        reg.unregisterSubscriptionAdapter(self.__checker, (IUserMessage,),
                                          IUserMessageChecker)
