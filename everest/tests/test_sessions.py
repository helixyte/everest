"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 13, 2012.
"""
from everest.entities.base import Entity
from everest.entities.utils import new_entity_id
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.specifications import FilterSpecificationFactory
from everest.repositories.memory import Aggregate
from everest.repositories.memory import Repository
from everest.repositories.memory import Session
from everest.testing import Pep8CompliantTestCase
from pyramid.threadlocal import get_current_registry
import gc

__docformat__ = 'reStructuredText en'
__all__ = ['JoinedTransactionMemorySessionTestCase',
           'TransactionLessMemorySessionTestCase',
           ]


class _MemorySessionTestCaseBase(Pep8CompliantTestCase):
    _session = None

    def set_up(self):
        Pep8CompliantTestCase.set_up(self)
        # Some tests require the filter specification factory.
        flt_spec_fac = FilterSpecificationFactory()
        reg = get_current_registry()
        reg.registerUtility(flt_spec_fac, IFilterSpecificationFactory)

    def test_basics(self):
        ent = _MyEntity()
        self.assert_is_none(ent.id)
        self.assert_is_none(ent.slug)
        # Load without ID fails.
        with self.assert_raises(ValueError) as cm:
            self._session.load(_MyEntity, ent)
        self.assert_true(cm.exception.message.startswith('Can not load'))
        self._session.add(_MyEntity, ent)
        self.assert_true(ent in self._session)
        self.assert_true(ent in self._session.query(_MyEntity))
        # Commit triggers ID generation.
        self._session.commit()
        self.assert_is_not_none(ent.id)
        self.assert_is_not_none(ent.slug)
        # After commit, the session is empty.
        self.assert_false(ent in self._session)
        self.assert_equal(len(self._session.query(_MyEntity).all()), 1)
        # Test loading by ID and slug.
        fetched_ent0 = self._session.get_by_id(_MyEntity, ent.id)
        self.assert_equal(fetched_ent0.slug, ent.slug)
        fetched_ent1 = self._session.get_by_slug(_MyEntity, ent.slug)
        self.assert_equal(fetched_ent1.id, ent.id)
        # We get a clone when we load an entity from the session.
        self.assert_false(fetched_ent0 is ent)
        # Once loaded, we always get the same entity.
        self.assert_true(fetched_ent0 is fetched_ent1)
        self._session.remove(_MyEntity, fetched_ent0)
        self.assert_equal(len(self._session.query(_MyEntity).all()), 0)
        self.assert_is_none(self._session.get_by_id(_MyEntity, ent.id))
        self.assert_is_none(self._session.get_by_slug(_MyEntity, ent.slug))

    def test_remove_entity_not_in_session_raises_error(self):
        ent = _MyEntity()
        self.assert_raises(ValueError, self._session.remove, _MyEntity, ent)

    def test_add_deleted(self):
        ent = _MyEntity()
        self._session.add(_MyEntity, ent)
        self._session.commit()
        self._session.remove(_MyEntity, ent)
        self._session.add(_MyEntity, ent)

    def test_update_entity_not_in_session_raises_error(self):
        ent = _MyEntity()
        self.assert_raises(ValueError, self._session.update, _MyEntity, ent)

    def test_get_entity_not_in_session(self):
        self.assert_is_none(self._session.get_by_id(_MyEntity, '-1'))


class JoinedTransactionMemorySessionTestCase(_MemorySessionTestCaseBase):
    def set_up(self):
        _MemorySessionTestCaseBase.set_up(self)
        self._repository = Repository('DUMMY', Aggregate,
                                      join_transaction=True)
        self._session = Session(self._repository)


class TransactionLessMemorySessionTestCase(_MemorySessionTestCaseBase):
    def set_up(self):
        _MemorySessionTestCaseBase.set_up(self)
        self._repository = Repository('DUMMY', Aggregate)
        self._session = Session(self._repository)

    def test_references(self):
        ent = _MyEntity()
        self._session.add(_MyEntity, ent)
        self.assert_equal(len(self._session.query(_MyEntity).all()), 1)
        # Even with the last external ref gone, the cache should hold a
        # reference to the entities it manages.
        del ent
        gc.collect()
        self.assert_equal(len(self._session.query(_MyEntity).all()), 1)

    def test_id_generation(self):
        ent1 = _MyEntity()
        self._session.add(_MyEntity, ent1)
        self._session.commit()
        self.assert_is_not_none(ent1.id)
        ent2 = _MyEntity()
        self._session.add(_MyEntity, ent2)
        self._session.commit()
        self.assert_is_not_none(ent2.id)
        # entity IDs can be sorted by creation time.
        self.assert_true(ent2.id > ent1.id)

    def test_with_id_without_slug(self):
        ent = _MyEntityNoneSlug(id=0)
        self._session.add(_MyEntityNoneSlug, ent)
        self.assert_true(self._session.get_by_id(_MyEntityNoneSlug, 0) is ent)

    def test_without_id_with_slug(self):
        ent = _MyEntityWithSlug()
        self._session.add(_MyEntityWithSlug, ent)
        self.assert_true(self._session.get_by_slug(_MyEntityWithSlug, 'slug')
                         is ent)

    def test_duplicate_id_raises_error(self):
        ent_id = new_entity_id()
        ent1 = _MyEntity(id=ent_id)
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntity(id=ent_id)
        self.assert_raises(ValueError, self._session.add, _MyEntity, ent2)

    def test_duplicate_slug_raises_error(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntityWithSlug, ent1)
        ent2 = _MyEntityWithSlug()
        self.assert_raises(ValueError,
                           self._session.add, _MyEntityWithSlug, ent2)

    def test_cope_with_numeric_id(self):
        ent = _MyEntity(id=0)
        self._session.add(_MyEntity, ent)
        self.assert_equal(self._session.get_by_id(_MyEntity, ent.id).id,
                          ent.id)
        self.assert_equal(self._session.get_by_slug(_MyEntity, ent.slug).id,
                          ent.id)

    def test_repeated_add_remove(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        self.assert_true(self._session.get_by_slug(_MyEntity, ent1.slug)
                         is ent1)
        self._session.remove(_MyEntity, ent1)
        self.assert_is_none(self._session.get_by_slug(_MyEntity, ent1.slug))
        ent2 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent2)
        self.assert_true(self._session.get_by_slug(_MyEntity, ent2.slug)
                         is ent2)
        self._session.remove(_MyEntity, ent2)
        self.assert_is_none(self._session.get_by_slug(_MyEntity, ent2.slug))

    def test_remove_(self):
        ent = _MyEntity()
        self._session.add(_MyEntity, ent)
        self._session.remove(_MyEntity, ent)
        self.assert_equal(len(self._session.query(_MyEntity).all()), 0)

    def test_add_remove_add(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntityWithSlug, ent1)
        self.assert_true(ent1 in self._session)
        self._session.remove(_MyEntityWithSlug, ent1)
        self.assert_false(ent1 in self._session)
        self._session.add(_MyEntityWithSlug, ent1)
        self.assert_true(ent1 in self._session)

    def test_update_without_id_raises_error(self):
        ent1 = _MyEntity(id=0)
        self._session.add(_MyEntity, ent1)
        self._session.commit()
        # Re-load.
        ent2 = self._session.load(_MyEntity, ent1)
        ent2.id = None
        with self.assert_raises(ValueError) as cm:
            self._session.commit()
        exc_msg = 'Entity ID must not be None.'
        self.assert_equal(cm.exception.message, exc_msg)

    def test_update_with_different_slug(self):
        ent_id = 0
        ent1 = _MyEntityWithSlug(id=ent_id)
        self._session.add(_MyEntityWithSlug, ent1)
        ent2 = self._session.get_by_id(_MyEntityWithSlug, ent_id)
        text = 'foo'
        ent2.slug = text
        self._session.commit()
        ent3 = \
            self._session.query(_MyEntityWithSlug).filter_by(slug=text).one()
        self.assert_equal(ent3.id, ent_id)

    def test_failing_commit_duplicate_id(self):
        ent1 = _MyEntity()
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntity()
        self._session.add(_MyEntity, ent2)
        self.assert_is_none(ent1.id)
        self.assert_is_none(ent2.id)
        ent2.id = ent1.id = 0
        self.assert_raises(ValueError, self._session.commit)

    def test_failing_flush_duplicate_slug(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntityWithSlug()
        ent2.slug = None
        self._session.add(_MyEntity, ent2)
        ent2.slug = 'slug'
        self.assert_raises(ValueError, self._session.commit)

    def test_find_added_by_id(self):
        ent1 = _MyEntityWithSlug(id=0)
        self._session.add(_MyEntity, ent1)
        ent2 = self._session.get_by_id(_MyEntity, ent1.id)
        self.assert_is_not_none(ent2)
        self.assert_equal(ent1.id, ent2.id)

    def test_find_added_by_slug(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        ent2 = self._session.get_by_slug(_MyEntity, ent1.slug)
        self.assert_is_not_none(ent2)
        self.assert_equal(ent1.id, ent2.id)

    def test_find_added_with_none_slug_by_slug(self):
        ent1 = _MyEntityNoneSlug()
        self._session.add(_MyEntity, ent1)
        ent1.slug = 'testslug'
        ent2 = self._session.get_by_slug(_MyEntity, ent1.slug)
        self.assert_is_not_none(ent2)
        self.assert_equal(ent1.id, ent2.id)

    def test_update(self):
        ent1 = _MyEntity(id=0)
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntity()
        ent2.id = ent1.id
        my_attr_value = 1
        ent2.my_attr = my_attr_value
        self._session.update(_MyEntity, ent2)
        ent3 = self._session.get_by_id(_MyEntity, ent1.id)
        self.assert_is_not_none(ent3)
        self.assert_equal(ent3.id, ent1.id)
        self.assert_equal(ent3.my_attr, my_attr_value)


class _MyEntity(Entity):
    my_attr = None


class _MyEntityWithSlug(Entity):
    slug = 'slug'


class _MyEntityNoneSlug(Entity):
    slug = None
