"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 5, 2012.
"""
from everest.mime import CsvMime
from everest.renderers import RendererFactory
from everest.renderers import ResourceRenderer
from everest.testing import ResourceTestCase
from everest.tests.complete_app.testing import create_collection
from pyramid.compat import binary_type

__docformat__ = 'reStructuredText en'
__all__ = ['RendererTestCase',
           ]


class RendererTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_rpr.zcml'
    class _Info(object):
        def __init__(self, name):
            self.name = name
    def test_renderer_factory(self):
        def _test(rc, rnd_name, exp_str):
            inf = self._Info(rnd_name)
            fac = RendererFactory(inf)
            rpr_str = fac(dict(), dict(request=self._request, context=rc))
            self.assert_true(isinstance(rpr_str, binary_type))
            self.assert_not_equal(rpr_str.find(exp_str), -1)
        resource = create_collection()
        _test(resource, 'csv', b'"id","parent.id"')
        _test(resource, 'atom', b'www.w3.org/2005/Atom')
        self.assert_raises(ValueError, _test, resource, 'foo', '')
        self.assert_raises(ValueError, _test, None, 'csv', '"id","parent"')

    def test_nonvalidating_renderer(self):
        class FooRenderer(ResourceRenderer):
            def __init__(self):
                ResourceRenderer.__init__(self, CsvMime)

            def _validate(self, resource): # pylint: disable=W0613
                return False

            def _prepare_response(self, system):
                pass
        rc = create_collection()
        rnd = FooRenderer()
        self.assert_raises(ValueError, rnd,
                           dict(), dict(request=self._request, context=rc))
