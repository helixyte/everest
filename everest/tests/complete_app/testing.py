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
    my_entity_parent = MyEntityParent(id=entity_id, text=entity_text)
    my_entity_grandchild = MyEntityGrandchild(id=entity_id, text=entity_text)
    my_entity_child = MyEntityChild(id=entity_id,
                                    text=entity_text,
                                    children=[my_entity_grandchild])
    my_entity = MyEntity(id=entity_id,
                         text=entity_text,
                         parent=my_entity_parent,
                         children=[my_entity_child])
    # If we run with the SQLAlchemy backend, the back references are populated
    # automatically.
    if my_entity_child.parent is None:
        my_entity_child.parent = my_entity
    if my_entity_grandchild.parent is None:
        my_entity_grandchild.parent = my_entity_child
    return my_entity


def create_collection(entity_id1=0, entity_id2=1):
    my_entity1 = create_entity(entity_id=None, entity_text='foo0')
    my_entity2 = create_entity(entity_id=None, entity_text='too1')
    coll = get_root_collection(IMyEntity)
    coll.create_member(my_entity1)
    coll.create_member(my_entity2)
    my_entity1.id = entity_id1
    my_entity1.parent.id = entity_id1
    my_entity1.children[0].id = entity_id1
    my_entity1.children[0].children[0].id = entity_id1
    my_entity2.id = entity_id2
    my_entity2.parent.id = entity_id2
    my_entity2.children[0].id = entity_id2
    my_entity2.children[0].children[0].id = entity_id2
    return coll
