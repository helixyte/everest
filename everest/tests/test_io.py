"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 21, 2012.
"""

from everest.mime import CsvMime
from everest.resources.io import ConnectedResourcesSerializer
from everest.resources.io import build_resource_dependency_graph
from everest.resources.io import find_connected_resources
from everest.resources.utils import get_member_class
from everest.resources.utils import get_root_collection
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.entities import MyEntityChild
from everest.tests.testapp_db.entities import MyEntityGrandchild
from everest.tests.testapp_db.entities import MyEntityParent
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityChild
from everest.tests.testapp_db.interfaces import IMyEntityGrandchild
from everest.tests.testapp_db.interfaces import IMyEntityParent
from everest.tests.testapp_db.resources import MyEntityChildMember
from everest.tests.testapp_db.resources import MyEntityGrandchildMember

__docformat__ = 'reStructuredText en'
__all__ = ['ConnectedResourcesTestCase',
           'ResourceDependencyGraphTestCase',
           ]

class ResourceGraphTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'
    _interfaces = [IMyEntityParent, IMyEntity, IMyEntityChild,
                   IMyEntityGrandchild]


class ResourceDependencyGraphTestCase(ResourceGraphTestCase):

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
        # Entity Grandchild has Child, but backrefs are excluded by default.
        self.assert_equal(grph.neighbors(entity_grandchild_mb_cls),
                          [])
        # Entity has Parent and Child.
        self.assert_equal(set(grph.neighbors(entity_mb_cls)),
                          set([entity_parent_mb_cls, entity_child_mb_cls]))


class ConnectedResourcesTestCase(ResourceGraphTestCase):

    def test_find_connected(self):
        member = self._make_member()
        coll_map = find_connected_resources(member)
        for coll in coll_map.itervalues():
            self.assert_equal(len(coll), 1)

    def test_find_connected_with_deps(self):
        member = self._make_member()
        dep_grph = \
            build_resource_dependency_graph(self._interfaces,
                                            include_backrefs=True)
        coll_map = find_connected_resources(member,
                                            dependency_graph=dep_grph)
        # Backrefs should not make a difference since we check for duplicates.
        for coll in coll_map.itervalues():
            self.assert_equal(len(coll), 1)

    def test_find_connected_with_custom_deps(self):
        member = self._make_member()
        ent = member.get_entity()
        # Point grandchild's parent to new child.
        new_child = MyEntityChild(id=1)
        ent.children[0].children[0].parent = new_child
        # When backrefs are excluded, we should not pick up the new parent
        # of the grandchild; when backrefs are included, we should.
        dep_grph = build_resource_dependency_graph(self._interfaces)
        self.assert_false(dep_grph.has_edge((MyEntityGrandchildMember,
                                             MyEntityChildMember)))
        coll_map = find_connected_resources(member)
        self.assert_equal(len(coll_map[MyEntityChildMember]), 1)
        dep_grph = \
            build_resource_dependency_graph(self._interfaces,
                                            include_backrefs=True)
        self.assert_true(dep_grph.has_edge((MyEntityGrandchildMember,
                                            MyEntityChildMember)))
        coll_map = find_connected_resources(member,
                                            dependency_graph=dep_grph)
        self.assert_equal(len(coll_map[MyEntityChildMember]), 2)

    def test_convert_to_strings(self):
        member = self._make_member()
        srl = ConnectedResourcesSerializer(CsvMime)
        rpr_map = srl.to_strings(member)
        self.assert_equal(len(rpr_map), 4)

    def _make_member(self):
        parent = MyEntityParent(id=0)
        entity = MyEntity(id=0, parent=parent)
        parent.child = entity
        child = MyEntityChild(id=0, parent=entity)
        entity.children.append(child)
        grandchild = MyEntityGrandchild(id=0, parent=child)
        child.children.append(grandchild)
        coll = get_root_collection(IMyEntity)
        return coll.create_member(entity)
