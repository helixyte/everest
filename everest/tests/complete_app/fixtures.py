"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 17, 2014.
"""
import pytest

from everest.representers.utils import as_representer
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityGrandchild
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity


__docformat__ = 'reStructuredText en'
__all__ = []


# pylint: disable=W0621

def _check_parent(func):
    def wrap(*args, **kw):
        inst = func(*args, **kw)
        if inst.children[0].parent is None:
            inst.children[0].parent = inst
        return inst
    return wrap


@pytest.fixture
def my_entity_parent_fac(test_object_fac):
    kw = dict(id=0,
              )
    return test_object_fac(MyEntityParent, kw=kw)


@pytest.fixture
def my_entity_grandchild_fac(test_object_fac):
    kw = dict(id=0,
              )
    return test_object_fac(MyEntityGrandchild, kw=kw)


@pytest.fixture
def my_entity_child_fac(test_object_fac, my_entity_grandchild_fac):
    kw = dict(id=0,
              children=[my_entity_grandchild_fac()])
    return _check_parent(test_object_fac(MyEntityChild, kw=kw))


@pytest.fixture
def my_entity_fac(test_object_fac, my_entity_parent_fac,
                  my_entity_child_fac):
    kw = dict(id=0,
              parent=my_entity_parent_fac(),
              children=[my_entity_child_fac()])
    return _check_parent(test_object_fac(MyEntity, kw=kw))


def create_entity_tree(id=0, text=None): # pylint: disable=W0622
    my_entity_grandchild = MyEntityGrandchild(id=id, text=text)
    my_entity_child = MyEntityChild(id=id, text=text,
                                    children=[my_entity_grandchild])
    my_entity_parent = MyEntityParent(id=id, text=text,)
    my_entity = MyEntity(id=id, text=text,
                         children=[my_entity_child],
                         parent=my_entity_parent)
    # If we run with the SQLAlchemy backend, the back references are populated
    # automatically.
    if my_entity_child.parent is None:
        my_entity_child.parent = my_entity
    if my_entity_grandchild.parent is None:
        my_entity_grandchild.parent = my_entity_child
    return my_entity


@pytest.fixture
def entity_tree_fac(test_object_fac):
    return test_object_fac(create_entity_tree, kw=dict())


@pytest.fixture
def collection(resource_repo, my_entity_fac, my_entity_id1_fac):
    my_entity1 = my_entity_fac(text='foo0')
    my_entity2 = my_entity_id1_fac(text='too1')
    coll = resource_repo.get_collection(IMyEntity)
    coll.create_member(my_entity1)
    coll.create_member(my_entity2)
    return coll


@pytest.fixture
def member(collection):
    return next(iter(collection))


@pytest.fixture
def representer(request, collection):
    cnt_type = request.cls.content_type
    return as_representer(collection, cnt_type)


@pytest.fixture
def member_representer(request, member):
    cnt_type = request.cls.content_type
    return as_representer(member, cnt_type)


@pytest.fixture
def mapping(representer):
    return representer._mapping # accessing protected pylint: disable=W0212


@pytest.fixture
def member_mapping(member_representer):
    return member_representer._mapping # accessing protected pylint: disable=W0212

# pylint: enable=W0621
