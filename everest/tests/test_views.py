"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 17, 2011.
"""
from everest.mime import CSV_MIME
from everest.mime import CsvMime
from everest.orm import reset_metadata
from everest.renderers import RendererFactory
from everest.resources.interfaces import IService
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import get_service
from everest.testing import FunctionalTestCase
from everest.tests.testapp.entities import FooEntity
from everest.tests.testapp.interfaces import IFoo
from everest.tests.testapp.resources import FooCollection
from everest.tests.testapp.resources import FooMember
from everest.tests.testapp.views import ExceptionPostCollectionView
from everest.tests.testapp.views import ExceptionPutMemberView
from everest.tests.testapp.views import UserMessagePostCollectionView
from everest.tests.testapp.views import UserMessagePutMemberView
from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.testing import create_collection
from everest.traversal import SuffixResourceTraverser
from everest.utils import get_repository_manager
from everest.views.getcollection import GetCollectionView
from everest.views.static import public_view
from everest.views.utils import accept_csv_only
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
        self.config.add_resource_view(IMyEntity,
                                      renderer='csv',
                                      request_method='GET')
        self.config.add_member_view(IMyEntity,
                                    renderer='csv',
                                    request_method='PUT')
        self.config.add_collection_view(IMyEntity,
                                        renderer='csv',
                                        request_method='POST')
        self.config.add_member_view(IMyEntity,
                                    renderer='csv',
                                    request_method='DELETE')

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

    def test_get_collection_with_order_and_size(self):
        create_collection()
        res = self.app.get(self.path, params=dict(sort='id:asc', size=1),
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
                           content_type=CsvMime.mime_type_string,
                           status=200)
        self.assert_is_not_none(res)
        mb = iter(coll).next()
        self.assert_equal(mb.__name__, '1')
        self.assert_equal(mb.text, 'abc')

    def test_post_collection(self):
        req_body = '"id","text","number"\n0,"abc",2\n'
        res = self.app.post("%s" % self.path,
                            params=req_body,
                            content_type=CsvMime.mime_type_string,
                            status=201)
        self.assert_is_not_none(res)
        coll = get_root_collection(IMyEntity)
        mb = coll['0']
        self.assert_equal(mb.text, 'abc')

    def test_delete_member(self):
        coll = create_collection()
        self.assert_equal(len(coll), 2)
        res = self.app.delete("%s/0" % self.path,
                              content_type=CsvMime.mime_type_string,
                              status=200)
        self.assert_is_not_none(res)
        self.assert_equal(len(coll), 1)
        # Second delete triggers 404.
        self.app.delete("%s/0" % self.path,
                        content_type=CsvMime.mime_type_string,
                        status=404)
        coll_cls = get_collection_class(IMyEntity)
        old_remove = coll_cls.__dict__.get('remove')
        def remove_with_exception(self): # pylint: disable=W0613
            raise RuntimeError()
        coll_cls.remove = remove_with_exception
        try:
            self.app.delete("%s/1" % self.path,
                            content_type=CsvMime.mime_type_string,
                            status=500)
        finally:
            if not old_remove is None:
                coll_cls.remove = old_remove


class PredicatedViewTestCase(FunctionalTestCase):
    package_name = 'everest.tests.testapp_db'
    ini_file_path = resource_filename('everest.tests.testapp_db',
                                      'testapp.ini')
    app_name = 'testapp_db'
    path = '/my-entities'
    def set_up(self):
        FunctionalTestCase.set_up(self)
        self.config.load_zcml('everest.tests.testapp_db:configure_rpr.zcml')
        self.config.add_renderer('csv', RendererFactory)
        self.config.add_view(context=get_collection_class(IMyEntity),
                             view=GetCollectionView,
                             renderer='csv',
                             request_method='GET',
                             custom_predicates=(accept_csv_only,))

    def test_csv_only(self):
        # Without accept header, we get a 404.
        self.app.get(self.path, status=404)
        self.app.get(self.path, headers=dict(accept=CSV_MIME), status=200)


class _ConfiguredViewsTestCase(FunctionalTestCase):
    views_config_file_name = None

    package_name = 'everest.tests.testapp'
    ini_file_path = resource_filename('everest.tests.testapp',
                                      'testapp_views.ini')
    app_name = 'testapp'
    path = '/foos'

    def set_up(self):
        FunctionalTestCase.set_up(self)
        self.config.load_zcml(self.views_config_file_name)
        coll = get_root_collection(IFoo)
        coll.create_member(FooEntity(id=0))
        transaction.commit()

    def test_with_suffix(self):
        self._test_with_view_name(
                            lambda path, suffix: "%s.%s" % (path, suffix))

    def test_with_at_at(self):
        self._test_with_view_name(
                            lambda path, suffix: "%s/@@%s" % (path, suffix))

    def test_custom_view_with_interface_raises_error(self):
        self.assert_raises(ValueError,
                           self.config.add_resource_view, IFoo,
                           view=lambda context, request: None)

    def _test_with_view_name(self, path_fn):
        # Use suffix traverser as default.
        self.config.add_traverser(SuffixResourceTraverser)
        for sfx, fn in (('csv', lambda body: body.startswith('"id"')),
                        ('json', lambda body: body.startswith('[{"id": 0')),
                        ('xml', lambda body: body.strip().endswith('</foos>'))
                        ):
            res = self.app.get(path_fn(self.path, sfx), status=200)
            self.assert_true(fn(res.body))
        # Fail for non-existing collection.
        self.app.get('/bars.csv', status=404)


class ClassicStyleConfiguredViewsTestCase(_ConfiguredViewsTestCase):
    views_config_file_name = \
                    'everest.tests.testapp:configure_views_classic.zcml'

    def test_default(self):
        # No default - triggers a 404.
        self.app.get(self.path, status=404)


class NewStyleConfiguredViewsTestCase(_ConfiguredViewsTestCase):
    views_config_file_name = \
                'everest.tests.testapp:configure_views.zcml'

    def test_default(self):
        # New style views return the default_content_type.
        res = self.app.get(self.path, status=200)
        self.assert_true(res.body.startswith('"id"'))

    def test_custom_view(self):
        TXT = 'my custom response body'
        def custom_view(context, request): # context unused pylint: disable=W0613
            request.response.body = TXT
            return request.response
        self.config.add_collection_view(IFoo, view=custom_view, name='custom')
        res = self.app.get('/foos/@@custom')
        self.assert_equal(res.body, TXT)

    def test_invalid_accept_header(self):
        self.app.get(self.path,
                     headers=dict(accept='application/foobar'),
                     status=406)

    def test_invalid_request_content_type(self):
        self.config.add_collection_view(IFoo, request_method='POST')
        self.app.post(self.path,
                      params='foobar',
                      content_type='application/foobar',
                      status=415)


class StaticViewTestCase(FunctionalTestCase):
    package_name = 'everest.tests.testapp_db'
    ini_file_path = resource_filename('everest.tests.testapp_db',
                                      'testapp.ini')
    app_name = 'testapp_db'
    def set_up(self):
        FunctionalTestCase.set_up(self)
        self.config.load_zcml('everest.tests.testapp_db:configure_no_orm.zcml')
        self.config.add_view(context=IService,
                             view=public_view,
                             name='public',
                             request_method='GET')
        fn = resource_filename('everest.tests.testapp_db', 'data/original')
        self.config.registry.settings['public_dir'] = fn

    def test_access_public_dir(self):
        self.app.get('/public/myentity-collection.csv', status=200)


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
        self.config.add_member_view(IMyEntity,
                                    view=ExceptionPutMemberView,
                                    request_method='PUT')
        self.config.add_collection_view(IMyEntity,
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
                     content_type=CsvMime.mime_type_string,
                     status=500)


class _WarningViewBaseTestCase(FunctionalTestCase):
    package_name = 'everest.tests.testapp'
    ini_file_path = resource_filename('everest.tests.testapp',
                                      'testapp_views.ini')
    app_name = 'testapp'
    path = '/foos'
    config_file_name = None

    def set_up(self):
        FunctionalTestCase.set_up(self)
        self.config.load_zcml(self.config_file_name)
        self.config.add_collection_view(FooCollection,
                                        view=UserMessagePostCollectionView,
                                        request_method='POST')
        self.config.add_member_view(FooMember,
                                    view=UserMessagePutMemberView,
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


class WarningViewMemoryTestCase(_WarningViewBaseTestCase):
    config_file_name = 'everest.tests.testapp:configure_messaging_memory.zcml'


class WarningViewOrmTestCase(_WarningViewBaseTestCase):
    config_file_name = 'everest.tests.testapp:configure_messaging_orm.zcml'

    def set_up(self):
        _WarningViewBaseTestCase.set_up(self)
        repo_mgr = get_repository_manager()
        repo_mgr.initialize_all()

    @classmethod
    def tear_down_class(cls):
        reset_metadata()


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
                             view=ExceptionPostCollectionView,
                             request_method='POST')

    def test_post_collection_raises_error(self):
        req_body = '"id","text","number"\n0,"abc",2\n'
        self.app.post("%s" % self.path,
                     params=req_body,
                     content_type=CsvMime.mime_type_string,
                     status=500)
