"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 17, 2011.
"""
import os

from everest.constants import RequestMethods
from everest.mime import CSV_MIME
from everest.mime import CsvMime
from everest.mime import XmlMime
from everest.querying.specifications import eq
from everest.renderers import RendererFactory
from everest.resources.interfaces import IService
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import get_service
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.fixtures import create_entity_tree
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild
from everest.tests.simple_app.entities import FooEntity
from everest.tests.simple_app.interfaces import IFoo
from everest.tests.simple_app.resources import FooCollection
from everest.tests.simple_app.resources import FooMember
from everest.tests.simple_app.views import ExceptionPostCollectionView
from everest.tests.simple_app.views import ExceptionPutMemberView
from everest.tests.simple_app.views import UserMessagePostCollectionView
from everest.tests.simple_app.views import UserMessagePutMemberView
from everest.traversal import SuffixResourceTraverser
from everest.utils import get_repository_manager
from everest.views.getcollection import GetCollectionView
from everest.views.static import public_view
from everest.views.utils import accept_csv_only
from pkg_resources import resource_filename # pylint: disable=E0611
from pyramid.compat import bytes_
from pyramid.compat import native_
from pyramid.testing import DummyRequest
import pytest
import transaction


__docformat__ = 'reStructuredText en'
__all__ = ['TestClassicStyleConfiguredViews',
           'TestExceptionView',
           'TestGetCollectionView',
           'TestMessagingView',
           'TestNewStyleConfiguredViews',
           'TestPredicatedView',
           'TestStaticView',
           'TestViewBasicsMemory',
           'TestViewBasicsRdb',
           'TestWarningViewMemory',
           'TestWarningViewRdb',
           'TestWarningWithExceptionView',
           ]


@pytest.yield_fixture
def view_app_creator(app_creator):
    app_creator.config.add_resource_view(IMyEntity,
                                         renderer='csv',
                                         request_method=RequestMethods.GET)
    app_creator.config.add_member_view(IMyEntity,
                                       renderer='csv',
                                       request_method=RequestMethods.PUT)
    app_creator.config.add_member_view(IMyEntity,
                                       renderer='csv',
                                       request_method=RequestMethods.PATCH)
    app_creator.config.add_collection_view(IMyEntity,
                                           renderer='csv',
                                           request_method=RequestMethods.POST)
    app_creator.config.add_collection_view(IMyEntityChild,
                                           renderer='csv',
                                           request_method=RequestMethods.POST)
    app_creator.config.add_member_view(IMyEntity,
                                       renderer='csv',
                                       request_method=RequestMethods.DELETE)
    yield app_creator


@pytest.yield_fixture
def msg_view_app_creator(app_creator):
    app_creator.config.add_resource_view(IMyEntity,
                                         renderer='csv',
                                         request_method=RequestMethods.GET,
                                         enable_messaging=True)
    app_creator.config.add_member_view(IMyEntity,
                                       renderer='csv',
                                       request_method=RequestMethods.PATCH,
                                       enable_messaging=False)
    yield app_creator

@pytest.yield_fixture
def pred_view_app_creator(app_creator):
    app_creator.config.add_renderer('csv', RendererFactory)
    app_creator.config.add_view(context=get_collection_class(IMyEntity),
                                view=GetCollectionView,
                                renderer='csv',
                                request_method=RequestMethods.GET,
                                custom_predicates=(accept_csv_only,))
    yield app_creator


@pytest.fixture
def view_collection(app_creator): #pylint:disable=W0613
    my_entity1 = create_entity_tree(id=0, text='foo0')
    my_entity2 = create_entity_tree(id=1, text='too1')
    coll = get_root_collection(IMyEntity)
    coll.create_member(my_entity1)
    coll.create_member(my_entity2)
    return coll


@pytest.fixture
def view_member(view_collection): #pylint: disable=W0621
    view_collection.filter = eq(id=0)
    return next(iter(view_collection))


@pytest.yield_fixture
def trv_app_creator(app_creator):
    app_creator.config.add_traverser(SuffixResourceTraverser)
    yield app_creator


@pytest.fixture
def trv_view_member(app_creator): #pylint:disable=W0613
    foo_ent = FooEntity(id=0)
    coll = get_root_collection(IFoo)
    mb = coll.create_member(foo_ent)
    transaction.commit()
    return mb


@pytest.yield_fixture
def static_vw_app_creator(app_creator):
    app_creator.config.load_zcml(
                    'everest.tests.complete_app:configure_no_rdb.zcml')
    app_creator.config.add_view(context=IService,
                         view=public_view,
                         name='public',
                         request_method=RequestMethods.GET)
    fn = resource_filename('everest.tests.complete_app', 'data/original')
    app_creator.config.registry.settings['public_dir'] = fn
    yield app_creator


@pytest.yield_fixture
def exc_vw_app_creator(app_creator):
    app_creator.config.add_member_view(IMyEntity,
                                       view=ExceptionPutMemberView,
                                       request_method=RequestMethods.PUT)
    app_creator.config.add_collection_view(IMyEntity,
                                           view=ExceptionPostCollectionView,
                                           request_method=RequestMethods.POST)
    yield app_creator


@pytest.yield_fixture
def wrn_vw_app_creator(app_creator):
    repo_mgr = get_repository_manager()
    repo_mgr.initialize_all()
    app_creator.config.add_collection_view(FooCollection,
                                           view=UserMessagePostCollectionView,
                                           request_method=RequestMethods.POST)
    app_creator.config.add_member_view(FooMember,
                                       view=UserMessagePutMemberView,
                                       request_method=RequestMethods.PUT)
    yield app_creator


@pytest.yield_fixture
def wrn_with_exc_vw_app_creator(app_creator):
    app_creator.config.load_zcml(
                        'everest.tests.complete_app:configure_no_rdb.zcml')
    app_creator.config.add_view(context=get_collection_class(IMyEntity),
                                view=ExceptionPostCollectionView,
                                request_method=RequestMethods.POST)
    yield app_creator


# We make excessive use of local test fixtures here.
# pylint: disable=W0621


class _TestViewBase(object):
    package_name = 'everest.tests.complete_app'
    app_name = 'complete_app'
    path = '/my-entities/'

    def test_get_collection_defaults(self,
                                     view_app_creator): # pylint:disable=W0621
        res = view_app_creator.get(self.path, status=200)
        assert not res is None

    @pytest.mark.usefixtures('view_collection')
    def test_get_collection_with_slice_larger_max_size(self,
                                    view_app_creator): # pylint:disable=W0621
        res = view_app_creator.get(self.path,
                                   params=dict(size=10000), status=200)
        assert not res is None

    @pytest.mark.usefixtures('view_collection')
    def test_get_collection_with_invalid_slice_raises_error(self,
                                    view_app_creator): # pylint:disable=W0621
        res = view_app_creator.get(self.path,
                                   params=dict(size='foo'), status=500)
        assert not res is None

    @pytest.mark.usefixtures('view_collection')
    def test_get_collection_with_slice_size(self,
                                    view_app_creator): # pylint:disable=W0621
        res = view_app_creator.get(self.path, params=dict(size=1),
                                   status=200)
        assert not res is None

    @pytest.mark.usefixtures('view_collection')
    def test_get_collection_with_slice_start(self,
                                    view_app_creator): # pylint:disable=W0621
        res = view_app_creator.get(self.path,
                                   params=dict(start=1, size=1),
                                   status=200)
        assert not res is None

    @pytest.mark.usefixtures('view_collection')
    def test_get_collection_with_filter(self,
                                        view_app_creator): # pylint:disable=W0621
        res = view_app_creator.get(self.path,
                                   params=dict(q='id:equal-to:0'),
                                   status=200)
        assert not res is None

    @pytest.mark.usefixtures('view_collection')
    def test_get_collection_with_order(self,
                                       view_app_creator): # pylint:disable=W0621
        res = view_app_creator.get(self.path, params=dict(sort='id:asc'),
                                   status=200)
        assert not res is None

    @pytest.mark.usefixtures('view_collection')
    def test_get_collection_with_order_and_size(self,
                                    view_app_creator): # pylint:disable=W0621
        res = view_app_creator.get(self.path,
                                   params=dict(sort='id:asc', size=1),
                                   status=200)
        assert not res is None

    @pytest.mark.usefixtures('view_collection')
    def test_get_collection_with_refs_options(self,
                                    view_app_creator): # pylint:disable=W0621
        # The refs options are not processed by the renderers, so we need
        # a native everest view with a defined response MIME type.
        view_app_creator.config.add_resource_view(
                                    IMyEntity,
                                    default_response_content_type=CsvMime,
                                    request_method=RequestMethods.GET)
        res1 = view_app_creator.get(self.path, params=dict(refs='parent:OFF'),
                                    status=200)
        assert not res1 is None
        assert native_(res1.body).find(',"parent",') == -1
        assert native_(res1.body).find(',"parent.id",') == -1
        res2 = view_app_creator.get(self.path,
                                    params=dict(refs='parent:INLINE'),
                                    status=200)
        assert not res2 is None
        assert native_(res2.body).find(',"parent",') == -1
        assert native_(res2.body).find(',"parent.id",') != -1
        # Bogus refs parameters.
        view_app_creator.get(self.path, params=dict(refs='parent:XXX'),
                             status=500)

    @pytest.mark.usefixtures('view_collection')
    def test_get_member_default_content_type(self,
                                             view_app_creator): # pylint:disable=W0621
        res = view_app_creator.get("%s/0" % self.path, status=200)
        assert not res is None

    def test_put_member(self, view_app_creator, view_member): # pylint:disable=W0621
        req_body = b'"id","text","number"\n0,"abc",2\n'
        res = view_app_creator.put("%s/0" % self.path,
                                   params=req_body,
                                   content_type=CsvMime.mime_type_string,
                                   status=200)
        assert not res is None
        assert view_member.text == 'abc'
        assert view_member.number == 2
        req_body = b'"id","text","number"\n2,"abc",2\n'
        res = view_app_creator.put("%s/0" % self.path,
                                   params=req_body,
                                   content_type=CsvMime.mime_type_string,
                                   status=200)
        assert view_member.id == 2
        assert res.headers['Location'].endswith('2/')

    def test_patch_member(self, view_app_creator, view_member): # pylint:disable=W0621
        req_body = b'"number"\n2\n'
        res = view_app_creator.patch("%s/0" % self.path,
                             params=req_body,
                             content_type=CsvMime.mime_type_string,
                             status=200)
        assert not res is None
        assert view_member.number == 2
        req_body = b'"id"\n2\n'
        res = view_app_creator.patch("%s/0" % self.path,
                                     params=req_body,
                                     content_type=CsvMime.mime_type_string,
                                     status=200)
        assert view_member.id == 2
        assert res.headers['Location'].endswith('2/')

    def test_patch_member_with_xml(self,
                                   view_app_creator, view_member): # pylint:disable=W0621
        view_app_creator.config.add_member_view(IMyEntity,
                                         renderer='xml',
                                         request_method=RequestMethods.PATCH)
        req_body = \
            b'<tst:myentity xmlns:tst="http://xml.test.org/tests" id="0">' \
            b'    <tst:number>2</tst:number>' \
            b'</tst:myentity>'
        res = view_app_creator.patch("%s/0" % self.path,
                                     params=req_body,
                                     content_type=XmlMime.mime_type_string,
                                     status=200)
        assert not res is None
        assert view_member.number == 2

    @pytest.mark.usefixtures('view_collection')
    def test_post_nested_collection_no_parent(self, class_ini,
                                view_app_creator, view_member): # pylint:disable=W0621
        parent_url = "%s%s/0/" % (class_ini.app_url, self.path)
        req_body = b'"id","text"\n2,"child2"\n'
        res = view_app_creator.post("%schildren" % parent_url,
                                    params=req_body,
                                    content_type=CsvMime.mime_type_string,
                                    status=201)
        assert not res is None
        child_coll = get_root_collection(IMyEntityChild)
        child_mb = child_coll['2']
        assert child_mb.text == 'child2'
        assert child_mb.parent.id == view_member.id

    def test_delete_member(self, view_app_creator, view_collection): # pylint:disable=W0621
        assert len(view_collection) == 2
        res = view_app_creator.delete("%s/0" % self.path,
                                      content_type=CsvMime.mime_type_string,
                                      status=200)
        assert not res is None
        assert len(view_collection) == 1
        # Second delete triggers 404.
        view_app_creator.delete("%s/0" % self.path,
                                content_type=CsvMime.mime_type_string,
                                status=404)
        coll_cls = get_collection_class(IMyEntity)
        old_remove = coll_cls.__dict__.get('remove')
        def remove_with_exception(self): # pylint: disable=W0613
            raise RuntimeError()
        coll_cls.remove = remove_with_exception
        try:
            view_app_creator.delete("%s/1" % self.path,
                                    content_type=CsvMime.mime_type_string,
                                    status=500)
        finally:
            if not old_remove is None:
                coll_cls.remove = old_remove


class TestViewBasicsMemory(_TestViewBase):
    ini_file_path = resource_filename('everest.tests.complete_app',
                                      'complete_app.ini')

    def test_post_collection(self, view_app_creator): # pylint:disable=W0621
        # This only works in the memory backend because of the referential
        # constraint of the parent attribute.
        new_id = 0
        req_body = b'"id","text","number"\n%d,"abc",2\n' % new_id
        res = view_app_creator.post("%s" % self.path,
                                    params=req_body,
                                    content_type=CsvMime.mime_type_string,
                                    status=201)
        assert not res is None
        coll = get_root_collection(IMyEntity)
        mb = coll[str(new_id)]
        assert mb.text == 'abc'

    def test_post_collection_no_id(self,
                                   view_app_creator): # pylint:disable=W0621
        # This only works in the memory backend because of the referential
        # constraint of the parent attribute.
        req_body = b'"text","number"\n"abc",2\n'
        res = view_app_creator.post("%s" % self.path,
                                    params=req_body,
                                    content_type=CsvMime.mime_type_string,
                                    status=201)
        assert not res is None
        assert res.headers['Location'].endswith(self.path)
        assert native_(res.body).split(os.linesep)[1][:2] != '""'

    @pytest.mark.usefixtures('view_collection')
    def test_post_nested_collection(self, class_ini,
                                    view_app_creator, view_member): # pylint:disable=W0621
        # This only works in the memory backend because it tolerates adding
        # the same entity multiple times.
        child_coll = get_root_collection(IMyEntityChild)
        parent_url = "%s%s/0/" % (class_ini.app_url, self.path)
        req_text = '"id","text","parent"\n2,"child2","%s"\n' % parent_url
        res = view_app_creator.post("%schildren" % parent_url,
                                    params=bytes_(req_text, encoding='utf-8'),
                                    content_type=CsvMime.mime_type_string,
                                    status=201)
        assert not res is None
        child_mb = child_coll['2']
        assert child_mb.text == 'child2'
        assert child_mb.parent.id == view_member.id


@pytest.mark.usefixtures('rdb')
class TestViewBasicsRdb(_TestViewBase):
    ini_file_path = resource_filename('everest.tests.complete_app',
                                      'complete_app_rdb.ini')



class TestMessagingView(object):
    package_name = 'everest.tests.complete_app'
    ini_file_path = resource_filename('everest.tests.complete_app',
                                      'complete_app.ini')
    app_name = 'complete_app'
    path = '/my-entities/'

    def test_get_member_default_content_type(self, msg_view_app_creator): #pylint:disable=W0621
        coll = get_root_collection(IMyEntity)
        ent = MyEntity(id=0)
        coll.create_member(ent)
        res = msg_view_app_creator.get("%s/0" % self.path, status=200)
        assert not res is None

    def test_patch_member(self, msg_view_app_creator): #pylint:disable=W0621
        coll = get_root_collection(IMyEntity)
        ent = MyEntity(id=0)
        mb = coll.create_member(ent)
        assert mb.__name__ == '0'
        req_body = b'"number"\n2\n'
        res = msg_view_app_creator.patch("%s/0" % self.path,
                                         params=req_body,
                                         content_type=CsvMime.mime_type_string,
                                         status=200)
        assert not res is None


class TestPredicatedView(object):
    package_name = 'everest.tests.complete_app'
    ini_file_path = resource_filename('everest.tests.complete_app',
                                      'complete_app.ini')
    app_name = 'complete_app'
    path = '/my-entities'

    def test_csv_only(self, pred_view_app_creator): #pylint:disable=W0621
        # Without accept header, we get a 404.
        pred_view_app_creator.get(self.path, status=404)
        pred_view_app_creator.get(self.path,
                                  headers=dict(accept=CSV_MIME), status=200)


class _TestConfiguredViews(object):
    views_config_file_name = None
    package_name = 'everest.tests.simple_app'
    ini_file_path = resource_filename('everest.tests.simple_app',
                                      'simple_app_views.ini')
    app_name = 'simple_app'
    path = '/foos'

    params = ('suffix,expected,end',
              [('csv', b'"id"', False),
               ('json', b'[{"id": 0', False),
               ('xml', b'</foos>', True)])

    @pytest.mark.usefixtures('trv_view_member')
    @pytest.mark.parametrize('template,' + params[0],
                             [('%s.%s',) + args
                              for args in params[1]] + # pylint: disable=E0602
                             [('%s/@@%s',) + args
                              for args in params[1]]) # pylint: disable=E0602
    def test_with_suffix(self, trv_app_creator, template,
                         suffix, expected, end):
        res = trv_app_creator.get(template % (self.path, suffix), status=200)
        if not end:
            assert res.body[:len(expected)] == expected
        else:
            assert res.body.strip()[-len(expected):] == expected
        # Fail for non-existing collection.
        trv_app_creator.get('/bars.csv', status=404)

    def test_custom_view_with_interface_raises_error(self, app_creator):
        with pytest.raises(ValueError):
            app_creator.config.add_resource_view(IFoo,
                                                 view=lambda context,
                                                 request: None)


class TestClassicStyleConfiguredViews(_TestConfiguredViews):
    config_file_name = 'everest.tests.simple_app:configure_views_classic.zcml'

    def test_default(self, app_creator):
        # No default - triggers a 404.
        app_creator.get(self.path, status=404)


class TestNewStyleConfiguredViews(_TestConfiguredViews):
    config_file_name = 'everest.tests.simple_app:configure_views.zcml'

    def test_default(self, app_creator):
        # New style views return the default_content_type.
        res = app_creator.get(self.path, status=200)
        assert res.body.startswith(b'<?xml')

    def test_custom_view(self, app_creator):
        TXT = b'my custom response body'
        def custom_view(context, request): # context unused pylint: disable=W0613
            request.response.body = TXT
            return request.response
        app_creator.config.add_collection_view(IFoo,
                                               view=custom_view, name='custom')
        res = app_creator.get('/foos/@@custom')
        assert res.body == TXT

    def test_invalid_accept_header(self, app_creator):
        app_creator.get(self.path,
                        headers=dict(accept='application/foobar'),
                        status=406)

    def test_star_star_accept_header(self, app_creator):
        app_creator.get(self.path,
                        headers=dict(accept='*/*'),
                        status=200)

    def test_invalid_request_content_type(self, app_creator):
        app_creator.config.add_collection_view(IFoo,
                                               request_method=
                                                    RequestMethods.POST)
        app_creator.post(self.path,
                         params='foobar',
                         content_type='application/foobar',
                         status=415)

    @pytest.mark.usefixtures('trv_view_member')
    def test_fake_put_view(self, app_creator):
        app_creator.config.add_member_view(IFoo,
                                           request_method=
                                                RequestMethods.FAKE_PUT)
        req_body = '"id"\n0'
        app_creator.post("%s/0" % self.path,
                         params=req_body,
                         content_type=CsvMime.mime_type_string,
                         headers={'X-HTTP-Method-Override' :
                                                RequestMethods.PUT},
                         status=200)

    @pytest.mark.usefixtures('trv_view_member')
    def test_fake_patch_view(self, app_creator):
        app_creator.config.add_member_view(IFoo,
                                           request_method=
                                                RequestMethods.FAKE_PATCH)
        req_body = '"id"\n0'
        app_creator.post("%s/0" % self.path,
                         params=req_body,
                         content_type=CsvMime.mime_type_string,
                         headers={'X-HTTP-Method-Override' :
                                                RequestMethods.PATCH},
                         status=200)

    @pytest.mark.usefixtures('trv_view_member')
    def test_fake_delete_view(self, app_creator):
        app_creator.config.add_member_view(IFoo,
                                           request_method=
                                                RequestMethods.FAKE_DELETE)
        app_creator.post("%s/0" % self.path,
                         headers=
                            {'X-HTTP-Method-Override' : RequestMethods.DELETE},
                         status=200)

    def test_add_collection_view_with_put_fails(self, app_creator):
        with pytest.raises(ValueError) as cm:
            app_creator.config.add_collection_view(IFoo,
                                                   request_method=
                                                        RequestMethods.PUT)
        assert str(cm.value).startswith('Autodetection')

    def test_add_member_view_with_post_fails(self, app_creator):
        with pytest.raises(ValueError) as cm:
            app_creator.config.add_member_view(IFoo,
                                               request_method=
                                                        RequestMethods.POST)
        assert str(cm.value).startswith('Autodetection')


class TestGetCollectionView(object):
    package_name = 'everest.tests.simple_app'
    config_file_name = 'configure.zcml'
    ini_file_path = resource_filename('everest.tests.simple_app',
                                      'simple_app_views.ini')

    def test_get_collection_view_with_size(self, class_ini, app_creator):
        coll = get_root_collection(IFoo)
        path_url = 'http://0.0.0.0:6543/foos/'
        req = DummyRequest(application_url=class_ini.app_url,
                           host_url=class_ini.app_url,
                           path_url=path_url,
                           url=path_url + '?size=10',
                           params=dict(size=10),
                           registry=app_creator.config.registry,
                           accept=['*/*'])
        req.get_response = lambda exc: None
        view = GetCollectionView(coll, req)
        res = view()
        assert res is not None
        assert view.context.slice.start == 0
        assert view.context.slice.stop == 10
        # Try again with size exceeding the allowed maximum limit (page size).
        req.params = dict(size=10000)
        req.url = path_url + '?size=10000'
        res = view()
        assert res is not None
        assert view.context.slice.start == 0
        assert view.context.slice.stop == FooCollection.max_limit


class TestStaticView(object):
    package_name = 'everest.tests.complete_app'
    ini_file_path = resource_filename('everest.tests.complete_app',
                                      'complete_app.ini')
    app_name = 'complete_app'


    def test_access_public_dir(self, static_vw_app_creator):
        static_vw_app_creator.get('/public/myentity-collection.csv', status=200)


class TestExceptionView(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'everest.tests.complete_app:configure_no_rdb.zcml'
    ini_file_path = resource_filename('everest.tests.complete_app',
                                      'complete_app.ini')
    app_name = 'complete_app'
    path = '/my-entities'

    def test_put_member_raises_error(self, exc_vw_app_creator):
        coll = get_root_collection(IMyEntity)
        ent = MyEntity(id=0)
        coll.create_member(ent)
        exc_vw_app_creator.put("%s/0" % self.path,
                               params='dummy body',
                               status=500)

    def test_post_collection_raises_error(self, exc_vw_app_creator):
        req_body = '"id","text","number"\n0,"abc",2\n'
        exc_vw_app_creator.post("%s" % self.path,
                                params=req_body,
                                content_type=CsvMime.mime_type_string,
                                status=500)


class _TestWarningViewBase(object):
    package_name = 'everest.tests.simple_app'
    ini_file_path = resource_filename('everest.tests.simple_app',
                                      'simple_app_views.ini')
    app_name = 'simple_app'
    path = '/foos'
    config_file_name = None

    def test_post_collection_empty_body(self, wrn_vw_app_creator):
        res = wrn_vw_app_creator.post(self.path, params='',
                            status=400)
        assert res is not None

    @pytest.mark.parametrize('path', [path, '/foos?q=id=0'])
    def test_post_collection_warning_exception(self, wrn_vw_app_creator, path):
        # First POST - get back a 307.
        res1 = wrn_vw_app_creator.post(path, params='foo name',
                                       status=307)
        body_text = native_(res1.body.rstrip(), encoding='utf-8')
        assert body_text.endswith(UserMessagePostCollectionView.message)
        assert res1.body.startswith(b'307 Temporary Redirect')
        # Second POST to redirection location - get back a 201.
        resubmit_location1 = res1.headers['Location']
        res2 = wrn_vw_app_creator.post(resubmit_location1,
                             params='foo name',
                             status=201)
        assert not res2 is None
        # Third POST to same redirection location with different warning
        # message triggers a 307 again.
        old_msg = UserMessagePostCollectionView.message
        UserMessagePostCollectionView.message = old_msg[::-1]
        try:
            res3 = wrn_vw_app_creator.post(resubmit_location1,
                                 params='foo name',
                                 status=307)
            assert res3.body.startswith(b'307 Temporary Redirect')
            # Fourth POST to new redirection location - get back a 409 (since
            # the second POST from above went through).
            resubmit_location2 = res3.headers['Location']
            res4 = wrn_vw_app_creator.post(resubmit_location2,
                                 params='foo name',
                                 status=409)
            assert not res4 is None
        finally:
            UserMessagePostCollectionView.message = old_msg

    def test_put_member_warning_exception(self, wrn_vw_app_creator):
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
        res1 = wrn_vw_app_creator.put(path,
                            params='foo name',
                            status=307)
        assert res1.body.startswith(b'307 Temporary Redirect')
        # Second PUT to redirection location - get back a 200.
        resubmit_location1 = res1.headers['Location']
        res2 = wrn_vw_app_creator.put(resubmit_location1, params='foo name',
                            status=200)
        assert not res2 is None


class TestWarningViewMemory(_TestWarningViewBase):
    config_file_name = \
            'everest.tests.simple_app:configure_messaging_memory.zcml'


@pytest.mark.usefixtures('rdb')
class TestWarningViewRdb(_TestWarningViewBase):
    config_file_name = 'everest.tests.simple_app:configure_messaging_rdb.zcml'



class TestWarningWithExceptionView(object):
    package_name = 'everest.tests.complete_app'
    ini_file_path = resource_filename('everest.tests.complete_app',
                                      'complete_app.ini')
    app_name = 'complete_app'
    path = '/my-entities'

    def test_post_collection_raises_error(self, wrn_with_exc_vw_app_creator):
        req_body = '"id","text","number"\n0,"abc",2\n'
        wrn_with_exc_vw_app_creator.post("%s" % self.path,
                                         params=req_body,
                                         content_type=
                                                CsvMime.mime_type_string,
                                         status=500)

# pylint: enable=W0621
