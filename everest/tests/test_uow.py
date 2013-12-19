"""

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 10, 2013.
"""
from everest.entities.base import Entity
from everest.repositories.state import ENTITY_STATUS
from everest.repositories.state import EntityState
from everest.repositories.uow import UnitOfWork
from everest.testing import Pep8CompliantTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['UnitOfWorkTestCase',
           ]


class UnitOfWorkTestCase(Pep8CompliantTestCase):
    def set_up(self):
        self._uow = UnitOfWork()

    def test_basics(self):
        ent = _MyEntity(id=0)
        self._uow.register_new(_MyEntity, ent)
        self.assert_equal(EntityState.get_state(ent).status,
                          ENTITY_STATUS.NEW)
        self.assert_equal([item.entity for item in self._uow.iterator()],
                          [ent])
        self.assert_equal(list(self._uow.get_new(_MyEntity)), [ent])
        self._uow.mark_clean(ent)
        self.assert_equal(list(self._uow.get_clean(_MyEntity)), [ent])
        self._uow.mark_dirty(ent)
        self.assert_equal(list(self._uow.get_dirty(_MyEntity)), [ent])
        self._uow.mark_deleted(ent)
        self.assert_equal(list(self._uow.get_deleted(_MyEntity)), [ent])
        self._uow.unregister(_MyEntity, ent)
        self.assert_equal(list(self._uow.iterator()), [])
        self._uow.reset()

    def test_get_state_unregistered_fails(self):
        ent = _MyEntity()
        with self.assert_raises(ValueError) as cm:
            EntityState.get_state(ent)
        msg = 'Trying to obtain state for un-managed entity'
        self.assert_true(cm.exception.args[0].startswith(msg))

    def test_is_marked_unregistered(self):
        ent = _MyEntity()
        self.assert_false(self._uow.is_marked_persisted(ent))
        self.assert_false(self._uow.is_marked_pending(ent))

    def test_mark_unregistered_fails(self):
        ent = _MyEntity()
        with self.assert_raises(ValueError) as cm:
            self._uow.mark_dirty(ent)
        msg = 'Trying to obtain state for un-managed entity'
        self.assert_true(cm.exception.args[0].startswith(msg))

    def test_release_unregistered_fails(self):
        ent = _MyEntity()
        with self.assert_raises(ValueError) as cm:
            self._uow.unregister(_MyEntity, ent)
        msg = 'Trying to unregister an entity that has not been'
        self.assert_true(str(cm.exception).startswith(msg))

    def test_registered_with_other_uow_fails(self):
        ent = _MyEntity()
        uow = UnitOfWork()
        uow.register_new(_MyEntity, ent)
        with self.assert_raises(ValueError) as cm1:
            self._uow.register_new(_MyEntity, ent)
        msg1 = 'Trying to register an entity that has been'
        self.assert_true(str(cm1.exception).startswith(msg1))
        with self.assert_raises(ValueError) as cm2:
            self._uow.unregister(_MyEntity, ent)
        msg2 = 'Trying to unregister an entity that has been'
        self.assert_true(str(cm2.exception).startswith(msg2))

    def test_mark_deleted_as_dirty(self):
        ent = _MyEntity()
        self._uow.register_new(_MyEntity, ent)
        self._uow.mark_deleted(ent)
        with self.assert_raises(ValueError) as cm:
            self._uow.mark_dirty(ent)
        msg = 'Invalid status transition'
        self.assert_true(str(cm.exception).startswith(msg))

    def test_check_unregistered_is_marked_new(self):
        ent = _MyEntity()
        self.assert_false(self._uow.is_marked_new(ent))

    def test_mark_deleted_as_new(self):
        ent = _MyEntity(id=0)
        self._uow.register_deleted(_MyEntity, ent)
        self._uow.mark_new(ent)


class _MyEntity(Entity):
    __everest_attributes__ = {}
