"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 23, 2012.
"""
from everest.resources.utils import get_root_collection
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityGrandchild
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity

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
    my_entity.children.append(my_entity_child)
    my_entity_grandchild = MyEntityGrandchild()
    my_entity_grandchild.id = entity_id
    my_entity_child.children.append(my_entity_grandchild)
    return my_entity


def create_collection():
    my_entity0 = create_entity(entity_id=0, entity_text='foo0')
    my_entity1 = create_entity(entity_id=1, entity_text='too1')
    coll = get_root_collection(IMyEntity)
    coll.create_member(my_entity0)
    coll.create_member(my_entity1)
    return coll
