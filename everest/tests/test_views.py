"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 17, 2011.
"""

from everest.testing import FunctionalTestCase
from everest.tests.testapp import TestApp

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
