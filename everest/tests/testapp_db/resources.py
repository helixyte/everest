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
import datetime

__docformat__ = 'reStructuredText en'
__all__ = ['MyEntityChildMember',
           'MyEntityMember',
           'MyEntityGrandchildMember',
           'MyEntityParentMember',
           ]


class MyEntityParentMember(Member):
    relation = 'http://test.org/myentity-parent'
    # String terminal.
    text = terminal_attribute(str, 'text')
    # String terminal with different name in entity.
    text_rc = terminal_attribute(str, 'text_ent')


class MyEntityMember(Member):
    relation = 'http://test.org/myentity'
    # Member.
    parent = member_attribute(IMyEntityParent, 'parent')
    # Nested member (i.e., URL built relative to parent).
    nested_parent = member_attribute(IMyEntityParent, 'parent', is_nested=True)
    # Collection.
    children = collection_attribute(IMyEntityChild, 'children')
    # String terminal.
    text = terminal_attribute(str, 'text')
    # String terminal with different name in entity.
    text_rc = terminal_attribute(str, 'text_ent')
    # Number terminal.
    number = terminal_attribute(int, 'number')
    # Date time terminal.
    date_time = terminal_attribute(datetime.datetime, 'date_time')
    # Nested attribute.
    parent_text = terminal_attribute(str, 'parent.text_ent')


class MyEntityChildMember(Member):
    relation = 'http://test.org/myentity-child'
    # Collection built from backreferences.
    children = collection_attribute(IMyEntityGrandchild,
                                    entity_attr='children',
                                    is_nested=False,
                                    backref='parent')
    # Collection built from IDs.
    no_backref_children = collection_attribute(IMyEntityGrandchild,
                                               entity_attr='children',
                                               is_nested=False)
    # String terminal.
    text = terminal_attribute(str, 'text')
    # String terminal with different name in entity.
    text_rc = terminal_attribute(str, 'text_ent')


class MyEntityGrandchildMember(Member):
    relation = 'http://test.org/myentity-grandchild'
    # String terminal.
    text = terminal_attribute(str, 'text')
    # String terminal with different name in entity.
    text_rc = terminal_attribute(str, 'text_ent')
    # Member.
    parent = member_attribute(IMyEntityChild, 'parent')
