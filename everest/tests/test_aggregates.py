"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 31, 2012.
"""
import pytest

from everest.constants import DEFAULT_CASCADE
from everest.constants import RELATION_OPERATIONS
from everest.entities.attributes import get_domain_class_attribute
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.specifications import asc
from everest.querying.specifications import eq
from everest.querying.specifications import gt
from everest.repositories.memory.aggregate import MemoryAggregate
from everest.repositories.rdb.aggregate import RdbAggregate
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild


__docformat__ = 'reStructuredText en'
__all__ = ['TestMemoryRelationshipAggregate',
           'TestMemoryRootAggregate',
           'TestRdbRelationshipAggregate',
           'TestRdbRootAggregate',
           ]


class Fixtures(object):
    ent0 = lambda entity_tree_fac: entity_tree_fac(id=0, text='222')
    ent1 = lambda entity_tree_fac: entity_tree_fac(id=1, text='111')
    ent2 = lambda entity_tree_fac: entity_tree_fac(id=2, text='000')


class BaseTestRootAggregate(object):
    package_name = 'everest.tests.complete_app'
    agg_class = None

    def test_clone(self, class_entity_repo):
        agg = class_entity_repo.get_aggregate(IMyEntity)
        assert isinstance(agg, self.agg_class)
        agg_clone = agg.clone()
        for attr in ('entity_class', '_session_factory',
                     '_filter_spec', '_order_spec', '_slice_key',
                     '_RootAggregate__repository'):
            assert getattr(agg, attr) == getattr(agg_clone, attr)

    def test_iterator_count(self, class_entity_repo, ent0, ent1):
        agg = class_entity_repo.get_aggregate(IMyEntity)
        with pytest.raises(StopIteration):
            next(agg.iterator())
        agg.add(ent0)
        assert next(agg.iterator()) is ent0
        # Iterator heeds filtering.
        agg.filter = eq(id=ent1.id)
        with pytest.raises(StopIteration):
            next(agg.iterator())
        agg.add(ent1)
        assert next(agg.iterator()) is ent1
        # Iterator heeds ordering.
        agg.filter = None
        agg.order = asc('id')
        assert isinstance(agg.order, AscendingOrderSpecification)
        assert next(agg.iterator()) is ent0
        # Iterator heeds slice.
        assert len(list(agg.iterator())) == 2
        agg.slice = slice(0, 1)
        assert len(list(agg.iterator())) == 1
        # Count ignores slice.
        assert agg.count() == 2
        # Count heeds filtering.
        agg.filter = eq(id=1)
        assert agg.count() == 1

    def test_get_by_id_and_slug(self, class_entity_repo, ent0):
        agg = class_entity_repo.get_aggregate(IMyEntity)
        agg.add(ent0)
        assert agg.get_by_id(0)  is ent0
        assert agg.get_by_slug('0') is ent0
        assert agg.get_by_id(-1) is None
        assert agg.get_by_slug('-1') is None
        agg.filter = eq(id=1)
        assert agg.get_by_id(0) is None
        assert agg.get_by_slug('0') is None
        with pytest.raises(ValueError) as cm:
            agg.add(object())
        exp_msg = 'Invalid data type for traversal'
        assert str(cm.value).startswith(exp_msg)

    def test_nested_attribute(self, class_entity_repo, ent0, ent1, ent2):
        agg = class_entity_repo.get_aggregate(IMyEntity)
        agg.add(ent0)
        agg.add(ent1)
        agg.add(ent2)
        assert len(list(agg.iterator())) == 3
        agg.filter = eq(**{'parent.text':'222'})
        assert len(list(agg.iterator())) == 1
        agg.filter = None
        assert len(list(agg.iterator())) == 3
        agg.order = asc('parent.text')
        assert next(agg.iterator()) is ent2
        # With nested filter and order.
        agg.filter = gt(**{'parent.text':'000'})
        assert next(agg.iterator()) is ent1
        # With nested filter, order, and slice.
        agg.slice = slice(1, 2)
        assert next(agg.iterator()) is ent0

    def test_add_remove(self, class_entity_repo, ent0):
        agg = class_entity_repo.get_aggregate(IMyEntity)
        agg.add(ent0)
        assert len(list(agg.iterator())) == 1
        agg.remove(ent0)
        assert len(list(agg.iterator())) == 0


class TestMemoryRootAggregate(BaseTestRootAggregate):
    config_file_name = 'configure_no_rdb.zcml'
    agg_class = MemoryAggregate


@pytest.mark.usefixtures('rdb')
class TestRdbRootAggregate(BaseTestRootAggregate):
    agg_class = RdbAggregate


class _TestRelationshipAggregate(object):
    package_name = 'everest.tests.complete_app'

    def _make_rel_agg(self, class_entity_repo, entity, attr_name=None):
        if attr_name is None:
            attr_name = 'children'
        attr = get_domain_class_attribute(entity, attr_name)
        rel = attr.make_relationship(entity)
        child_agg = class_entity_repo.get_aggregate(attr.attr_type)
        return child_agg.make_relationship_aggregate(rel)

    def _make_child(self, child_agg, child_id=0):
        new_parent = MyEntityParent()
        new_ent = MyEntity()
        new_ent.parent = new_parent
        new_child = MyEntityChild()
        new_ent.children.append(new_child)
        if new_child.parent is None:
            new_child.parent = new_ent
        child_agg.add(new_child)
        new_parent.id = child_id
        new_ent.id = child_id
        new_child.id = child_id
        return new_child

    def test_basics(self, class_entity_repo):
        agg = class_entity_repo.get_aggregate(IMyEntity)
        child_agg = class_entity_repo.get_aggregate(IMyEntityChild)
        new_child0 = self._make_child(child_agg)
        new_parent1 = MyEntityParent()
        new_ent1 = MyEntity()
        new_ent1.parent = new_parent1
        new_child1 = MyEntityChild()
        child_rel_agg = self._make_rel_agg(class_entity_repo, new_ent1)
        assert len(list(child_agg.iterator())) == 1
        assert len(list(agg.iterator())) == 1
        assert len(list(child_rel_agg.iterator())) == 0
        # Adding to a relationship aggregate .....
        child_rel_agg.add(new_child1)
        # ....... adds to root aggregates:
        assert len(list(child_agg.iterator())) == 2
        # ....... adds (along the cascade) to parent root aggregate:
        assert len(list(agg.iterator())) == 2
        # ....... appends to children:
        assert new_ent1.children == [new_child1]
        # get by ID and slug, filtering.
        assert child_rel_agg.get_by_id(new_child1.id).id == new_child1.id
        assert \
            child_rel_agg.get_by_slug(new_child1.slug).slug == new_child1.slug
        child_rel_agg.filter = eq(id=2)
        assert child_rel_agg.get_by_id(new_child1.id) is None
        assert child_rel_agg.get_by_slug(new_child1.slug) is None
        # update.
        upd_child0 = MyEntityChild(id=0)
        txt = 'FROBNIC'
        upd_child0.text = txt
        child_rel_agg.update(upd_child0)
        assert new_child0.text == txt
        # FIXME: The RDB backend behaves different from the memory backend
        #        here (parent is not None unless the child is also removed
        #        from the children container).
#        assert new_child0.parent is None

    def test_update_cascade(self, class_entity_repo, monkeypatch):
        csc = DEFAULT_CASCADE & ~RELATION_OPERATIONS.UPDATE
        child_agg = class_entity_repo.get_aggregate(IMyEntityChild)
        new_child = self._make_child(child_agg)
        child_rel_agg = self._make_rel_agg(class_entity_repo,
                                           new_child.parent)
        children_attr = get_domain_class_attribute(MyEntity, 'children')
        monkeypatch.setattr(children_attr, 'cascade', csc)
        upd_child = MyEntityChild(id=0)
        txt = 'FROBNIC'
        upd_child.text = txt
        child_rel_agg.update(upd_child)
        assert new_child.text != txt
        assert not new_child.parent is None

    def test_add_one_to_one(self, class_entity_repo):
        new_parent1 = MyEntityParent(id=1)
        new_ent1 = MyEntity(id=1)
        parent_rel_agg = self._make_rel_agg(class_entity_repo, new_ent1,
                                            'parent')
        assert new_ent1.parent is None
        parent_rel_agg.add(new_parent1)
        assert new_ent1.parent == new_parent1

    def test_delete_cascade(self, class_entity_repo, monkeypatch):
        new_parent1 = MyEntityParent()
        new_ent1 = MyEntity()
        new_ent1.parent = new_parent1
        new_child1 = MyEntityChild()
        new_child1.parent = new_ent1
        child_rel_agg = self._make_rel_agg(class_entity_repo, new_ent1)
        child_rel_agg.add(new_child1)
        new_parent1.id = 1
        new_ent1.id = 1
        new_child1.id = 1
        agg = class_entity_repo.get_aggregate(IMyEntity)
        child_agg = class_entity_repo.get_aggregate(IMyEntityChild)
        assert len(list(child_agg.iterator())) == 1
        assert len(list(agg.iterator())) == 1
        assert new_ent1.children == [new_child1]
        assert new_child1.parent == new_ent1
        csc = DEFAULT_CASCADE | RELATION_OPERATIONS.REMOVE
        children_attr = get_domain_class_attribute(MyEntity, 'children')
        parent_attr = get_domain_class_attribute(MyEntityChild, 'parent')
        monkeypatch.setattr(children_attr, 'cascade', csc)
        monkeypatch.setattr(parent_attr, 'cascade', csc)
        child_rel_agg.remove(new_child1)
        assert new_ent1.children == []
        assert new_child1.parent is None
        assert len(list(child_agg.iterator())) == 0
        if self.__class__.__name__.startswith('TestMemory'):
            # FIXME: Transparent modification of RDB mapper cascades
            #        does not work yet.
            assert len(list(agg.iterator())) == 0
        assert len(list(child_rel_agg.iterator())) == 0


class TestMemoryRelationshipAggregate(_TestRelationshipAggregate):
    config_file_name = 'configure_no_rdb.zcml'

    def test_non_unique_slug(self, class_entity_repo, entity_tree_fac,
                             monkeypatch):
        text = 'SLUG'
        ent0 = entity_tree_fac(id=0, text=text)
        ent1 = entity_tree_fac(id=1, text=text)
        root_agg = class_entity_repo.get_aggregate(IMyEntity)
        root_agg.add(ent0)
        root_agg.add(ent1)
        monkeypatch.setattr(MyEntityChild, 'slug',
                            property(lambda self: self.text))
        child_rel_agg = self._make_rel_agg(class_entity_repo, ent1)
        assert len(list(iter(child_rel_agg))) == 1
        assert child_rel_agg.get_by_slug(text) == ent1.children[0]


@pytest.mark.usefixtures('rdb')
class TestRdbRelationshipAggregate(_TestRelationshipAggregate):
    pass
