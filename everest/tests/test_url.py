"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from pyramid.compat import urlparse
import pytest

from everest.resources.utils import resource_to_url
from everest.resources.utils import url_to_resource
from everest.tests.complete_app.interfaces import IMyEntityParent
from everest.tests.complete_app.resources import MyEntityMember
from everest.resources.service import Service


__docformat__ = 'reStructuredText en'
__all__ = ['TestUrlNoRdb',
           'TestUrlRdb',
           ]


@pytest.mark.usefixtures("collection")
class _TestUrl(object):
    package_name = 'everest.tests.complete_app'
    app_url = 'http://0.0.0.0:6543'
    base_url = '%s/my-entities/' % app_url

    def test_resource_to_url_non_resource_object(self, member):
        ent = member.get_entity()
        with pytest.raises(TypeError) as cm:
            resource_to_url(ent)
        exc_msg = 'Can not generate URL for non-resource'
        assert str(cm.value).startswith(exc_msg)

    def test_resource_to_url_floating_member(self, member):
        ent = member.get_entity()
        mb = MyEntityMember.create_from_entity(ent)
        with pytest.raises(ValueError) as cm:
            resource_to_url(mb)
        exc_msg = 'Can not generate URL for floating resource'
        assert str(cm.value).startswith(exc_msg)

    def test_resource_to_url_member(self, member):
        self.__check_url(resource_to_url(member),
                         schema='http', path='/my-entities/0/', params='',
                         query='')

    def test_resource_to_url_collection(self, collection):
        self.__check_url(resource_to_url(collection),
                         schema='http', path='/my-entities/', params='',
                         query='')

    def test_resource_to_url_with_slice(self, collection):
        collection.slice = slice(0, 1)
        self.__check_url(resource_to_url(collection),
                         schema='http', path='/my-entities/',
                         params='', query='start=0&size=1')

    def test_resource_to_url_with_id_filter(self, collection,
                                            filter_specification_factory):
        flt_spec = filter_specification_factory.create_equal_to('id', 0)
        collection.filter = flt_spec
        self.__check_url(resource_to_url(collection),
                         schema='http', path='/my-entities/', params='',
                         query='q=id:equal-to:0')

    def test_resource_to_url_with_resource_filter(self, resource_repo,
                                                  collection,
                                                filter_specification_factory):
        parent_coll = resource_repo.get_collection(IMyEntityParent)
        parent = parent_coll['0']
        parent_url = resource_to_url(parent)
        flt_spec = \
            filter_specification_factory.create_equal_to('parent', parent)
        collection.filter = flt_spec
        self.__check_url(resource_to_url(collection),
                         schema='http', path='/my-entities/', params='',
                         query='q=parent:equal-to:"%s"' % parent_url)

    def test_resource_to_url_with_order(self, collection,
                                        order_specification_factory):
        ord_spec = order_specification_factory.create_ascending('id')
        collection.order = ord_spec
        self.__check_url(resource_to_url(collection),
                         schema='http', path='/my-entities/', params='',
                         query='sort=id:asc')

    def test_resource_to_url_with_multiple_order(self,
                                                 collection,
                                                 order_specification_factory):
        ord_spec_id = order_specification_factory.create_ascending('id')
        ord_spec_text = order_specification_factory.create_descending('text')
        ord_spec = \
            order_specification_factory.create_conjunction(ord_spec_id,
                                                           ord_spec_text)
        collection.order = ord_spec
        self.__check_url(resource_to_url(collection),
                         schema='http', path='/my-entities/', params='',
                         query='sort=id:asc~text:desc')

    def test_resource_to_url_nested(self, member, resource_repo):
        child_root_coll = resource_repo.get_collection(type(member.children))
        srvc = child_root_coll.__parent__
        resource_repo.set_collection_parent(child_root_coll, None)
        try:
            coll = member.children
            coll_url = resource_to_url(coll)
            self.__check_url(coll_url, path='/my-entities/0/children/',
                             query='')
            mb = coll['0']
            mb_url = resource_to_url(mb)
            self.__check_url(mb_url, path='/my-entities/0/children/0/',
                             query='')
        finally:
            resource_repo.set_collection_parent(child_root_coll, srvc)

    def test_url_to_resource(self, collection):
        coll_from_url = url_to_resource(self.base_url)
        assert collection['0'] == coll_from_url['0']

    @pytest.mark.parametrize('url,error,msg',
                             [('http://0.0.0.0:6543/my-foos/', KeyError,
                               'has no subelement my-foos'),
                              ('http://0.0.0.0:6543/my-foos/', KeyError,
                               'has no subelement my-foos'),
                              ('http://0.0.0.0:6543/', ValueError,
                               'Traversal found non-resource object'),
                              (base_url + '?q=id|foo', ValueError,
                               'Expression parameters have errors'),
                              (base_url + '?sort=id|foo', ValueError,
                               'Expression parameters have errors'),
                              (base_url + '?start=0&size=a',
                               ValueError, 'must be a number.'),
                              (base_url + '?start=a&size=100',
                               ValueError, 'must be a number.'),
                              (base_url + '?start=-1&size=100',
                               ValueError,
                               'must be zero or a positive number.'),
                              (base_url + '?start=0&size=-100',
                               ValueError, 'must be a positive number.'),
                              ])
    def test_url_to_resource_invalid(self, url, error, msg):
        with pytest.raises(error) as cm:
            url_to_resource(url)
        assert str(cm.value).find(msg) != -1

    def test_url_to_resource_with_slice(self):
        coll_from_url = url_to_resource(self.base_url + '?size=1&start=0')
        # The length is not affected by the slice...
        assert len(coll_from_url) == 2
        # ... the actual number of members in the collection is.
        assert len(list(coll_from_url)) == 1

    def test_url_to_resource_with_filter(self):
        def _test(criterion, attr, value):
            coll_from_url = \
                        url_to_resource(self.base_url + '?q=%s' % criterion)
            mbs = list(coll_from_url)
            assert len(mbs) == 1
            assert getattr(mbs[0], attr) == value
        _test('id:equal-to:0', 'id', 0)
        _test('id:not-equal-to:0', 'id', 1)
        _test('text:starts-with:"foo"', 'text', 'foo0')
        _test('text:ends-with:"o1"', 'text', 'too1')
        _test('text:contains:"o0"', 'text', 'foo0')
        _test('text:not-contains:"o0"', 'text', 'too1')
        _test('text:contained:"foo0"', 'text', 'foo0')
        _test('text:not-contained:"foo0"', 'text', 'too1')
        _test('id:less-than:1', 'id', 0)
        _test('id:less-than-or-equal-to:0', 'id', 0)
        _test('id:greater-than:0', 'id', 1)
        _test('id:greater-than-or-equal-to:1', 'id', 1)
        _test('id:in-range:0-0', 'id', 0)

    def test_url_to_resource_with_filter_no_values_raises_error(self):
        pytest.raises(ValueError,
                           url_to_resource, self.base_url + '?q=id:equal-to:')

    def test_url_to_resource_with_complex_filter(self):
        criterion = '(id:equal-to:0 and text:equal-to:"foo0") or ' \
                    '(id:equal-to:1 and text:equal-to:"too1")'
        coll_from_url = \
                    url_to_resource(self.base_url + '?q=%s' % criterion)
        mbs = list(coll_from_url)
        assert len(mbs) == 2

    def test_url_to_resource_with_order(self):
        coll_from_url = url_to_resource(self.base_url + '?sort=id:asc')
        assert len(coll_from_url) == 2
        assert list(coll_from_url)[-1].id == 1

    def test_url_to_resource_with_multiple_order(self):
        coll_from_url = url_to_resource(self.base_url +
                                        '?sort=id:asc~text:desc')
        assert len(coll_from_url) == 2
        assert list(coll_from_url)[-1].id == 1

    def test_url_to_resource_with_multiple_filter(self):
        criteria = 'id:less-than:1~id:less-than-or-equal-to:1'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        assert len(coll_from_url) == 1

    def test_url_to_resource_with_multiple_criteria_one_empty(self):
        criteria = 'id:less-than:1~'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        assert len(coll_from_url) == 1

    def test_url_to_resource_with_multiple_values(self):
        criteria = 'id:equal-to:0,1'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        assert len(coll_from_url) == 2

    def test_url_to_resource_with_multiple_values_one_empty(self):
        criteria = 'id:equal-to:0,'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        assert len(coll_from_url) == 1

    def test_url_to_resource_with_multiple_string_values_one_empty(self):
        criteria = 'text:starts-with:"foo",""'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        assert len(coll_from_url) == 1

    def test_url_to_resource_with_link(self):
        criterion = 'parent:equal-to:"%s/my-entity-parents/0/"' % self.app_url
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criterion)
        assert len(coll_from_url) == 1

