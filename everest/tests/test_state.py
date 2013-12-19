"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 19, 2013.
"""
from everest.testing import EntityTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.entities import MyEntityChild
from everest.repositories.state import EntityState
from everest.resources.descriptors import terminal_attribute
from mock import MagicMock

__docformat__ = 'reStructuredText en'
__all__ = ['EntityStateTestCase',
           ]


class EntityStateTestCase(EntityTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_state_data(self):
        data = dict(text='FOO',
                    number=-1,
                    parent=MyEntityParent(),
                    children=[MyEntityChild()])
        entity = MyEntity(**data)
        # We don't want to test the required unit of work here.
        uow = MagicMock()
        self.assert_raises(ValueError, EntityState.get_state, entity)
        entity.__everest__ = EntityState(entity, uow)
        state_data = EntityState.get_state(entity).data
        for attr, value in state_data.items():
            if attr.resource_attr == 'number':
                number_attr = attr
            elif attr.resource_attr == 'parent':
                parent_attr = attr
            elif attr.resource_attr == 'parent_text':
                parent_text_attr = attr
            if attr.resource_attr in data:
                self.assert_equal(value, data[attr.resource_attr])
        new_number = -2
        state_data[number_attr] = new_number
        EntityState.get_state(entity).data = state_data
        self.assert_equal(entity.number, new_number)
        new_entity = MyEntity()
        self.assert_not_equal(new_entity.number, new_number)
        new_entity.__everest__ = EntityState(new_entity, uow)
        EntityState.transfer_state_data(entity, new_entity)
        self.assert_equal(new_entity.number, new_number)
        # Make setting invalid attribute fail.
        invalid_number_attr = terminal_attribute(str, 'grmbl')
        del state_data[number_attr]
        state_data[invalid_number_attr] = -2
        with self.assert_raises(ValueError) as cm:
            EntityState.get_state(entity).data = state_data
        self.assert_true(cm.exception.args[0].startswith('Can not set'))
        # Make set nested attribute fail.
        entity.parent = None
        del state_data[invalid_number_attr]
        del state_data[parent_attr]
        state_data[parent_text_attr] = 'FOO PARENT'
        state = EntityState.get_state(entity)
        self.assert_raises(AttributeError, setattr, state, 'data', state_data)


