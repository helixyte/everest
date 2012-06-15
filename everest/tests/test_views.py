"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 17, 2011.
"""
from everest.messaging import IUserMessageEvent
from everest.messaging import IUserMessageEventNotifier
from everest.messaging import UserMessageEventNotifier
from everest.messaging import UserMessageHandler
from everest.mime import CsvMime
from everest.renderers import RendererFactory
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import get_service
from everest.testing import FunctionalTestCase
from everest.tests.testapp.entities import FooEntity
from everest.tests.testapp.resources import FooCollection
from everest.tests.testapp.resources import FooMember
from everest.tests.testapp.views import DummyUserMessageAndExceptionView
from everest.tests.testapp.views import ExceptionPostCollectionView
from everest.tests.testapp.views import ExceptionPutMemberView
from everest.tests.testapp.views import UserMessagePostCollectionView
from everest.tests.testapp.views import UserMessagePutMemberView
from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.testing import create_collection
from everest.views.getcollection import GetCollectionView
from everest.views.getmember import GetMemberView
from everest.views.postcollection import PostCollectionView
from everest.views.putmember import PutMemberView
from pkg_resources import resource_filename # pylint: disable=E0611
import transaction

__docformat__ = 'reStructuredText en'
__all__ = ['BasicViewsTestCase',
           'WarningViewsTestCase',
           ]


class BasicViewTestCase(FunctionalTestCase):
    package_name = 'everest.tests.testapp_db'
    ini_file_path = resource_filename('everest.tests.testapp_db',
                                      'testapp.ini')
    app_name = 'testapp_db'
    path = '/my-entities'

    def set_up(self):
        FunctionalTestCase.set_up(self)
        self.config.load_zcml('everest.tests.testapp_db:configure_rpr.zcml')
        self.config.add_renderer('csv', RendererFactory)
        self.config.add_view(context=get_member_class(IMyEntity),
                             view=GetMemberView,
                             renderer='csv',
                             request_method='GET')
        self.config.add_view(context=get_collection_class(IMyEntity),
                             view=GetCollectionView,
                             renderer='csv',
                             request_method='GET')
        self.config.add_view(context=get_member_class(IMyEntity),
                             view=PutMemberView,
                             renderer='csv',
                             request_method='PUT')
        self.config.add_view(context=get_collection_class(IMyEntity),
                             view=PostCollectionView,
                             renderer='csv',
                             request_method='POST')

    def test_get_collection_defaults(self):
        res = self.app.get(self.path, status=200)
        self.assert_is_not_none(res)

    def test_get_collection_with_slice_larger_max_size(self):
        create_collection()
        res = self.app.get(self.path, params=dict(size=10000), status=200)
        self.assert_is_not_none(res)

    def test_get_collection_with_invalid_slice_raises_error(self):
        create_collection()
        res = self.app.get(self.path, params=dict(size='foo'), status=500)
        self.assert_is_not_none(res)

    def test_get_collection_with_slice_size(self):
        create_collection()
        res = self.app.get(self.path, params=dict(size=1),
                           status=200)
        self.assert_is_not_none(res)

    def test_get_collection_with_slice_start(self):
        create_collection()
        res = self.app.get(self.path, params=dict(start=1, size=1),
                           status=200)
        self.assert_is_not_none(res)

    def test_get_collection_with_filter(self):
        create_collection()
        res = self.app.get(self.path, params=dict(q='id:equal-to:0'),
                           status=200)
        self.assert_is_not_none(res)

    def test_get_collection_with_order(self):
        create_collection()
        res = self.app.get(self.path, params=dict(sort='id:asc'),
                           status=200)
        self.assert_is_not_none(res)

    def test_get_member_default_content_type(self):
        coll = get_root_collection(IMyEntity)
        ent = MyEntity(id=0)
        coll.create_member(ent)
        res = self.app.get("%s/0" % self.path, status=200)
        self.assert_is_not_none(res)

    def test_put_member(self):
        coll = get_root_collection(IMyEntity)
        ent = MyEntity(id=0)
        mb = coll.create_member(ent)
        self.assert_equal(mb.__name__, '0')
        req_body = '"id","text","number"\n1,"abc",2\n'
        res = self.app.put("%s/0" % self.path,
                           params=req_body,
                           content_type=CsvMime.mime_string,
                           status=200)
        self.assert_is_not_none(res)
        mb = iter(coll).next()
        self.assert_equal(mb.__name__, '1')
        self.assert_equal(mb.text, 'abc')

    def test_post_collection(self):
        req_body = '"id","text","number"\n0,"abc",2\n'
        res = self.app.post("%s" % self.path,
                            params=req_body,
                            content_type=CsvMime.mime_string,
                            status=201)
        self.assert_is_not_none(res)
        coll = get_root_collection(IMyEntity)
        mb = coll['0']
        self.assert_equal(mb.text, 'abc')


class ExceptionViewTestCase(FunctionalTestCase):
    package_name = 'everest.tests.testapp_db'
    ini_file_path = resource_filename('everest.tests.testapp_db',
                                      'testapp.ini')
    app_name = 'testapp_db'
    path = '/my-entities'

    def set_up(self):
        FunctionalTestCase.set_up(self)
        self.config.load_zcml(
                        'everest.tests.testapp_db:configure_no_orm.zcml')
        self.config.add_view(context=get_member_class(IMyEntity),
                             view=ExceptionPutMemberView,
                             request_method='PUT')
        self.config.add_view(context=get_collection_class(IMyEntity),
                             view=ExceptionPostCollectionView,
                             request_method='POST')

    def test_put_member_raises_error(self):
        coll = get_root_collection(IMyEntity)
        ent = MyEntity(id=0)
        coll.create_member(ent)
        self.app.put("%s/0" % self.path,
                     params='dummy body',
                     status=500)

    def test_post_collection_raises_error(self):
        req_body = '"id","text","number"\n0,"abc",2\n'
        self.app.post("%s" % self.path,
                     params=req_body,
                     content_type=CsvMime.mime_string,
                     status=500)


class WarningViewTestCase(FunctionalTestCase):
    package_name = 'everest.tests.testapp'
    ini_file_path = resource_filename('everest.tests.testapp',
                                      'testapp_views.ini')
    app_name = 'testapp'
    path = '/foos'

    def set_up(self):
        FunctionalTestCase.set_up(self)
        self.config.load_zcml('everest.tests.testapp:configure_views.zcml')
        reg = self.config.registry
        reg.registerUtility(UserMessageEventNotifier(), # pylint:disable=E1103
                            IUserMessageEventNotifier)
        reg.registerHandler(UserMessageHandler.handle_user_message_event,
                            required=(IUserMessageEvent,))
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
        res1 = self.app.post(self.path, params='foo name',
                             status=307)
        self.assert_true(res1.body.startswith('307 Temporary Redirect'))
        # Second POST to redirection location - get back a 201.
        resubmit_location1 = res1.headers['Location']
        res2 = self.app.post(resubmit_location1,
                             params='foo name',
                             status=201)
        self.assert_true(not res2 is None)
        # Third POST to same redirection location with different warning
        # message triggers a 307 again.
        old_msg = UserMessagePostCollectionView.message
        UserMessagePostCollectionView.message = old_msg[::-1]
        try:
            res3 = self.app.post(resubmit_location1,
                                 params='foo name',
                                 status=307)
            self.assert_true(
                    res3.body.startswith('307 Temporary Redirect'))
            # Fourth POST to new redirection location - get back a 409 (since
            # the second POST from above went through).
            resubmit_location2 = res3.headers['Location']
            res4 = self.app.post(resubmit_location2,
                                 params='foo name',
                                 status=409)
            self.assert_true(not res4 is None)
        finally:
            UserMessagePostCollectionView.message = old_msg

    def test_post_collection_warning_exception_with_query_string(self):
        old_path = self.path
        self.path = '/foos?q=id=0'
        try:
            self.test_post_collection_warning_exception()
        finally:
            self.path = old_path

    def test_put_member_warning_exception(self):
        root = get_service()
        # Need to start the service manually - no request root has been set 
        # yet.
        root.start()
        coll = root['foos']
        mb = FooMember(FooEntity(id=0))
        coll.add(mb)
        transaction.commit()
        path = '/'.join((self.path, '0'))
        # First PUT - get back a 307.
        res1 = self.app.put(path,
                            params='foo name',
                            status=307)
        self.assert_true(
                    res1.body.startswith('307 Temporary Redirect'))
        # Second PUT to redirection location - get back a 200.
        resubmit_location1 = res1.headers['Location']
        res2 = self.app.put(resubmit_location1, params='foo name',
                            status=200)
        self.assert_true(not res2 is None)


class WarningWithExceptionViewTestCase(FunctionalTestCase):
    package_name = 'everest.tests.testapp_db'
    ini_file_path = resource_filename('everest.tests.testapp_db',
                                      'testapp.ini')
    app_name = 'testapp_db'
    path = '/my-entities'

    def set_up(self):
        FunctionalTestCase.set_up(self)
        self.config.load_zcml(
                        'everest.tests.testapp_db:configure_no_orm.zcml')
        self.config.add_view(context=get_collection_class(IMyEntity),
                             view=DummyUserMessageAndExceptionView,
                             request_method='POST')

    def test_post_collection_raises_error(self):
        req_body = '"id","text","number"\n0,"abc",2\n'
        self.app.post("%s" % self.path,
                     params=req_body,
                     content_type=CsvMime.mime_string,
                     status=500)
