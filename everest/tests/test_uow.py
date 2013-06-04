"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 10, 2013.
"""
from everest.entities.base import Entity
from everest.repositories.memory.uow import EntityStateManager
from everest.repositories.memory.uow import OBJECT_STATES
from everest.repositories.memory.uow import UnitOfWork
from everest.testing import Pep8CompliantTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['UnitOfWorkTestCase',
           ]


class UnitOfWorkTestCase(Pep8CompliantTestCase):
    def set_up(self):
        self._uow = UnitOfWork()

    def test_basics(self):
        ent = _MyEntity()
        self._uow.register_new(_MyEntity, ent)
        self.assert_equal(EntityStateManager.get_state(ent),
                          OBJECT_STATES.NEW)
        self.assert_equal([item[1] for item in self._uow.iterator()],
                          [ent])
        self.assert_equal(list(self._uow.get_new(_MyEntity)), [ent])
        self._uow.mark_clean(_MyEntity, ent)
        self.assert_equal(list(self._uow.get_clean(_MyEntity)), [ent])
        self._uow.mark_dirty(_MyEntity, ent)
        self.assert_equal(list(self._uow.get_dirty(_MyEntity)), [ent])
        self._uow.mark_deleted(_MyEntity, ent)
        self.assert_equal(list(self._uow.get_deleted(_MyEntity)), [ent])
        self._uow.unregister(_MyEntity, ent)
        self.assert_equal(list(self._uow.iterator()), [])
        self._uow.reset()

    def test_get_state_unregistered_fails(self):
        ent = _MyEntity()
        with self.assert_raises(ValueError) as cm:
            EntityStateManager.get_state(ent)
        msg = 'Trying to get the state of an unregistered entity'
        self.assert_true(str(cm.exception).startswith(msg))

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

    def test_mark_deleted_as_clean(self):
        ent = _MyEntity()
        self._uow.register_new(_MyEntity, ent)
        self._uow.mark_deleted(_MyEntity, ent)
        with self.assert_raises(ValueError) as cm:
            self._uow.mark_clean(_MyEntity, ent)
        msg = 'Invalid state transition'
        self.assert_true(str(cm.exception).startswith(msg))


class _MyEntity(Entity):
    pass
