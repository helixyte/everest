"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 22, 2011.
"""
from everest.messaging import IUserMessageNotifier
from everest.tests.simple_app.entities import FooEntity
from everest.tests.simple_app.resources import FooMember
from everest.views.postcollection import PostCollectionView
from everest.views.putmember import PutMemberView
from pyramid.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['UserMessagePutMemberView',
           'UserMessagePostCollectionView',
           ]


class UserMessagePostCollectionView(PostCollectionView):
    message = 'This is my warning message'
    def _extract_request_data(self):
        foo = FooEntity(name=self.request.body)
        return FooMember(foo)

    def _process_request_data(self, data):
        reg = get_current_registry()
        msg_notifier = reg.getUtility(IUserMessageNotifier)
        if msg_notifier.notify(self.message):
            return PostCollectionView._process_request_data(self, data)


class UserMessagePutMemberView(PutMemberView):
    message = 'This is my member warning message'
    def _extract_request_data(self):
        reg = get_current_registry()
        msg_notifier = reg.getUtility(IUserMessageNotifier)
        msg_notifier.notify(self.message)
        return self.context

    def _process_request_data(self, data):
        return self._get_result(data)


class _ExtractDataExceptionViewMixin(object):
    def _extract_request_data(self):
        raise ValueError()


class _ProcessDataExceptionViewMixin(object):
    def _process_request_data(self, data): # pylint: disable=W0613
        raise ValueError()


class ExceptionPutMemberView(_ExtractDataExceptionViewMixin, PutMemberView):
    pass


class ExceptionPostCollectionView(_ProcessDataExceptionViewMixin,
                                  PutMemberView):
    pass
