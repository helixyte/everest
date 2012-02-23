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
__all__ = ['MyEntityChildMember',
           'MyEntityMember',
           'MyEntityGrandchildMember',
           'MyEntityParentMember',
           ]


class MyEntityParentMember(Member):
    relation = 'http://test.org/my-entity-parent'
    text = terminal_attribute('text', str)
    text_rc = terminal_attribute('text_ent', str)


class MyEntityMember(Member):
    relation = 'http://test.org/my-entity'
    parent = member_attribute('parent', IMyEntityParent)
    nested_parent = member_attribute('parent', IMyEntityParent, is_nested=True)
    children = collection_attribute('children', IMyEntityChild)
    text = terminal_attribute('text', str)
    text_rc = terminal_attribute('text_ent', str)
    number = terminal_attribute('number', int)
    parent_text = terminal_attribute('parent.text_ent', str)


class MyEntityChildMember(Member):
    relation = 'http://test.org/my-entity-child'
    children = collection_attribute('children', IMyEntityGrandchild,
                                    is_nested=False,
                                    backref_attr='parent')
    no_backref_children = collection_attribute('children', IMyEntityGrandchild,
                                               is_nested=False)
    text = terminal_attribute('text', str)
    text_rc = terminal_attribute('text_ent', str)


class MyEntityGrandchildMember(Member):
    relation = 'http://test.org/my-entity-grandchild'
    text = terminal_attribute('text', str)
    text_rc = terminal_attribute('text_ent', str)
    parent = member_attribute('parent', IMyEntityChild)
