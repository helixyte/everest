"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 22, 2011.
"""

from everest.views.postcollection import PostCollectionView
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from everest.messaging import IUserMessageEventNotifier
from everest.tests.testapp.entities import FooEntity
from everest.tests.testapp.resources import FooMember
from everest.views.putmember import PutMemberView

__docformat__ = 'reStructuredText en'
__all__ = ['UserMessagePostCollectionView',
           ]


class UserMessagePostCollectionView(PostCollectionView):
    message = 'This is my warning message'
    def _extract_request_data(self):
        msg_notifier = get_utility(IUserMessageEventNotifier)
        msg_notifier.notify(self.message)
        foo = FooEntity(name=self.request.body)
        return FooMember(foo)


class UserMessagePutMemberView(PutMemberView):
    message = 'This is my member warning message'
    def _extract_request_data(self):
        msg_notifier = get_utility(IUserMessageEventNotifier)
        msg_notifier.notify(self.message)
        return self.context

    def _process_request_data(self, data):
        return dict(context=data)
