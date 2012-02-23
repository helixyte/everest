"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 21, 2012.
"""
from everest.resources.io import build_resource_dependency_graph
from everest.resources.utils import get_member_class
from everest.testing import BaseTestCase
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityChild
from everest.tests.testapp_db.interfaces import IMyEntityGrandchild
from everest.tests.testapp_db.interfaces import IMyEntityParent

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceGraphTestCase',
           ]


class ResourceGraphTestCase(BaseTestCase):
    package_name = 'everest.tests.testapp_db'
    _interfaces = None

    def set_up(self):
        BaseTestCase.set_up(self)
        self.config.hook_zca()
        self.config.begin()
        self.config.load_zcml('configure.zcml')
        self._interfaces = [IMyEntityParent, IMyEntity, IMyEntityChild,
                            IMyEntityGrandchild]

    def test_dependency_graph(self):
        grph = build_resource_dependency_graph(self._interfaces)
        self.assert_equal(len(grph.nodes()), 4)
        entity_mb_cls = get_member_class(IMyEntity)
        entity_parent_mb_cls = get_member_class(IMyEntityParent)
        entity_child_mb_cls = get_member_class(IMyEntityChild)
        entity_grandchild_mb_cls = get_member_class(IMyEntityGrandchild)
        # Entity Parent resource deps should be empty.
        self.assert_equal(grph.neighbors(entity_parent_mb_cls), [])
        # Entity Child has Grandchild.
        self.assert_equal(grph.neighbors(entity_child_mb_cls),
                          [entity_grandchild_mb_cls])
        # Entity Grandchild has Child.
        self.assert_equal(grph.neighbors(entity_grandchild_mb_cls),
                          [entity_child_mb_cls])
        # Entity has Parent and Child.
        self.assert_equal(set(grph.neighbors(entity_mb_cls)),
                          set([entity_parent_mb_cls, entity_child_mb_cls]))
