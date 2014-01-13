"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 13, 2012.
"""
from everest.entities.utils import new_entity_id
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.specifications import FilterSpecificationFactory
from everest.repositories.memory import Aggregate
from everest.repositories.memory import Repository
from everest.testing import EntityTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityParent
from mock import patch
from pyramid.threadlocal import get_current_registry
import gc
from everest.tests.complete_app.interfaces import IMyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild
from everest.tests.complete_app.interfaces import IMyEntityGrandchild


__docformat__ = 'reStructuredText en'
__all__ = ['JoinedTransactionMemorySessionTestCase',
           'TransactionLessMemorySessionTestCase',
           ]


class _MemorySessionTestCaseBase(EntityTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'
    _session = None

    def set_up(self):
        EntityTestCase.set_up(self)
        # Some tests require the filter specification factory.
        flt_spec_fac = FilterSpecificationFactory()
        reg = get_current_registry()
        reg.registerUtility(flt_spec_fac, IFilterSpecificationFactory)
        self._repository = self._make_repository()
        # Strictly speaking, we should register the rcs only with *one*
        # repository; the tests do not require this at the moment, however.
        for ifc in (IMyEntityParent, IMyEntity, IMyEntityChild,
                    IMyEntityGrandchild):
            self._repository.register_resource(ifc)
        self._repository.initialize()
        self._session = self._repository.session_factory()

    def test_basics(self):
        ent = MyEntity()
        self.assert_is_none(ent.id)
        self.assert_is_none(ent.slug)
        # Load without ID fails.
        with self.assert_raises(ValueError) as cm:
            self._session.load(MyEntity, ent)
        self.assert_true(cm.exception.args[0].startswith('Can not load'))
        self._session.add(MyEntity, ent)
        self.assert_true(ent in self._session)
        self.assert_true(ent in self._session.query(MyEntity))
        self.assert_equal(list(self._session.new), [ent])
        # Commit triggers ID generation.
        self._session.commit()
        self.assert_is_not_none(ent.id)
        self.assert_is_not_none(ent.slug)
        # After commit, the session is empty.
        self.assert_false(ent in self._session)
        self.assert_equal(len(self._session.query(MyEntity).all()), 1)
        # Test loading by ID and slug.
        fetched_ent0 = self._session.get_by_id(MyEntity, ent.id)
        self.assert_equal(fetched_ent0.slug, ent.slug)
        fetched_ent1 = self._session.get_by_slug(MyEntity, ent.slug)
        self.assert_equal(fetched_ent1.id, ent.id)
        # We get a clone when we load an entity from the session.
        self.assert_false(fetched_ent0 is ent)
        # Once loaded, we always get the same entity.
        self.assert_true(fetched_ent0 is fetched_ent1)
        self._session.remove(MyEntity, fetched_ent0)
        self.assert_equal(len(self._session.query(MyEntity).all()), 0)
        self.assert_is_none(self._session.get_by_id(MyEntity, ent.id))
        self.assert_is_none(self._session.get_by_slug(MyEntity, ent.slug))
        self.assert_equal(list(self._session.deleted), [fetched_ent0])

    def test_remove_entity_not_in_session_raises_error(self):
        ent = MyEntity()
        self.assert_raises(ValueError, self._session.remove, MyEntity, ent)

    def test_add_deleted(self):
        ent = MyEntity()
        self._session.add(MyEntity, ent)
        self._session.commit()
        self._session.remove(MyEntity, ent)
        self._session.add(MyEntity, ent)

    def test_nested(self):
        ent = MyEntity()
        parent = MyEntityParent()
        ent.parent = parent
        child = MyEntityChild()
        ent.children.append(child)
        self._session.add(MyEntity, ent)
        self._session.commit()
        self.assert_equal(len(self._session.query(MyEntityChild).all()), 1)
        self.assert_equal(len(self._session.query(MyEntityParent).all()), 1)
        fetched_ent = self._session.query(MyEntity).one()
        self.assert_is_not_none(fetched_ent.parent)
        self.assert_equal(len(fetched_ent.children), 1)

    def test_nested_with_set_collection_type(self):
        ent = MyEntity()
        child = MyEntityChild()
        ent.children = set([child])
        self._session.add(MyEntity, ent)
        self._session.commit()
        fetched_ent = self._session.query(MyEntity).one()
        self.assert_true(isinstance(fetched_ent.children, set))

    def test_nested_with_invalid_collection_type(self):
        ent = MyEntity()
        child = MyEntityChild()
        ent.children = (child,)
        self.assert_raises(ValueError, self._session.add, MyEntity, ent)
        ent.id = 0
        child.id = 0
        with self.assert_raises(ValueError) as cm:
            self._session.load(MyEntity, ent)
        self.assert_true(cm.exception.args[0].startswith('Do not know'))

    def test_nested_with_invalid_collection_data(self):
        ent = MyEntity()
        ent.children = [None]
        self.assert_raises(ValueError, self._session.add, MyEntity, ent)

    def _make_repository(self):
        raise NotImplementedError('Abstract method.')


class JoinedTransactionMemorySessionTestCase(_MemorySessionTestCaseBase):
    def _make_repository(self):
        return Repository('DUMMY', Aggregate, join_transaction=True)


class TransactionLessMemorySessionTestCase(_MemorySessionTestCaseBase):
    def _make_repository(self):
        return Repository('DUMMY', Aggregate)

    def test_update_entity_not_in_session_raises_error(self):
        ent = MyEntity()
        self.assert_raises(ValueError, self._session.update, MyEntity, ent)

    def test_get_entity_not_in_session(self):
        self.assert_is_none(self._session.get_by_id(MyEntity, '-1'))

    def test_references(self):
        ent = MyEntity()
        self._session.add(MyEntity, ent)
        self.assert_equal(len(self._session.query(MyEntity).all()), 1)
        # Even with the last external ref gone, the cache should hold a
        # reference to the entities it manages.
        del ent
        gc.collect()
        self.assert_equal(len(self._session.query(MyEntity).all()), 1)

    def test_id_generation(self):
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        self._session.commit()
        self.assert_is_not_none(ent1.id)
        ent2 = MyEntity()
        self._session.add(MyEntity, ent2)
        self._session.commit()
        self.assert_is_not_none(ent2.id)
        # entity IDs can be sorted by creation time.
        self.assert_true(ent2.id > ent1.id)

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, None)
    def test_with_id_without_slug(self):
        ent = MyEntity(id=0)
        self._session.add(MyEntity, ent)
        self.assert_true(self._session.get_by_id(MyEntity, 0) is ent)

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, 'slug')
    def test_without_id_with_slug(self):
        ent = MyEntity()
        self._session.add(MyEntity, ent)
        self.assert_true(self._session.get_by_slug(MyEntity, 'slug') is ent)

    def test_duplicate_id_raises_error(self):
        ent_id = new_entity_id()
        ent1 = MyEntity(id=ent_id)
        self._session.add(MyEntity, ent1)
        ent2 = MyEntity(id=ent_id)
        self.assert_raises(ValueError, self._session.add, MyEntity, ent2)

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, 'slug')
    def test_duplicate_slug_raises_error(self):
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        ent2 = MyEntity()
        self.assert_raises(ValueError,
                           self._session.add, MyEntity, ent2)

    def test_cope_with_numeric_id(self):
        ent = MyEntity(id=0)
        self._session.add(MyEntity, ent)
        self.assert_equal(self._session.get_by_id(MyEntity, ent.id).id,
                          ent.id)
        self.assert_equal(self._session.get_by_slug(MyEntity, ent.slug).id,
                          ent.id)

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, 'slug')
    def test_repeated_add_remove(self):
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        self.assert_true(self._session.get_by_slug(MyEntity, ent1.slug)
                         is ent1)
        self._session.remove(MyEntity, ent1)
        self.assert_is_none(self._session.get_by_slug(MyEntity, ent1.slug))
        ent2 = MyEntity()
        self._session.add(MyEntity, ent2)
        self.assert_true(self._session.get_by_slug(MyEntity, ent2.slug)
                         is ent2)
        self._session.remove(MyEntity, ent2)
        self.assert_is_none(self._session.get_by_slug(MyEntity, ent2.slug))

    def test_remove_flush_add(self):
        ent = MyEntity()
        self._session.add(MyEntity, ent)
        self._session.commit()
        self.assert_equal(len(self._session.query(MyEntity).all()), 1)
        self._session.remove(MyEntity, ent)
        self.assert_equal(len(self._session.query(MyEntity).all()), 0)
        self._session.add(MyEntity, ent)
        self.assert_equal(len(self._session.query(MyEntity).all()), 1)

    def test_add_immediate_remove(self):
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        self._session.remove(MyEntity, ent1)
        self.assert_false(ent1 in self._session)
        self.assert_equal(len(self._session.query(MyEntity).all()), 0)

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, 'slug')
    def test_add_remove_add(self):
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        self.assert_true(ent1 in self._session)
        self._session.remove(MyEntity, ent1)
        self.assert_false(ent1 in self._session)
        self._session.add(MyEntity, ent1)
        self.assert_true(ent1 in self._session)

    def test_update_without_id_raises_error(self):
        ent1 = MyEntity(id=0)
        self._session.add(MyEntity, ent1)
        self._session.commit()
        # Re-load.
        ent2 = self._session.load(MyEntity, ent1)
        ent2.id = None
        with self.assert_raises(ValueError) as cm:
            self._session.commit()
        exc_msg = 'Could not persist data - target entity not found'
        self.assert_true(str(cm.exception).startswith(exc_msg))

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, 'slug')
    def test_update_with_different_slug(self):
        ent_id = 0
        ent1 = MyEntity(id=ent_id)
        self._session.add(MyEntity, ent1)
        ent2 = self._session.get_by_id(MyEntity, ent_id)
        text = 'foo'
        ent2.slug = text
        self._session.commit()
        ent3 = self._session.query(MyEntity).filter_by(slug=text).one()
        self.assert_equal(ent3.id, ent_id)

    def test_failing_commit_duplicate_id(self):
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        ent2 = MyEntity()
        self._session.add(MyEntity, ent2)
        self.assert_is_none(ent1.id)
        self.assert_is_none(ent2.id)
        ent2.id = ent1.id = 0
        self.assert_raises(ValueError, self._session.commit)

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, 'slug')
    def test_failing_flush_duplicate_slug(self):
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        ent2 = MyEntity()
        ent2.slug = None
        self._session.add(MyEntity, ent2)
        ent2.slug = 'slug'
        self.assert_raises(ValueError, self._session.commit)

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, 'slug')
    def test_find_added_by_id(self):
        ent1 = MyEntity(id=0)
        self._session.add(MyEntity, ent1)
        ent2 = self._session.get_by_id(MyEntity, ent1.id)
        self.assert_is_not_none(ent2)
        self.assert_equal(ent1.id, ent2.id)

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, 'slug')
    def test_find_added_by_slug(self):
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        ent2 = self._session.get_by_slug(MyEntity, ent1.slug)
        self.assert_is_not_none(ent2)
        self.assert_equal(ent1.id, ent2.id)

    @patch('%s.entities.MyEntity.slug' %
           _MemorySessionTestCaseBase.package_name, None)
    def test_find_added_with_none_slug_by_slug(self):
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        ent1.slug = 'testslug'
        ent2 = self._session.get_by_slug(MyEntity, ent1.slug)
        self.assert_is_not_none(ent2)
        self.assert_equal(ent1.id, ent2.id)

    def test_update(self):
        ent1 = MyEntity(id=0)
        self._session.add(MyEntity, ent1)
        ent2 = MyEntity()
        ent2.id = ent1.id
        my_attr_value = 1
        ent2.number = my_attr_value
        self._session.update(MyEntity, ent2)
        ent3 = self._session.get_by_id(MyEntity, ent1.id)
        self.assert_is_not_none(ent3)
        self.assert_equal(ent3.id, ent1.id)
        self.assert_equal(ent3.number, my_attr_value)