#    def test_url_to_resource_with_link_and_other(self):
#        criterion1 = 'parent:equal-to:%s/my-entity-parents/0/' % self.app_url
#        criterion2 = 'id:equal-to:0'
#        coll_from_url = url_to_resource(self.base_url +
#                                        '?q=%s~%s' % (criterion1, criterion2))
#        assertlen(coll_from_url), 1)

    def test_url_to_resource_with_link_and_other(self):
        criterion1 = 'parent:equal-to:"%s/my-entity-parents/0/"' \
                     % self.app_url
        criterion2 = 'id:equal-to:0'
        coll_from_url = url_to_resource(self.base_url +
                                        '?q=%s~%s' % (criterion1, criterion2))
        assert len(coll_from_url) == 1

    def test_two_urls(self):
        par_url = self.app_url + '/my-entity-parents/'
        criteria = 'parent:equal-to:"%s","%s"' \
                   % (par_url + '0/', par_url + '1/')
        url = self.base_url + '?q=%s' % criteria
        coll_from_url = url_to_resource(url)
        assert len(coll_from_url) == 2

    def test_url_to_resource_contained_with_simple_collection_link(self):
        nested_url = self.app_url \
                     + '/my-entity-parents/?q=id:less-than:1'
        url = self.app_url + '/my-entities/?q=parent:contained:' \
              + '"' + nested_url + '"'
        coll_from_url = url_to_resource(url)
        assert len(coll_from_url) == 1

    def test_url_to_resource_contained_with_complex_collection_link(self):
        for op, crit, num in zip((' and ', '~'),
                                 ('id:greater-than:0',
                                  'text:not-equal-to:"foo0"'),
                                 (1, 2)):
            nested_url = self.app_url \
                         + '/my-entity-parents/?q=id:less-than:2' \
                         + op \
                         + crit
            url = self.app_url + '/my-entities/?q=parent:contained:' \
                  + "'" + nested_url + "'"
            coll_from_url = url_to_resource(url)
            assert len(coll_from_url) == num

    def test_url_to_resource_contained_with_grouped_collection_link(self):
        url = self.app_url + '/my-entities/' \
              + '?q=(parent:contained:"' \
              + self.app_url \
              + '/my-entity-parents/?q=id:less-than:3") ' \
              + 'and text:not-equal-to:"foo0"'
        coll_from_url = url_to_resource(url)
        assert len(coll_from_url) == 1

    def test_nested_member_url_with_query_string_fail(self):
        par_url = self.app_url + '/my-entity-parents/1/'
        criteria = 'parent:equal-to:%s?q=id:equal-to:0' % par_url
        url = self.base_url + '?q=%s' % criteria
        pytest.raises(ValueError, url_to_resource, url)

    def test_url_to_resource_invalid_traversal_object(self, monkeypatch):
        monkeypatch.setattr(Service, '__getitem__',
                            classmethod(lambda cls, item: 1))
        url = self.app_url + '/foo'
        with pytest.raises(ValueError) as cm:
            url_to_resource(url)
        exc_msg = 'Traversal found non-resource object'
        assert str(cm.value).startswith(exc_msg)

    def __check_url(self, url,
                    schema=None, path=None, params=None, query=None):
        urlp = urlparse.urlparse(url)
        if not schema is None:
            assert urlp.scheme == schema # pylint: disable=E1101
        if not path is None:
            assert urlp.path == path # pylint: disable=E1101
        if not params is None:
            assert urlp.params == params # pylint: disable=E1101
        if not query is None:
            # We can not rely on the order of query parameters returned by
            # urlparse, so we compare the sets of parameters.
            assert set(urlp.query.split('&')) == \
                       set(query.split('&')) # pylint: disable=E1101


class TestUrlNoRdb(_TestUrl):
    config_file_name = 'configure_no_rdb.zcml'


@pytest.mark.usefixtures("rdb")
class TestUrlRdb(_TestUrl):
    config_file_name = 'configure.zcml'
