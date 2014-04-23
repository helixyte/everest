"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 17, 2014.
"""
import pytest

from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.testing import create_entity
from everest.representers.utils import as_representer


__docformat__ = 'reStructuredText en'
__all__ = ['collection',
           ]


@pytest.fixture
def collection(resource_repo, entity_id1=0, entity_id2=1):
    my_entity1 = create_entity(entity_id=None, entity_text='foo0')
    my_entity2 = create_entity(entity_id=None, entity_text='too1')
    coll = resource_repo.get_collection(IMyEntity)
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


@pytest.fixture
def member(collection): # pylint: disable=W0621
    return next(iter(collection))


@pytest.fixture
def representer(request, collection): # pylint: disable=W0621
    cnt_type = request.cls.content_type
    return as_representer(collection, cnt_type)


@pytest.fixture
def member_representer(request, member): # pylint: disable=W0621
    cnt_type = request.cls.content_type
    return as_representer(member, cnt_type)


@pytest.fixture
def mapping(representer): # pylint: disable=W0621
    return representer._mapping # accessing protected pylint: disable=W0212


@pytest.fixture
def member_mapping(member_representer): # pylint: disable=W0621
    return member_representer._mapping # accessing protected pylint: disable=W0212

