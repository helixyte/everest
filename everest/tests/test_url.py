"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.querying.utils import get_filter_specification_factory
from everest.querying.utils import get_order_specification_factory
from everest.testing import ResourceTestCase
from everest.tests.complete_app.resources import MyEntityMember
from everest.tests.complete_app.testing import create_collection
from everest.tests.complete_app.testing import create_entity
from everest.resources.utils import resource_to_url
from everest.resources.utils import url_to_resource
from urlparse import urlparse

__docformat__ = 'reStructuredText en'
__all__ = ['UrlTestCase',
           ]


class UrlTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def set_up(self):
        ResourceTestCase.set_up(self)
        self.coll = create_collection()
        self.app_url = 'http://0.0.0.0:6543'
        self.base_url = '%s/my-entities/' % self.app_url

    def test_resource_to_url_non_resource_object(self):
        ent = create_entity(entity_id=2)
        with self.assert_raises(TypeError) as cm:
            resource_to_url(ent)
        exc_msg = 'Can not generate URL for non-resource'
        self.assert_true(cm.exception.message.startswith(exc_msg))

    def test_resource_to_url_floating_member(self):
        ent = create_entity(entity_id=2)
        mb = MyEntityMember.create_from_entity(ent)
        with self.assert_raises(ValueError) as cm:
            resource_to_url(mb)
        exc_msg = 'Can not generate URL for floating resource'
        self.assert_true(cm.exception.message.startswith(exc_msg))

    def test_resource_to_url(self):
        self.__check_url(resource_to_url(self.coll),
                         schema='http', path='/my-entities/', params='',
                         query='')

    def test_resource_to_url_with_slice(self):
        self.coll.slice = slice(0, 1)
        self.__check_url(resource_to_url(self.coll),
                         schema='http', path='/my-entities/',
                         params='', query='start=0&size=1')

    def test_resource_to_url_with_filter(self):
        flt_spec_fac = get_filter_specification_factory()
        flt_spec = flt_spec_fac.create_equal_to('id', 0)
        self.coll.filter = flt_spec
        self.__check_url(resource_to_url(self.coll),
                         schema='http', path='/my-entities/', params='',
                         query='q=id:equal-to:0')

    def test_resource_to_url_with_order(self):
        ord_spec_fac = get_order_specification_factory()
        ord_spec = ord_spec_fac.create_ascending('id')
        self.coll.order = ord_spec
        self.__check_url(resource_to_url(self.coll),
                         schema='http', path='/my-entities/', params='',
                         query='sort=id:asc')

    def test_resource_to_url_with_multiple_order(self):
        ord_spec_fac = get_order_specification_factory()
        ord_spec_id = ord_spec_fac.create_ascending('id')
        ord_spec_text = ord_spec_fac.create_descending('text')
        ord_spec = ord_spec_fac.create_conjunction(ord_spec_id, ord_spec_text)
        self.coll.order = ord_spec
        self.__check_url(resource_to_url(self.coll),
                         schema='http', path='/my-entities/', params='',
                         query='sort=id:asc~text:desc')

    def test_url_to_resource_nonexisting_collection(self):
        with self.assert_raises(KeyError) as cm:
            url_to_resource('http://0.0.0.0:6543/my-foos/')
        exc_msg = 'has no subelement my-foos'
        self.assert_true(cm.exception.message.endswith(exc_msg))

    def test_url_to_resource_non_resource_object(self):
        with self.assert_raises(ValueError) as cm:
            url_to_resource('http://0.0.0.0:6543/')
        exc_msg = 'Traversal found non-resource object'
        self.assert_true(cm.exception.message.startswith(exc_msg))

    def test_url_to_resource_invalid_filter_criterion(self):
        with self.assert_raises(ValueError) as cm:
            url_to_resource(self.base_url + '?q=id|foo')
        exc_msg = 'Expression parameters have errors'
        self.assert_true(cm.exception.message.startswith(exc_msg))

    def test_url_to_resource_invalid_order_criterion(self):
        with self.assert_raises(ValueError) as cm:
            url_to_resource(self.base_url + '?sort=id|foo')
        exc_msg = 'Expression parameters have errors'
        self.assert_true(cm.exception.message.startswith(exc_msg))

    def test_url_to_resource_invalid_slice(self):
        with self.assert_raises(ValueError) as cm:
            url_to_resource(self.base_url + '?start=0&size=a')
        exc_msg = 'must be a number.'
        self.assert_true(cm.exception.message.endswith(exc_msg))
        with self.assert_raises(ValueError) as cm:
            url_to_resource(self.base_url + '?start=a&size=100')
        self.assert_true(cm.exception.message.endswith(exc_msg))
        with self.assert_raises(ValueError) as cm:
            url_to_resource(self.base_url + '?start=-1&size=100')
        exc_msg = 'must be zero or a positive number.'
        self.assert_true(cm.exception.message.endswith(exc_msg))
        with self.assert_raises(ValueError) as cm:
            url_to_resource(self.base_url + '?start=0&size=-100')
        exc_msg = 'must be a positive number.'
        self.assert_true(cm.exception.message.endswith(exc_msg))

    def test_url_to_resource(self):
        coll_from_url = url_to_resource(self.base_url)
        self.assert_equal(self.coll['0'], coll_from_url['0'])

    def test_url_to_resource_with_slice(self):
        coll_from_url = url_to_resource(self.base_url + '?size=1&start=0')
        # The length is not affected by the slice...
        self.assert_equal(len(coll_from_url), 2)
        # ... the actual number of members in the collection is.
        self.assert_equal(len(list(coll_from_url)), 1)

    def test_url_to_resource_with_filter(self):
        def _test(criterion, attr, value):
            coll_from_url = \
                        url_to_resource(self.base_url + '?q=%s' % criterion)
            mbs = list(coll_from_url)
            self.assert_equal(len(mbs), 1)
            self.assert_equal(getattr(mbs[0], attr), value)
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
        self.assert_raises(ValueError,
                           url_to_resource, self.base_url + '?q=id:equal-to:')

    def test_url_to_resource_with_complex_filter(self):
        criterion = '(id:equal-to:0 and text:equal-to:"foo0") or ' \
                    '(id:equal-to:1 and text:equal-to:"too1")'
        coll_from_url = \
                    url_to_resource(self.base_url + '?q=%s' % criterion)
        mbs = list(coll_from_url)
        self.assert_equal(len(mbs), 2)

    def test_url_to_resource_with_order(self):
        coll_from_url = url_to_resource(self.base_url + '?sort=id:asc')
        self.assert_equal(len(coll_from_url), 2)
        self.assert_equal(list(coll_from_url)[-1].id, 1)

    def test_url_to_resource_with_multiple_order(self):
        coll_from_url = url_to_resource(self.base_url +
                                        '?sort=id:asc~text:desc')
        self.assert_equal(len(coll_from_url), 2)
        self.assert_equal(list(coll_from_url)[-1].id, 1)

    def test_url_to_resource_with_multiple_filter(self):
        criteria = 'id:less-than:1~id:less-than-or-equal-to:1'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        self.assert_equal(len(coll_from_url), 1)

    def test_url_to_resource_with_multiple_criteria_one_empty(self):
        criteria = 'id:less-than:1~'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        self.assert_equal(len(coll_from_url), 1)

    def test_url_to_resource_with_multiple_values(self):
        criteria = 'id:equal-to:0,1'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        self.assert_equal(len(coll_from_url), 2)

    def test_url_to_resource_with_multiple_values_one_empty(self):
        criteria = 'id:equal-to:0,'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        self.assert_equal(len(coll_from_url), 1)

    def test_url_to_resource_with_multiple_string_values_one_empty(self):
        criteria = 'text:starts-with:"foo",""'
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criteria)
        self.assert_equal(len(coll_from_url), 1)

    def test_url_to_resource_with_link(self):
        criterion = 'parent:equal-to:"%s/my-entity-parents/0/"' % self.app_url
        coll_from_url = url_to_resource(self.base_url + '?q=%s' % criterion)
        self.assert_equal(len(coll_from_url), 1)

    def __check_url(self, url,
                    schema=None, path=None, params=None, query=None):
        urlp = urlparse(url)
        if not schema is None:
            self.assert_equal(urlp.scheme, schema) # pylint: disable=E1101
        if not path is None:
            self.assert_equal(urlp.path, path) # pylint: disable=E1101
        if not params is None:
            self.assert_equal(urlp.params, params) # pylint: disable=E1101
        if not query is None:
            self.assert_equal(urlp.query, query) # pylint: disable=E1101
