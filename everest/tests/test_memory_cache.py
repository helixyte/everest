"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 13, 2013.
"""
from everest.entities.base import Entity
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.interfaces import IOrderSpecificationFactory
from everest.querying.specifications import FilterSpecificationFactory
from everest.querying.specifications import OrderSpecificationFactory
from everest.querying.specifications import asc
from everest.querying.specifications import eq
from everest.repositories.memory.cache import EntityCache
from everest.repositories.memory.querying import EvalFilterExpression
from everest.repositories.memory.querying import EvalOrderExpression
from everest.testing import Pep8CompliantTestCase
from pyramid.threadlocal import get_current_registry
from everest.repositories.memory.cache import EntityCacheMap

__docformat__ = 'reStructuredText en'
__all__ = ['EntityCacheTestCase',
           'EntityCacheMapTestCase',
           ]


class EntityCacheTestCase(Pep8CompliantTestCase):
    def set_up(self):
        Pep8CompliantTestCase.set_up(self)
        # Some tests require the filter and order specification factories.
        flt_spec_fac = FilterSpecificationFactory()
        ord_spec_fac = OrderSpecificationFactory()
        reg = get_current_registry()
        reg.registerUtility(flt_spec_fac, IFilterSpecificationFactory)
        reg.registerUtility(ord_spec_fac, IOrderSpecificationFactory)

    def test_basics(self):
        ent = MyEntity(id=0)
        cache = EntityCache(entities=[])
        cache.add(ent)
        self.assert_true(cache.get_by_id(ent.id) is ent)
        self.assert_true(cache.has_id(ent.id))
        self.assert_true(cache.get_by_slug(ent.slug) is ent)
        self.assert_true(cache.has_slug(ent.slug))
        ent1 = MyEntity(id=0)
        txt = 'FROBNIC'
        ent1.text = txt
        cache.replace(ent1)
        self.assert_equal(cache.get_by_id(ent.id).text, txt)
        self.assert_equal(cache.get_all(), [ent])
        self.assert_equal(list(cache.retrieve()), [ent])
        cache.remove(ent)
        self.assert_is_none(cache.get_by_id(ent.id))
        self.assert_is_none(cache.get_by_slug(ent.slug))

    def test_filter_order_slice(self):
        ent0 = MyEntity(id=0)
        ent1 = MyEntity(id=1)
        ent2 = MyEntity(id=2)
        cache = EntityCache(entities=[])
        cache.add(ent0)
        cache.add(ent1)
        cache.add(ent2)
        filter_expr = EvalFilterExpression(~eq(id=0))
        order_expr = EvalOrderExpression(asc('id'))
        slice_expr = slice(1, 2)
        self.assert_equal(list(cache.retrieve(filter_expression=filter_expr,
                                              order_expression=order_expr,
                                              slice_expression=slice_expr)),
                          [ent2])

    def test_allow_none_id_false(self):
        ent = MyEntity()
        cache = EntityCache(entities=[], allow_none_id=False)
        self.assert_raises(ValueError, cache.add, ent)


class EntityCacheMapTestCase(Pep8CompliantTestCase):
    def test_basics(self):
        ecm = EntityCacheMap()
        ent = MyEntity(id=0)
        ecm.add(MyEntity, ent)
        self.assert_equal(ecm[MyEntity].get_by_id(0), ent)
        self.assert_true(ent in ecm)
        self.assert_equal(ecm.keys(), [MyEntity])
        ecm.remove(MyEntity, ent)
        self.assert_false(ent in ecm)


class MyEntity(Entity):
    text = None

