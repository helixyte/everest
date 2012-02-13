"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 13, 2012.
"""

from everest.testing import Pep8CompliantTestCase
from everest.resources.persisters import InMemorySession
from everest.resources.persisters import DummyPersister
from everest.entities.base import Entity

__docformat__ = 'reStructuredText en'

__author__ = 'F Oliver Gathmann'
__date__ = '$Date: $'
__revision__ = '$Rev: $'
__source__ = '$URL::                                                        #$'

__all__ = ['InMemorySessionTestCase',
           ]


class InMemorySessionTestCase(Pep8CompliantTestCase):
    _session = None

    def set_up(self):
        Pep8CompliantTestCase.set_up(self)
        prst = DummyPersister('DUMMY')
        self._session = InMemorySession(prst)

    def test_with_autoflush(self):
        class MyEntity(Entity):
            pass
        ent = MyEntity()
        self.assert_is_none(ent.id)
        self.assert_is_none(ent.slug)
        self._session.add(MyEntity, ent)
        self.assert_true(ent in self._session.get_all(MyEntity))
        # get_all triggered flush - we should have ID & slug now.
        self.assert_is_not_none(ent.id)
        self.assert_is_not_none(ent.slug)
        self.assert_equal(len(self._session.get_all(MyEntity)), 1)
        self.assert_true(self._session.get_by_id(MyEntity, ent.id) is ent)
        self.assert_true(self._session.get_by_slug(MyEntity, ent.slug) is ent)
        self._session.remove(MyEntity, ent)
        self.assert_equal(len(self._session.get_all(MyEntity)), 0)
        self.assert_is_none(self._session.get_by_id(MyEntity, ent.id))
        self.assert_is_none(self._session.get_by_slug(MyEntity, ent.slug))

    def test_without_autoflush(self):
        class MyEntity(Entity):
            pass
        ent = MyEntity()
        self._session.autoflush = False
        self._session.add(MyEntity, ent)
        self.assert_true(ent in self._session.get_all(MyEntity))
        # no autoflush - ID & slug should still be none
        self.assert_is_none(ent.id)
        self.assert_is_none(ent.slug)
        #
        self._session.flush()
        self.assert_is_not_none(ent.id)
        self.assert_is_not_none(ent.slug)

    def test_references(self):
        class MyEntity(Entity):
            pass
        ent = MyEntity()
        self._session.add(MyEntity, ent)
        self._session.flush()
        self.assert_equal(len(self._session.get_all(MyEntity)), 1)
        # With the last reference to the entity gone, the entity should vanish
        # from the cache.
        del ent
        self.assert_equal(len(self._session.get_all(MyEntity)), 0)

    def test_id_generation(self):
        class MyEntity(Entity):
            pass
        ent1 = MyEntity(id=5)
        self._session.add(MyEntity, ent1)
        ent2 = MyEntity()
        self._session.add(MyEntity, ent2)
        self._session.flush()
        self.assert_equal(ent2.id, 6)

    def test_with_id_without_slug_raises_error(self):
        class MyEntity(Entity):
            slug = None
        ent = MyEntity(id=0)
        self.assert_raises(ValueError, self._session.add, MyEntity, ent)

    def test_without_id_with_slug(self):
        class MyEntity(Entity):
            slug = 'slug'
        ent = MyEntity()
        self._session.add(MyEntity, ent)
        self.assert_true(self._session.get_by_slug(MyEntity, 'slug') is ent)

    def test_duplicate_id_raises_error(self):
        class MyEntity(Entity):
            pass
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        # Trigger autoflush to create ID.
        self._session.flush()
        ent2 = MyEntity(id=0)
        self.assert_raises(ValueError, self._session.add, MyEntity, ent2)

    def test_duplicate_slug_raises_error(self):
        class MyEntity(Entity):
            slug = 'slug'
        ent1 = MyEntity()
        self._session.add(MyEntity, ent1)
        ent2 = MyEntity()
        self.assert_raises(ValueError, self._session.add, MyEntity, ent2)

    def test_cope_with_string_id(self):
        class MyEntity(Entity):
            pass
        ent = MyEntity(id='0')
        self._session.add(MyEntity, ent)
        self.assert_true(self._session.get_by_id(MyEntity, ent.id) is ent)
        self.assert_true(self._session.get_by_slug(MyEntity, ent.slug) is ent)

    def test_remove_without_id(self):
        class MyEntity(Entity):
            pass
        ent = MyEntity()
        self._session.add(MyEntity, ent)
        self._session.remove(MyEntity, ent)
        self.assert_equal(len(self._session.get_all(MyEntity)), 0)

    def test_remove_entity_not_in_session_raises_error(self):
        class MyEntity(Entity):
            pass
        ent = MyEntity()
        self.assert_raises(KeyError, self._session.remove, MyEntity, ent)
