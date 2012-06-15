"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 23, 2012.
"""
from everest.resources.utils import get_root_collection
from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.entities import MyEntityChild
from everest.tests.testapp_db.entities import MyEntityGrandchild
from everest.tests.testapp_db.entities import MyEntityParent
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityChild
from everest.tests.testapp_db.interfaces import IMyEntityParent

__docformat__ = 'reStructuredText en'
__all__ = ['create_collection',
           'create_entity',
           ]


def create_entity(entity_id=0, entity_text=None):
    my_entity = MyEntity(text=entity_text)
    my_entity.id = entity_id
    my_entity_parent = MyEntityParent()
    my_entity_parent.id = entity_id
    my_entity.parent = my_entity_parent
    my_entity_child = MyEntityChild()
    my_entity_child.id = entity_id
    my_entity_child.parent = my_entity
    if len(my_entity.children) == 0:
        # Tests that use the ORM will not need to go here.
        my_entity.children.append(my_entity_child)
        assert len(my_entity.children) == 1
    my_entity_grandchild = MyEntityGrandchild()
    my_entity_grandchild.id = entity_id
    my_entity_child.children.append(my_entity_grandchild)
    return my_entity


def create_collection():
    my_entity0 = create_entity(entity_id=0, entity_text='foo0')
    my_entity1 = create_entity(entity_id=1, entity_text='too1')
    coll = get_root_collection(IMyEntity)
    my_mb0 = coll.create_member(my_entity0)
    my_mb1 = coll.create_member(my_entity1)
    # FIXME: This should really be done automatically.
    parent_coll = get_root_collection(IMyEntityParent)
    parent_coll.add(my_mb0.parent)
    parent_coll.add(my_mb1.parent)
    children_coll = get_root_collection(IMyEntityChild)
    children_coll.add(list(my_mb0.children)[0])
    children_coll.add(list(my_mb1.children)[0])
    return coll

