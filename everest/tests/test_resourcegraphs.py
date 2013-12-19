"""

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 21, 2012.
"""
from everest.resources.storing import build_resource_dependency_graph
from everest.resources.utils import get_member_class
from everest.testing import TestCaseWithConfiguration
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild
from everest.tests.complete_app.interfaces import IMyEntityGrandchild
from everest.tests.complete_app.interfaces import IMyEntityParent

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceGraphTestCase',
           ]


class ResourceGraphTestCase(TestCaseWithConfiguration):
    package_name = 'everest.tests.complete_app'

    def set_up(self):
        TestCaseWithConfiguration.set_up(self)
        self.config.load_zcml('configure_no_rdb.zcml')
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
        # Entity Grandchild has Child, but we ignore backreferences.
        self.assert_equal(grph.neighbors(entity_grandchild_mb_cls),
                          [])
        # Entity has Parent and Child.
        self.assert_equal(set(grph.neighbors(entity_mb_cls)),
                          set([entity_parent_mb_cls, entity_child_mb_cls]))
