"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 31, 2012.
"""
from everest.interfaces import IRepositoryManager
from everest.querying.utils import get_filter_specification_factory
from everest.querying.utils import get_order_specification_factory
from everest.relationship import Relationship
from everest.repository import REPOSITORIES
from everest.testing import EntityTestCase
from everest.tests.testapp_db.entities import MyEntityChild
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityChild
from everest.tests.testapp_db.testing import create_entity

__docformat__ = 'reStructuredText en'
__all__ = ['MemoryAggregateTestCase',
           'OrmAggregateTestCase',
           ]


class _AggregateTestCase(EntityTestCase):
    package_name = 'everest.tests.testapp_db'

    def _test_get_by_id_and_slug(self, ent, agg_children):
        self.assert_true(agg_children.get_by_id(ent.children[0].id)
                         is ent.children[0])
        self.assert_true(agg_children.get_by_slug(ent.children[0].slug)
                         is ent.children[0])

    def test_get_by_id_and_slug(self):
        ent, agg_children = self._make_one()
        self._test_get_by_id_and_slug(ent, agg_children)

    def test_get_by_id_and_slug_with_rel(self):
        ent, agg_children = self._make_one()
        rel = Relationship(ent, ent.children)
        agg_children.set_relationship(rel)
        self._test_get_by_id_and_slug(ent, agg_children)

    def _test_with_filter(self, agg_children):
        spec_fac = get_filter_specification_factory()
        spec = spec_fac.create_equal_to('id', 0)
        agg_children.filter = spec
        self.assert_true(agg_children.filter is spec)
        self.assert_equal(len(list(agg_children.iterator())), 1)
        spec1 = spec_fac.create_equal_to('id', 1)
        agg_children.filter = spec1
        self.assert_equal(len(list(agg_children.iterator())), 0)
        self.assert_is_none(agg_children.get_by_id(0))
        self.assert_is_none(agg_children.get_by_slug('0'))

    def test_with_filter(self):
        agg_children = self._make_one()[1]
        self._test_with_filter(agg_children)

    def test_with_filter_with_rel(self):
        ent, agg_children = self._make_one()
        rel = Relationship(ent, ent.children)
        agg_children.set_relationship(rel)
        self._test_with_filter(agg_children)

    def _test_with_slice(self, agg_children):
        agg_children.slice = slice(0, 1)
        self.assert_true(len(list(agg_children.iterator())), 1)

    def test_with_slice(self):
        agg_children = self._make_one()[1]
        self._test_with_slice(agg_children)

    def test_with_slice_with_rel(self):
        ent, agg_children = self._make_one()
        rel = Relationship(ent, ent.children)
        agg_children.set_relationship(rel)
        self._test_with_slice(agg_children)

    def _test_remove(self, ent, agg_children):
        self.assert_equal(len(list(agg_children.iterator())), 1)
        agg_children.remove(ent.children[0])
        self.assert_equal(len(list(agg_children.iterator())), 0)

    def test_remove(self):
        ent, agg_children = self._make_one()
        self._test_remove(ent, agg_children)

    def test_remove_with_rel(self):
        ent, agg_children = self._make_one()
        rel = Relationship(ent, ent.children)
        agg_children.set_relationship(rel)
        self._test_remove(ent, agg_children)

    def test_with_order(self):
        agg_children = self._make_one()[1]
        spec_fac = get_order_specification_factory()
        spec1 = spec_fac.create_ascending('id')
        agg_children.order = spec1
        self.assert_true(agg_children.order is spec1)
        self.assert_equal(len(list(agg_children.iterator())), 1)
        spec2 = spec_fac.create_ascending('children.text')
        agg_children.order = spec2
        self.assert_equal(len(list(agg_children.iterator())), 1)
        agg_children.order = None
        self.assert_equal(len(list(agg_children.iterator())), 1)

    def _get_repo(self):
        raise NotImplementedError('Abstract method.')

    def _make_one(self):
        rc_repo = self._get_repo()
        ent = create_entity()
        agg = rc_repo.get(IMyEntity).get_aggregate()
        agg.add(ent)
        agg_children = rc_repo.get(IMyEntityChild).get_aggregate()
        for child in ent.children:
            agg_children.add(child)
        return ent, agg_children


class MemoryAggregateTestCase(_AggregateTestCase):
    config_file_name = 'configure_no_orm.zcml'

    def _get_repo(self):
        repo_mgr = self.config.get_registered_utility(IRepositoryManager)
        return repo_mgr.get(REPOSITORIES.MEMORY)

    def test_add(self):
        ent, agg_children = self._make_one()
        self.assert_raises(ValueError, agg_children.add, None)
        self.assert_raises(ValueError, agg_children.add, ent.children[0])
        new_child = MyEntityChild()
        self.assert_equal(len(list(agg_children.iterator())), 1)
        # agg.add does not append to children.
        agg_children.add(new_child)
        self.assert_equal(len(list(agg_children.iterator())), 2)
        self.assert_equal(len(ent.children), 1)

    def test_add_with_relationship(self):
        ent, agg_children = self._make_one()
        rel = Relationship(ent, ent.children)
        agg_children.set_relationship(rel)
        self.assert_raises(ValueError, agg_children.add, ent.children[0])
        self.assert_equal(len(list(agg_children.iterator())), 1)
        # children.append adds to agg.
        new_child = MyEntityChild()
        ent.children.append(new_child)
        self.assert_equal(len(list(agg_children.iterator())), 2)
        self.assert_equal(len(ent.children), 2)
        # agg.add appends to children.
        new_child1 = MyEntityChild()
        agg_children.add(new_child1)
        self.assert_equal(len(list(agg_children.iterator())), 3)
        self.assert_equal(len(ent.children), 3)


# FIXME: This should inherit from OrmTestCaseMixin. However, for some reason
#        doing so breaks subsequent ORM test cases with an OperationalError
#        "ambiguous column" from SA.
class OrmAggregateTestCase(_AggregateTestCase):
    config_file_name = 'configure.zcml'

    def _get_repo(self):
        repo_mgr = self.config.get_registered_utility(IRepositoryManager)
        return repo_mgr.get(REPOSITORIES.ORM)

    def test_defaults_empty(self):
        agg_children = self._make_one()[1]
        agg_children._search_mode = True
        self.assert_equal(agg_children.count(), 0)
        self.assert_equal(len(list(agg_children.iterator())), 0)
