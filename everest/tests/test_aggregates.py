"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 31, 2012.
"""
from everest.constants import DEFAULT_CASCADE
from everest.constants import RELATION_OPERATIONS
from everest.entities.attributes import get_domain_class_attribute
from everest.entities.utils import get_root_aggregate
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.specifications import asc
from everest.querying.specifications import eq
from everest.querying.specifications import gt
from everest.repositories.memory.aggregate import MemoryAggregate
from everest.repositories.rdb.aggregate import RdbAggregate
from everest.repositories.rdb.testing import RdbTestCaseMixin
from everest.testing import EntityTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild
from everest.tests.complete_app.interfaces import IMyEntityParent
from everest.tests.complete_app.testing import create_entity
from everest.utils import classproperty
from mock import patch

__docformat__ = 'reStructuredText en'
__all__ = ['MemoryRootAggregateTestCase',
           'RdbRootAggregateTestCase',
           'RootAggregateTestCaseBase',
           ]


class RootAggregateTestCaseBase(EntityTestCase):
    package_name = 'everest.tests.complete_app'
    agg_class = None

    @classproperty
    def __test__(cls):
        return not cls is RootAggregateTestCaseBase

    def set_up(self):
        EntityTestCase.set_up(self)
        self._aggregate = get_root_aggregate(IMyEntity)
        self._entity = create_entity(entity_id=0)

    def test_clone(self):
        agg = self._aggregate
        self.assert_true(isinstance(agg, self.agg_class))
        agg_clone = agg.clone()
        for attr in ('entity_class', '_session_factory',
                     '_filter_spec', '_order_spec', '_slice_key',
                     '_RootAggregate__repository'):
            self.assert_equal(getattr(agg, attr), getattr(agg_clone, attr))

    def test_iterator_count(self):
        agg = self._aggregate
        ent0 = self._entity
        self.assert_raises(StopIteration, agg.iterator().next)
        agg.add(ent0)
        self.assert_true(agg.iterator().next() is ent0)
        # Iterator heeds filtering.
        agg.filter = eq(id=1)
        self.assert_raises(StopIteration, agg.iterator().next)
        ent1 = create_entity(entity_id=1)
        agg.add(ent1)
        self.assert_true(agg.iterator().next() is ent1)
        # Iterator heeds ordering.
        agg.filter = None
        agg.order = asc('id')
        self.assert_true(isinstance(agg.order, AscendingOrderSpecification))
        self.assert_true(agg.iterator().next() is ent0)
        # Iterator heeds slice.
        self.assert_equal(len(list(agg.iterator())), 2)
        agg.slice = slice(0, 1)
        self.assert_equal(len(list(agg.iterator())), 1)
        # Count ignores slice.
        self.assert_equal(agg.count(), 2)
        # Count heeds filtering.
        agg.filter = eq(id=1)
        self.assert_equal(agg.count(), 1)

    def test_get_by_id_and_slug(self):
        agg = self._aggregate
        ent = self._entity
        agg.add(ent)
        self.assert_true(agg.get_by_id(0) is ent)
        self.assert_true(agg.get_by_slug('0') is ent)
        self.assert_is_none(agg.get_by_id(-1))
        self.assert_is_none(agg.get_by_slug('-1'))
        agg.filter = eq(id=1)
        self.assert_is_none(agg.get_by_id(0))
        self.assert_is_none(agg.get_by_slug('0'))
        with self.assert_raises(ValueError) as cm:
            agg.add(object())
        exp_msg = 'Invalid data type for traversal'
        self.assert_true(cm.exception.message.startswith(exp_msg))

    def test_nested_attribute(self):
        agg = self._aggregate
        ent0 = create_entity(entity_id=0)
        ent0.parent.text_ent = '222'
        ent1 = create_entity(entity_id=1)
        ent1.parent.text_ent = '111'
        ent2 = create_entity(entity_id=2)
        ent2.parent.text_ent = '000'
        agg.add(ent0)
        agg.add(ent1)
        agg.add(ent2)
        self.assert_equal(len(list(agg.iterator())), 3)
        agg.filter = eq(**{'parent.text_ent':'222'})
        self.assert_equal(len(list(agg.iterator())), 1)
        agg.filter = None
        self.assert_equal(len(list(agg.iterator())), 3)
        agg.order = asc('parent.text_ent')
        self.assert_true(next(agg.iterator()) is ent2)
        # With nested filter and order.
        agg.filter = gt(**{'parent.text_ent':'000'})
        self.assert_true(next(agg.iterator()) is ent1)
        # With nested filter, order, and slice.
        agg.slice = slice(1, 2)
        self.assert_true(next(agg.iterator()) is ent0)

    def test_add_remove(self):
        agg = self._aggregate
        ent = self._entity
        agg.add(ent)
        self.assert_equal(len(list(agg.iterator())), 1)
        agg.remove(ent)
        self.assert_equal(len(list(agg.iterator())), 0)


class MemoryRootAggregateTestCase(RootAggregateTestCaseBase):
    config_file_name = 'configure_no_rdb.zcml'
    agg_class = MemoryAggregate


class RdbRootAggregateTestCase(RdbTestCaseMixin, RootAggregateTestCaseBase):
    agg_class = RdbAggregate


class _RelationshipAggregateTestCase(EntityTestCase):
    package_name = 'everest.tests.complete_app'

    def set_up(self):
        EntityTestCase.set_up(self)
        self._entity = create_entity()
        self._aggregate = get_root_aggregate(IMyEntity)
        self._child_aggregate = get_root_aggregate(IMyEntityChild)
        self._parent_aggregate = get_root_aggregate(IMyEntityParent)

    def _make_rel_agg(self, entity=None, attr_name=None):
        if entity is None:
            entity = self._entity
        if attr_name is None:
            attr_name = 'children'
        attr = get_domain_class_attribute(entity, attr_name)
        rel = attr.make_relationship(entity)
        child_agg = get_root_aggregate(attr.attr_type)
        return child_agg.make_relationship_aggregate(rel)

    def _make_child(self, child_id=0):
        new_parent = MyEntityParent()
        new_ent = MyEntity()
        new_ent.parent = new_parent
        new_child = MyEntityChild()
        new_ent.children.append(new_child)
        if new_child.parent is None:
            new_child.parent = new_ent
        self._child_aggregate.add(new_child)
        new_parent.id = child_id
        new_ent.id = child_id
        new_child.id = child_id
        return new_child

    def test_basics(self):
        new_child0 = self._make_child()
        new_parent1 = MyEntityParent()
        new_ent1 = MyEntity()
        new_ent1.parent = new_parent1
        new_child1 = MyEntityChild()
        new_child1.parent = new_ent1
        child_rel_agg = self._make_rel_agg(new_ent1)
        self.assert_equal(len(list(self._child_aggregate.iterator())), 1)
        self.assert_equal(len(list(self._aggregate.iterator())), 1)
        self.assert_equal(len(list(child_rel_agg.iterator())), 0)
        # Adding to a relationship aggregate .....
        child_rel_agg.add(new_child1)
        # ....... adds to root aggregates:
        self.assert_equal(len(list(self._child_aggregate.iterator())), 2)
        # ....... adds (along the cascade) to parent root aggregate:
        self.assert_equal(len(list(self._aggregate.iterator())), 2)
        # ....... appends to children:
        self.assert_equal(new_ent1.children, [new_child1])
        # get by ID and slug, filtering.
        self.assert_equal(child_rel_agg.get_by_id(new_child1.id).id,
                          new_child1.id)
        self.assert_equal(child_rel_agg.get_by_slug(new_child1.slug).slug,
                          new_child1.slug)
        child_rel_agg.filter = eq(id=2)
        self.assert_is_none(child_rel_agg.get_by_id(new_child1.id))
        self.assert_is_none(child_rel_agg.get_by_slug(new_child1.slug))
        # update.
        upd_child0 = MyEntityChild(id=0)
        txt = 'FROBNIC'
        upd_child0.text = txt
        child_rel_agg.update(upd_child0)
        self.assert_equal(new_child0.text, txt)
        # FIXME: The RDB backend behaves different from the memory backend
        #        here (parent is not None unless the child is also removed
        #        from the children container).
#        self.assert_is_none(new_child0.parent)

    def test_update_cascade(self):
        csc = DEFAULT_CASCADE & ~RELATION_OPERATIONS.UPDATE
        new_child = self._make_child()
        child_rel_agg = self._make_rel_agg(new_child.parent)
        with patch.object(get_domain_class_attribute(MyEntity, 'children'),
                          'cascade', csc):
            upd_child = MyEntityChild(id=0)
            txt = 'FROBNIC'
            upd_child.text = txt
            child_rel_agg.update(upd_child)
            self.assert_not_equal(new_child.text, txt)
            self.assert_is_not_none(new_child.parent)

    def test_add_one_to_one(self):
        new_parent1 = MyEntityParent(id=1)
        new_ent1 = MyEntity(id=1)
        parent_rel_agg = self._make_rel_agg(new_ent1, 'parent')
        self.assert_is_none(new_ent1.parent)
        parent_rel_agg.add(new_parent1)
        self.assert_equal(new_ent1.parent, new_parent1)

    def test_delete_cascade(self):
        new_parent1 = MyEntityParent()
        new_ent1 = MyEntity()
        new_ent1.parent = new_parent1
        new_child1 = MyEntityChild()
        new_child1.parent = new_ent1
        child_rel_agg = self._make_rel_agg(new_ent1)
        child_rel_agg.add(new_child1)
        new_parent1.id = 1
        new_ent1.id = 1
        new_child1.id = 1
        self.assert_equal(len(list(self._child_aggregate.iterator())), 1)
        self.assert_equal(len(list(self._aggregate.iterator())), 1)
        self.assert_equal(new_ent1.children, [new_child1])
        self.assert_equal(new_child1.parent, new_ent1)
        csc = DEFAULT_CASCADE | RELATION_OPERATIONS.REMOVE
        with patch.object(get_domain_class_attribute(MyEntity, 'children'),
                          'cascade', csc):
            with patch.object(get_domain_class_attribute(MyEntityChild,
                                                         'parent'),
                              'cascade', csc):
                child_rel_agg.remove(new_child1)
                self.assert_equal(new_ent1.children, [])
                self.assert_is_none(new_child1.parent)
                self.assert_equal(
                            len(list(self._child_aggregate.iterator())), 0)
                if self.__class__.__name__.startswith('Memory'):
                    # FIXME: Transparent modification of RDB mapper cascades
                    #        does not work yet.
                    self.assert_equal(
                                    len(list(self._aggregate.iterator())), 0)
                self.assert_equal(len(list(child_rel_agg.iterator())), 0)


class MemoryRelationshipAggregateTestCase(_RelationshipAggregateTestCase):
    config_file_name = 'configure_no_rdb.zcml'


class RdbRelationshipAggregateTestCase(RdbTestCaseMixin,
                                       _RelationshipAggregateTestCase):
    pass
