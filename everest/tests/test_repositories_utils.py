"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 31, 2013.
"""
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.repositories.nosqldb.utils import MongoClassRegistry
from everest.repositories.nosqldb.utils import MongoInstrumentedAttribute
from everest.repositories.rdb.utils import OrmAttributeInspector
from everest.repositories.rdb.utils import RdbTestCaseMixin
from everest.repositories.utils import commit_veto
from everest.testing import EntityTestCase
from everest.testing import Pep8CompliantTestCase
from everest.testing import ResourceTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityGrandchild
from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPRedirection
# FIXME: This helps us avoid a dependency on pymongo until we have proper
#        backend extension points.
try: # pragma: nocover
    from everest.repositories.nosqldb.utils import NoSqlAttributeInspector
    from everest.repositories.nosqldb.utils import NoSqlTestCaseMixin
    HAS_MONGO = True
except ImportError: # pragma: nocover
    HAS_MONGO = False

__docformat__ = 'reStructuredText en'
__all__ = ['NoSqlRepositoryUtilsTestCase',
           'RdbAttributeInspectorTestCase',
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


if HAS_MONGO:
    class NoSqlRepositoryUtilsTestCase(NoSqlTestCaseMixin, ResourceTestCase):
        package_name = 'everest.tests.complete_app'
        config_file_name = 'configure_nosql.zcml'

        def test_nosql_attribute_inspector(self):
            infos = NoSqlAttributeInspector.inspect(MyEntity,
                                                    'children.children.id')
            self.assert_equal(len(infos), 3)
            self.assert_equal(infos[0][0],
                              RESOURCE_ATTRIBUTE_KINDS.COLLECTION)
            self.assert_equal(infos[0][1], MyEntityChild)
            self.assert_equal(infos[0][2], 'children')
            self.assert_equal(infos[1][0],
                              RESOURCE_ATTRIBUTE_KINDS.COLLECTION)
            self.assert_equal(infos[1][1], MyEntityGrandchild)
            self.assert_equal(infos[1][2], 'children')
            self.assert_equal(infos[2][0],
                              RESOURCE_ATTRIBUTE_KINDS.TERMINAL)
            self.assert_equal(infos[2][1], int)
            self.assert_equal(infos[2][2], 'id')

        def test_nosql_attribute_inspector_embedded_attribute(self):
            infos = NoSqlAttributeInspector.inspect(MyEntity,
                                                    'children.id.foo')
            self.assert_equal(len(infos), 2)
            self.assert_equal(infos[1][0], RESOURCE_ATTRIBUTE_KINDS.TERMINAL)
            self.assert_equal(infos[1][1], None)
            self.assert_equal(infos[1][2], 'id.foo')

        def test_register_unregister(self):
            class Foo(object):
                pass
            self.assert_true(isinstance(MyEntity.parent,
                                        MongoInstrumentedAttribute))
            self.assert_raises(ValueError, MongoClassRegistry.unregister, Foo)
            self.assert_true(MongoClassRegistry.is_registered(MyEntity))
            # Registering a registered class raises a ValueError.
            self.assert_raises(ValueError, MongoClassRegistry.register,
                               MyEntity, None)
            MongoClassRegistry.unregister(MyEntity)
            self.assert_false(MongoClassRegistry.is_registered(MyEntity))


class DummyResponse(object):
    def __init__(self, status, headers):
        self.status = status
        self.headers = headers
