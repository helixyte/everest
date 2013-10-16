"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 14, 2013.
"""
from everest.entities.attributes import get_domain_class_attribute_iterator
from everest.entities.attributes import get_domain_class_attribute_names
from everest.utils import get_nested_attribute
from everest.utils import set_nested_attribute
from pyramid.compat import iteritems_
from weakref import ref

__docformat__ = 'reStructuredText en'
__all__ = ['ENTITY_STATES',
           'EntityStateManager',
           ]


class ENTITY_STATES(object):
    """
    Entity state flags.
    """
    CLEAN = 'CLEAN'
    NEW = 'NEW'
    DELETED = 'DELETED'
    DIRTY = 'DIRTY'


class EntityStateManager(object):
    """
    Manager for entity state and state data.

    Initially, an object is marked as NEW (freshly instantiated) or CLEAN
    (freshly fetched from repository).

    Only a weak reference to the tracked object is stored to avoid circular
    references.

    Not all state transitions are allowed.
    """
    # FIXME: Need a proper state diagram here or drop tracking alltogether.
    __allowed_transitions = set([(None, ENTITY_STATES.NEW),
                                 (None, ENTITY_STATES.CLEAN),
                                 (None, ENTITY_STATES.DELETED),
                                 (ENTITY_STATES.NEW, ENTITY_STATES.CLEAN),
                                 (ENTITY_STATES.NEW, ENTITY_STATES.DELETED),
                                 (ENTITY_STATES.DELETED, ENTITY_STATES.CLEAN),
                                 (ENTITY_STATES.DELETED, ENTITY_STATES.NEW),
                                 (ENTITY_STATES.CLEAN, ENTITY_STATES.DIRTY),
                                 (ENTITY_STATES.CLEAN, ENTITY_STATES.DELETED),
                                 (ENTITY_STATES.CLEAN, ENTITY_STATES.NEW),
                                 (ENTITY_STATES.DIRTY, ENTITY_STATES.CLEAN),
                                 (ENTITY_STATES.DIRTY, ENTITY_STATES.DELETED),
                                 ])

    def __init__(self, entity_class, entity, unit_of_work):
        self.__entity_class = entity_class
        self.__obj_ref = ref(entity)
        self.__uow_ref = ref(unit_of_work)
        self.__state = None
        self.__last_state = self.get_state_data(entity_class, entity)

    @classmethod
    def manage(cls, entity_class, entity, unit_of_work):
        """
        Manages the given entity under the given Unit Of Work.

        If `entity` is already managed by the given Unit Of Work, nothing
        is done.

        :raises ValueError: If the given entity is already under management
          by a different Unit Of Work.
        """
        if hasattr(entity, '__everest__'):
            if not unit_of_work is entity.__everest__.unit_of_work:
                raise ValueError('Trying to register an entity that has been '
                                 'registered with another session!')
        else:
            entity.__everest__ = cls(entity_class, entity, unit_of_work)

    @classmethod
    def release(cls, entity, unit_of_work):
        """
        Releases the given entity from management under the given Unit Of
        Work.

        :raises ValueError: If `entity` is not managed at all or is not
          managed by the given Unit Of Work.
        """
        if not hasattr(entity, '__everest__'):
            raise ValueError('Trying to unregister an entity that has not '
                             'been registered yet!')
        elif not unit_of_work is entity.__everest__.unit_of_work:
            raise ValueError('Trying to unregister an entity that has been '
                             'registered with another session!')
        delattr(entity, '__everest__')

    @classmethod
    def set_state(cls, entity, state):
        """
        Sets the state flag of the given entity to the given value.

        :raises ValueError: If `entity` is not managed.
        """
        if not hasattr(entity, '__everest__'):
            raise ValueError('Trying to mark an unregistered entity as '
                             '%s!' % state)
        entity.__everest__.state = state

    @classmethod
    def get_state(cls, entity):
        """
        Returns the state flag of the given entity.

        :raises ValueError: If `entity` is not managed.
        """
        if not hasattr(entity, '__everest__'):
            raise ValueError('Trying to get the state of an unregistered '
                             'entity!')
        return entity.__everest__.state

    @classmethod
    def transfer_state_data(cls, entity_class, source_entity, target_entity):
        """
        Transfers instance state data from the given source entity to the
        given target entity.
        """
        state = cls.get_state_data(entity_class, source_entity)
        cls.set_state_data(entity_class, state, target_entity)

    @classmethod
    def get_state_data(cls, entity_class, entity):
        """
        Returns state data for the given entity of the given class.

        :param entity: Entity to obtain the state data from.
        :returns: Dictionary mapping attributes to attribute values.
        """
        attrs = get_domain_class_attribute_iterator(entity_class)
        return dict([(attr,
                      get_nested_attribute(entity, attr.entity_attr))
                     for attr in attrs])

    @classmethod
    def set_state_data(cls, entity_class, data, entity):
        """
        Sets the given state data on the given entity of the given class.

        :param data: State data to set.
        :type data: Dictionary mapping attributes to attribute values.
        :param entity: Entity to receive the state data.
        """
        attr_names = get_domain_class_attribute_names(entity_class)
        nested_items = []
        for attr, new_attr_value in iteritems_(data):
            if not attr.entity_attr in attr_names:
                raise ValueError('Can not set attribute "%s" for entity '
                                 '"%s".' % (attr.entity_attr, entity_class))
            if '.' in attr.entity_attr:
                nested_items.append((attr, new_attr_value))
                continue
            else:
                setattr(entity, attr.entity_attr, new_attr_value)
        for attr, new_attr_value in nested_items:
            try:
                set_nested_attribute(entity, attr.entity_attr, new_attr_value)
            except AttributeError, exc:
                if not new_attr_value is None:
                    raise exc

    def __get_state(self):
        state = self.__state
        if state == ENTITY_STATES.CLEAN:
            if self.get_state_data(self.__entity_class, self.__obj_ref()) \
               != self.__last_state:
                state = ENTITY_STATES.DIRTY
        return state

    def __set_state(self, state):
        if not (self.__get_state(), state) in self.__allowed_transitions:
            raise ValueError('Invalid state transition %s -> %s.'
                             % (self.__state, state))
        self.__state = state
        if state == ENTITY_STATES.CLEAN:
            self.__last_state = self.get_state_data(self.__entity_class,
                                                    self.__obj_ref())

    #: The current state. One of the `ENTITY_STATES` constants.
    state = property(__get_state, __set_state)

    @property
    def unit_of_work(self):
        return self.__uow_ref()

