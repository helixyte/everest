"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 13, 2013.
"""
import pytest

from everest.entities.base import Entity
from everest.querying.specifications import asc
from everest.querying.specifications import eq
from everest.repositories.memory.cache import EntityCache
from everest.repositories.memory.cache import EntityCacheMap
from everest.repositories.memory.querying import EvalFilterExpression
from everest.repositories.memory.querying import EvalOrderExpression
from everest.repositories.state import EntityState
from everest.resources.descriptors import terminal_attribute


__docformat__ = 'reStructuredText en'
__all__ = ['TestEntityCache',
           'TestEntityCacheMap',
           ]


class TestEntityCache(object):
    def test_basics(self):
        ent = MyEntity(id=0)
        cache = EntityCache(entities=[])
        cache.add(ent)
        assert cache.get_by_id(ent.id) is ent
        assert cache.has_id(ent.id)
        assert cache.get_by_slug(ent.slug) is ent
        assert cache.has_slug(ent.slug)
        assert len(cache.get_all()) == 1
        # Adding the same entity twice should not have any effect.
        cache.add(ent)
        assert cache.get_by_id(ent.id) is ent
        assert len(cache.get_all()) == 1
        #
        ent1 = MyEntity(id=0)
        txt = 'FROBNIC'
        ent1.text = txt
        cache.update(EntityState.get_state_data(ent1), ent)
        assert cache.get_by_id(ent.id).text == txt
        assert cache.get_all() == [ent]
        assert list(cache.retrieve()) == [ent]
        cache.remove(ent)
        assert cache.get_by_id(ent.id) is None
        assert cache.get_by_slug(ent.slug) is None

    def test_filter_order_slice(self, configurator):
        configurator.begin()
        try:
            ent0 = MyEntity(id=0)
            ent1 = MyEntity(id=1)
            ent2 = MyEntity(id=2)
            cache = EntityCache(entities=[])
            cache.add(ent0)
            cache.add(ent1)
            cache.add(ent2)
            filter_expr = EvalFilterExpression(~eq(id=0))
            order_expr = EvalOrderExpression(asc('id'))
            slice_key = slice(1, 2)
            assert list(cache.retrieve(filter_expression=filter_expr,
                                       order_expression=order_expr,
                                       slice_key=slice_key)) \
                   == [ent2]
        finally:
            configurator.end()

    def test_allow_none_id_false(self):
        ent = MyEntity()
        cache = EntityCache(entities=[], allow_none_id=False)
        with pytest.raises(ValueError):
            cache.add(ent)


class TestEntityCacheMap(object):
    def test_basics(self):
        ecm = EntityCacheMap()
        ent = MyEntity(id=0)
        ecm.add(MyEntity, ent)
        assert ecm.has_key(MyEntity)
        assert ecm[MyEntity].get_by_id(ent.id) == ent
        assert ent in ecm
        assert list(ecm.keys()) == [MyEntity]
        ecm.remove(MyEntity, ent)
        assert not ent in ecm


class MyEntity(Entity):
    __everest_attributes__ = dict(text=terminal_attribute(str, 'text'))
    text = None
