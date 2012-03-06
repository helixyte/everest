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
    text = terminal_attribute(str, 'text')
    text_rc = terminal_attribute(str, 'text_ent')


class MyEntityMember(Member):
    relation = 'http://test.org/my-entity'
    parent = member_attribute(IMyEntityParent, 'parent')
    nested_parent = member_attribute(IMyEntityParent, 'parent', is_nested=True)
    children = collection_attribute(IMyEntityChild, 'children')
    text = terminal_attribute(str, 'text')
    text_rc = terminal_attribute(str, 'text_ent')
    number = terminal_attribute(int, 'number')
    parent_text = terminal_attribute(str, 'parent.text_ent')


class MyEntityChildMember(Member):
    relation = 'http://test.org/my-entity-child'
    children = collection_attribute(IMyEntityGrandchild,
                                    entity_attr='children',
                                    is_nested=False,
                                    backref='parent')
    no_backref_children = collection_attribute(IMyEntityGrandchild,
                                               entity_attr='children',
                                               is_nested=False)
    text = terminal_attribute(str, 'text')
    text_rc = terminal_attribute(str, 'text_ent')


class MyEntityGrandchildMember(Member):
    relation = 'http://test.org/my-entity-grandchild'
    text = terminal_attribute(str, 'text')
    text_rc = terminal_attribute(str, 'text_ent')
    parent = member_attribute(IMyEntityChild, 'parent')
