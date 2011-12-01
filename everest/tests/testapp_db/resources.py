"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 1, 2011.
"""

from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.tests.testapp_db.interfaces import IMyEntityChild
from everest.tests.testapp_db.interfaces import IMyEntityGrandchild
from everest.tests.testapp_db.interfaces import IMyEntityParent

__docformat__ = 'reStructuredText en'
__all__ = []


class MyEntityParentMember(Member):
    relation = 'http://test.org/my-entity-parent'
    text = terminal_attribute('text', str)


class MyEntityMember(Member):
    relation = 'http://test.org/my-entity'
    parent = member_attribute('parent', IMyEntityParent)
    children = collection_attribute('children', IMyEntityChild, is_nested=True)
    text = terminal_attribute('text', str)
    number = terminal_attribute('number', int)


class MyEntityChildMember(Member):
    relation = 'http://test.org/my-entity-child'
    children = collection_attribute('children', IMyEntityGrandchild,
                                    is_nested=True)
    text = terminal_attribute('text', str)


class MyEntityGrandchildMember(Member):
    relation = 'http://test.org/my-entity-grandchild'
    text = terminal_attribute('text', str)

