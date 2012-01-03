"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 17, 2011.
"""

from everest.messaging import IUserMessageEventNotifier
from everest.messaging import UserMessageEventNotifier
from everest.messaging import UserMessageHandler
from everest.resources.interfaces import IService
from everest.testing import FunctionalTestCase
from everest.tests.testapp import TestApp
from everest.tests.testapp.entities import FooEntity
from everest.tests.testapp.resources import FooCollection
from everest.tests.testapp.resources import FooMember
from everest.tests.testapp.views import UserMessagePostCollectionView
from everest.tests.testapp.views import UserMessagePutMemberView
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ViewsTestCase',
           ]


class ViewsTestCase(FunctionalTestCase):
    test_app_cls = TestApp

    path = '/foos'

    def _custom_configure(self):
        self.config.load_zcml('everest.tests.testapp:configure_views.zcml')

    def test_get_collection_default_content_type(self):
        res = self.app.get(self.path, status=200)
        self.assert_false(res is None)


class WarningViewsTestCase(ViewsTestCase):
    def _custom_configure(self):
        ViewsTestCase._custom_configure(self)
        reg = self.config.registry
        reg.registerUtility(UserMessageEventNotifier(), # pylint:disable=E1103
                            IUserMessageEventNotifier)
        reg.registerHandler(UserMessageHandler.handle_user_message_event)
        self.config.add_view(context=FooCollection,
                             view=UserMessagePostCollectionView,
                             renderer='csv',
                             request_method='POST')
        self.config.add_view(context=FooMember,
                             view=UserMessagePutMemberView,
                             renderer='csv',
                             request_method='PUT')

    def test_post_collection_empty_body(self):
        res = self.app.post(self.path, params='',
                            status=400)
        self.assert_false(res is None)

    def test_post_collection_warning_exception(self):
        # First POST - get back a 307.
        res1 = self.app.post(self.path, params='foo body',
                             status=307)
        self.assert_true(
                    res1.body.startswith('307 Temporary Redirect'))
        # Second POST to redirection location - get back a 201.
        resubmit_location1 = res1.headers['Location']
        res2 = self.app.post(resubmit_location1,
                             params='foo body',
                             status=201)
        self.assert_true(not res2 is None)
        # Third POST to same redirection location with different warning
        # message triggers a 307 again.
        old_msg = UserMessagePostCollectionView.message
        UserMessagePostCollectionView.message = old_msg[::-1]
        try:
            res3 = self.app.post(resubmit_location1,
                                 params='foo body',
                                 status=307)
            self.assert_true(
                    res3.body.startswith('307 Temporary Redirect'))
            # Fourth POST to new redirection location - get back a 409 (since
            # the second POST from above went through).
            resubmit_location2 = res3.headers['Location']
            res4 = self.app.post(resubmit_location2,
                                 params='foo body',
                                 status=409)
            self.assert_true(not res4 is None)
        finally:
            UserMessagePostCollectionView.message = old_msg

    def test_put_member_warning_exception(self):
        root = get_utility(IService)
        root.start()
        coll = root['foos']
        coll.add(FooMember(FooEntity(id=0)))
        path = '/'.join((self.path, '0'))
        # First PUT - get back a 307.
        res1 = self.app.put(path, params='foo body',
                            status=307)
        self.assert_true(
                    res1.body.startswith('307 Temporary Redirect'))
        # Second PUT to redirection location - get back a 201.
        resubmit_location1 = res1.headers['Location']
        res2 = self.app.put(resubmit_location1, params='foo body',
                            status=200)
        self.assert_true(not res2 is None)
