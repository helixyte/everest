"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 31, 2013.
"""
from everest.repositories.rdb.testing import RdbTestCaseMixin
from everest.repositories.rdb.utils import OrmAttributeInspector
from everest.repositories.utils import commit_veto
from everest.testing import EntityTestCase
from everest.testing import Pep8CompliantTestCase
from everest.tests.complete_app.entities import MyEntity
from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPRedirection

__docformat__ = 'reStructuredText en'
__all__ = ['RdbAttributeInspectorTestCase',
           'RepositoriesUtilsTestCase',
           ]


class RepositoriesUtilsTestCase(Pep8CompliantTestCase):
    def test_commit_veto(self):
        rsp1 = DummyResponse(HTTPOk().status, dict())
        self.assert_false(commit_veto(None, rsp1))
        rsp2 = DummyResponse(HTTPRedirection().status, dict())
        self.assert_true(commit_veto(None, rsp2))
        rsp3 = DummyResponse(HTTPRedirection().status, {'x-tm':'commit'})
        self.assert_false(commit_veto(None, rsp3))
        rsp4 = DummyResponse(HTTPRedirection().status, {'x-tm':'abort'})
        self.assert_true(commit_veto(None, rsp4))


class RdbAttributeInspectorTestCase(RdbTestCaseMixin, EntityTestCase):
    package_name = 'everest.tests.complete_app'

    def test_rdb_attribute_inspector(self):
        with self.assert_raises(ValueError) as cm:
            OrmAttributeInspector.inspect(MyEntity, 'text.something')
        self.assert_true(str(cm.exception).endswith(
                                    'references a terminal attribute.'))
        with self.assert_raises(ValueError) as cm:
            OrmAttributeInspector.inspect(MyEntity, 'DEFAULT_TEXT')
        self.assert_true(str(cm.exception).endswith('not mapped.'))


class DummyResponse(object):
    def __init__(self, status, headers):
        self.status = status
        self.headers = headers
