"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 19, 2012.
"""
from everest.entities.system import UserMessage
from everest.interfaces import IUserMessageNotifier
from everest.messaging import UserMessageChecker
from everest.messaging import UserMessageHandlingContextManager
from everest.messaging import UserMessageNotifier
from everest.testing import TestCaseWithConfiguration

__docformat__ = 'reStructuredText en'
__all__ = ['MessagingTestCase',
           ]


class MessagingTestCase(TestCaseWithConfiguration):
    def set_up(self):
        TestCaseWithConfiguration.set_up(self)
        reg = self.config.registry
        reg.registerUtility(UserMessageNotifier(), # pylint:disable=E1103
                            IUserMessageNotifier)
        self.values = []

    def test_user_message(self):
        self.assert_raises(ValueError, UserMessage, 'blah', guid='-1', id=1)

    def test_single(self):
        checker1 = MyChecker1()
        self.assert_true(checker1.vote is True)
        # Sending with TRUE message triggers an append to self.values.
        with UserMessageHandlingContextManager(checker1):
            self.__routine_which_sends_user_message(MESSAGE_ONE)
        self.assert_equal(self.values, [True])
        self.assert_equal(checker1.vote, True)
        # Sending with "FALSE" message vetoes the append.
        self.values.pop()
        with UserMessageHandlingContextManager(checker1):
            self.__routine_which_sends_user_message(MESSAGE_TWO)
        self.assert_equal(self.values, [])
        self.assert_equal(checker1.vote, False)
        # Sending without registered checker1 triggers an append (because
        # there is no veto), but does not change the checking vote.
        self.__routine_which_sends_user_message(MESSAGE_ONE)
        self.assert_equal(self.values, [True])
        self.assert_equal(checker1.vote, False)

    def test_nested(self):
        checker1 = MyChecker1()
        checker2 = MyChecker2()
        # No action because checker 2 returns False.
        with UserMessageHandlingContextManager(checker1):
            with UserMessageHandlingContextManager(checker2):
                self.__routine_which_sends_user_message(MESSAGE_ONE)
        self.assert_equal(self.values, [])
        self.assert_equal(checker1.vote, False)
        self.assert_equal(checker2.vote, False)
        self.assert_equal(checker1.myvote, True)
        self.assert_equal(checker2.myvote, False)
        # No action because checker 1 returns False. Checker 2 is not touched.
        checker2.myvote = -1
        with UserMessageHandlingContextManager(checker1):
            with UserMessageHandlingContextManager(checker2):
                self.__routine_which_sends_user_message(MESSAGE_TWO)
        self.assert_equal(self.values, [])
        self.assert_equal(checker1.vote, False)
        self.assert_equal(checker2.vote, False)
        self.assert_equal(checker1.myvote, False)
        self.assert_equal(checker2.myvote, -1)
        # Action because checker 1 returns None. Checker 2 is not touched.
        with UserMessageHandlingContextManager(checker1):
            with UserMessageHandlingContextManager(checker2):
                self.__routine_which_sends_user_message(MESSAGE_THREE)
        self.assert_equal(self.values, [True])
        self.assert_equal(checker1.vote, True)
        self.assert_equal(checker2.vote, True)
        self.assert_is_none(checker1.myvote)
        self.assert_equal(checker2.myvote, -1)

    def __routine_which_sends_user_message(self, msg):
        msg_notifier = \
          self.config.get_registered_utility(IUserMessageNotifier)
        if msg_notifier.notify(msg):
            self.values.append(True)


MESSAGE_ONE = 'ONE'
MESSAGE_TWO = 'TWO'
MESSAGE_THREE = 'THREE'


class MyChecker1(UserMessageChecker):
    myvote = -1
    def check(self):
        if self.message.text == MESSAGE_ONE:
            vote = True
        elif self.message.text == MESSAGE_TWO:
            vote = False
        else:
            vote = None
        self.myvote = vote
        return vote


class MyChecker2(UserMessageChecker):
    myvote = -1
    def check(self):
        if self.message.text == MESSAGE_ONE:
            vote = False
        elif self.message.text == MESSAGE_TWO:
            vote = True
        else:
            vote = False
        self.myvote = vote
        return vote
