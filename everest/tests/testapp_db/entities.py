"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 1, 2011.
"""

from everest.entities.base import Entity

__docformat__ = 'reStructuredText en'
__all__ = []


class _MyEntity(Entity):
    DEFAULT_TEXT = 'TEXT'

    text = None
    text_ent = None

    def __init__(self, text=None, text_ent=None, **kw):
        Entity.__init__(self, **kw)
        if text is None:
            text = self.DEFAULT_TEXT
        self.text = text
        if text_ent is None:
            text_ent = self.DEFAULT_TEXT
        self.text_ent = text_ent


class MyEntityParent(_MyEntity):

    child = None

    def __init__(self, child=None, **kw):
        _MyEntity.__init__(self, **kw)
        self.child = child


class MyEntity(_MyEntity):
    DEFAULT_NUMBER = 1

    parent = None
    children = None

    def __init__(self, parent=None, children=None, number=None, **kw):
        _MyEntity.__init__(self, **kw)
        self.parent = parent
        if children is None:
            children = []
        self.children = children
        if number is None:
            number = self.DEFAULT_NUMBER
        self.number = number

    def __getitem__(self, name):
        if name == 'children':
            return self.children
        return super(MyEntity, self).__getitem__(name)


class MyEntityChild(_MyEntity):

    parent = None
    children = None

    def __init__(self, parent=None, children=None, **kw):
        _MyEntity.__init__(self, **kw)
        self.parent = parent
        if children is None:
            children = []
        self.children = children

    def __getitem__(self, name):
        if name == 'children':
            return self.children
        return super(MyEntityChild, self).__getitem__(name)


class MyEntityGrandchild(_MyEntity):

    parent = None

    def __init__(self, parent=None, **kw):
        _MyEntity.__init__(self, **kw)
        self.parent = parent
