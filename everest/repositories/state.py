"""
Entity state management.

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
__all__ = ['ENTITY_STATUS',
           'EntityState',
           ]


class ENTITY_STATUS(object):
    """
    Entity status flags.
    """
    CLEAN = 'CLEAN'
    NEW = 'NEW'
    DELETED = 'DELETED'
    DIRTY = 'DIRTY'


class EntityState(object):
    """
    Tracks entity status, persistency, and state data.

    Initially, an object is marked as NEW (freshly instantiated) or CLEAN
    (freshly fetched from repository).

    Only a weak reference to the tracked object is stored to avoid circular
    references.

    Not all status transitions are allowed.
    """
    # FIXME: Need a proper state diagram here or drop tracking alltogether.
    __allowed_transitions = set([(None, ENTITY_STATUS.NEW),
                                 (None, ENTITY_STATUS.CLEAN),
                                 (None, ENTITY_STATUS.DELETED),
                                 (ENTITY_STATUS.NEW, ENTITY_STATUS.CLEAN),
                                 (ENTITY_STATUS.NEW, ENTITY_STATUS.DELETED),
                                 (ENTITY_STATUS.DELETED, ENTITY_STATUS.CLEAN),
                                 (ENTITY_STATUS.DELETED, ENTITY_STATUS.NEW),
                                 (ENTITY_STATUS.CLEAN, ENTITY_STATUS.DIRTY),
                                 (ENTITY_STATUS.CLEAN, ENTITY_STATUS.DELETED),
                                 (ENTITY_STATUS.CLEAN, ENTITY_STATUS.NEW),
                                 (ENTITY_STATUS.DIRTY, ENTITY_STATUS.CLEAN),
                                 (ENTITY_STATUS.DIRTY, ENTITY_STATUS.DELETED),
                                 ])

    def __init__(self, entity, unit_of_work):
        self.__entity_ref = ref(entity)
        self.__uow_ref = ref(unit_of_work)
        self.__status = None
        self.__clean_data = self.data
        #: Flag indicating if this state has been flushed to the backend.
        self.is_persisted = False

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
    def get_state(cls, entity):
        try:
            return entity.__everest__
        except AttributeError:
            raise ValueError('Trying to obtain state for un-managed entity.')

    @classmethod
    def get_state_data(cls, entity):
        """
        Returns the state data for the given entity.

        This also works for unmanaged entities.
        """
        attrs = get_domain_class_attribute_iterator(type(entity))
        return dict([(attr,
                      get_nested_attribute(entity, attr.entity_attr))
                     for attr in attrs
                     if not attr.entity_attr is None])

    @classmethod
    def set_state_data(cls, entity, data):
        """
        Sets the state data for the given entity to the given data.

        This also works for unmanaged entities.
        """
        attr_names = get_domain_class_attribute_names(type(entity))
        nested_items = []
        for attr, new_attr_value in iteritems_(data):
            if not attr.entity_attr in attr_names:
                raise ValueError('Can not set attribute "%s" for entity '
                                 '"%s".' % (attr.entity_attr, entity))
            if '.' in attr.entity_attr:
                nested_items.append((attr, new_attr_value))
                continue
            else:
                setattr(entity, attr.entity_attr, new_attr_value)
        for attr, new_attr_value in nested_items:
            try:
                set_nested_attribute(entity, attr.entity_attr, new_attr_value)
            except AttributeError as exc:
                if not new_attr_value is None:
                    raise exc

    @classmethod
    def transfer_state_data(cls, source_entity, target_entity):
        """
        Transfers instance state data from the given source entity to the
        given target entity.
        """
        state_data = cls.get_state_data(source_entity)
        cls.set_state_data(target_entity, state_data)

    def __get_data(self):
        """
        Returns state data for the given entity of the given class.

        :param entity: Entity to obtain the state data from.
        :returns: Dictionary mapping attributes to attribute values.
        """
        ent = self.__entity_ref()
        return self.get_state_data(ent)

    def __set_data(self, data):
        """
        Sets the given state data on the given entity of the given class.

        :param data: State data to set.
        :type data: Dictionary mapping attributes to attribute values.
        :param entity: Entity to receive the state data.
        """
        ent = self.__entity_ref()
        self.set_state_data(ent, data)

    data = property(__get_data, __set_data)

    @property
    def clean_data(self):
        return self.__clean_data

    def __get_status(self):
        status = self.__status
        if status == ENTITY_STATUS.CLEAN:
            if self.data != self.__clean_data:
                status = ENTITY_STATUS.DIRTY
        return status

    def __set_status(self, status):
        if not (self.__get_status(), status) in self.__allowed_transitions:
            raise ValueError('Invalid status transition %s -> %s.'
                             % (self.__status, status))
        self.__status = status
        if status == ENTITY_STATUS.CLEAN:
            self.__clean_data = self.data

    #: The current status. One of the `ENTITY_STATUS` constants.
    status = property(__get_status, __set_status)

    @property
    def unit_of_work(self):
        return self.__uow_ref()

    @property
    def entity(self):
        return self.__entity_ref()

