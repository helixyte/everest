"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 23, 2012.
"""

from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.entities import MyEntityChild
from everest.tests.testapp_db.entities import MyEntityGrandchild
from everest.tests.testapp_db.entities import MyEntityParent

__docformat__ = 'reStructuredText en'
__all__ = ['create_entity',
           ]


def create_entity(entity_id=0):
    my_entity = MyEntity()
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
