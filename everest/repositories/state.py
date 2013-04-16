"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 14, 2013.
"""
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
    __allowed_transitions = ((None, ENTITY_STATES.NEW),
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
                             )

    def __init__(self, entity, unit_of_work):
        self.__obj_ref = ref(entity)
        self.__uow_ref = ref(unit_of_work)
        self.__state = None
        self.__last_state = self._get_state_data(entity)

    @classmethod
    def clone(cls, entity):
        """
        Returns a clone (=copy with identical state) of the given entity.
        """
        clone = object.__new__(entity.__class__)
        data = cls._get_state_data(entity)
        cls._set_state_data(clone, data)
        return clone

    @classmethod
    def manage(cls, entity, unit_of_work):
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
            entity.__everest__ = cls(entity, unit_of_work)

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
    def transfer_state_data(cls, source_entity, target_entity):
        """
        Transfers instance state data from the given source entity to the
        given target entity.
        """
        state = cls._get_state_data(source_entity)
        cls._set_state_data(target_entity, state)

    @classmethod
    def _get_state_data(cls, entity):
        # FIXME: This is a very simple implementation of capturing state.
        return dict([(attr_name, attr_value)
                     for attr_name, attr_value in entity.__dict__.iteritems()
                     if not attr_name.startswith('_')])

    @classmethod
    def _set_state_data(cls, entity, data):
        # FIXME: This is a very simple implementation of capturing state.
        for attr_name, attr_value in data.iteritems():
            # Avoid calling setattr here as that might trigger custom
            # callbacks.
            entity.__dict__[attr_name] = attr_value

    def __get_state(self):
        state = self.__state
        if state == ENTITY_STATES.CLEAN:
            if self._get_state_data(self.__obj_ref()) != self.__last_state:
                state = ENTITY_STATES.DIRTY
        return state

    def __set_state(self, state):
        if not (self.__get_state(), state) in self.__allowed_transitions:
            raise ValueError('Invalid state transition %s -> %s.'
                             % (self.__state, state))
        self.__state = state
        if state == ENTITY_STATES.CLEAN:
            self.__last_state = self._get_state_data(self.__obj_ref())

    #: The current state. One of the `ENTITY_STATES` constants.
    state = property(__get_state, __set_state)

    @property
    def unit_of_work(self):
        return self.__uow_ref()

