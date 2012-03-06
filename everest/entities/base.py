"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Entity base classes.

Created on May 12, 2011.
"""

from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['Aggregate',
           'Entity',
           ]


class Entity(object):
    """
    Abstract base class for all model entities.

    All entities have an ID which is used as the default value for equality
    comparison. The object may be initialized without an ID.
    """
    implements(IEntity)

    id = None

    def __init__(self, id=None): # redefining id pylint: disable=W0622
        if self.__class__ is Entity:
            raise NotImplementedError('Abstract class.')
        self.id = id

    @property
    def slug(self):
        """
        Returns a human-readable and URL-compatible string that is unique
        within all siblings of this entity.
        """
        return not self.id is None and str(self.id) or None

    @classmethod
    def create_from_data(cls, data):
        return cls(**data)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)


class Aggregate(object):
    """
    Abstract base class for all aggregates.

    An aggregate is an accessor for a set of entities of the same type which 
    are held in some repository. 
    
    The wrapped entity set may be a "root" set of all entities in the 
    repository or a "relation" set defined by a relationship to entities of 
    some other type.

    Supports filtering, sorting, slicing, counting, iteration as well as
    retrieving, adding and removing entities.
    """
    implements(IAggregate)

    def __init__(self, entity_class, session_factory):
        """
        Constructor:

        :param entity_class: the entity class (type) of the entities in this
            aggregate.
        :type entity_class: a class implementing
            :class:`everest.entities.interfaces.IEntity`
        :param session: Session object.
        """
        if self.__class__ is Aggregate:
            raise NotImplementedError('Abstract class.')
        #: Entity class (type) of the entities in this aggregate.
        self.entity_class = entity_class
        #: The session.
        self._session_factory = session_factory
        #: Relationship of entities in this aggregate to a parent entity.
        self._relationship = None
        #: Specification for filtering
        #: (:class:`everest.querying.specifications.FilterSpecification`).
        #: Attribute names in this specification are relative to the entity. 
        self._filter_spec = None
        #: Specification for ordering
        #: (:class:`everest.querying.specifications.OrderSpecification`).
        #: Attribute names in this specification are relative to the entity. 
        self._order_spec = None
        #: Key for slicing. (:type:`slice`).
        self._slice_key = None

    @classmethod
    def create(cls, entity_class, session_factory):
        """
        Factory class method to create a new aggregate.
        """
        return cls(entity_class, session_factory)

    def clone(self):
        """
        Returns a clone of this aggregate.
        """
        clone = self.__class__.create(self.entity_class, self._session_factory)
        clone._relationship = self._relationship
        clone._filter_spec = self._filter_spec
        clone._order_spec = self._order_spec
        clone._slice_key = self._slice_key
        return clone

    def count(self):
        """
        Returns the total number of entities in the underlying aggregate.
        If specified, filter specs are applied. A specified slice key is
        ignored.

        :returns: number of aggregate members (:class:`int`)
        """
        raise NotImplementedError('Abstract method')

    def get_by_id(self, id_key):
        """
        Returns an entity by ID from the underlying aggregate or `None` if
        the entity is not found.

        :note: if a filter is set which matches the requested entity, it
          will not be found.
        :param id_key: ID value to look up
        :type id_key: `int` or `str`
        :raises: :class:`everest.exceptions.DuplicateException` if more than
          one entity is found for the given ID value. 
        :returns: specified entity or `None`

        Returns a single entity from the underlying aggregate by ID.
        """
        raise NotImplementedError('Abstract method')

    def get_by_slug(self, slug):
        """
        Returns an entity by slug or `None` if the entity is not found.

        :param slug: slug value to look up
        :type slug: `str`
        :raises: :class:`everest.exceptions.DuplicateException` if more than
          one entity is found for the given ID value. 
        :returns: entity or `None`
        """
        raise NotImplementedError('Abstract method')

    def iterator(self):
        """
        Returns an iterator for the entities contained in the underlying
        aggregate.

        If specified, filter, order, and slice settings are applied.

        :returns: an iterator for the aggregate entities
        """
        raise NotImplementedError('Abstract method')

    def add(self, entity):
        """
        Adds an entity to the aggregate.

        If the entity has an ID, it must be unique within the aggregate.

        :param entity: entity (domain object) to add
        :type entity: object implementing
          :class:`everest.entities.interfaces.IEntity`
        :raise ValueError: if an entity with the same ID exists
        """
        raise NotImplementedError('Abstract method')

    def remove(self, entity):
        """
        Removes an entity from the aggregate.

        :param entity: entity (domain object) to remove
        :type entity: object implementing
          :class:`everest.entities.interfaces.IEntity`
        :raise ValueError: entity was not found
        """
        raise NotImplementedError('Abstract method')

    def set_relationship(self, relationship):
        """
        Sets a relationship for this aggregate.
        
        :param relationship: 
            instance of :class:`thelma.relationsip.Relationship`.
        """
        self._relationship = relationship

    @property
    def _session(self):
        return self._session_factory()

    def _get_filter(self):
        #: Returns the filter specification for this aggregate.
        return self._filter_spec

    def _set_filter(self, filter_spec):
        #: Sets the filter specification for this aggregate.
        self._filter_spec = filter_spec
        self._apply_filter()

    filter = property(_get_filter, _set_filter)

    def _get_order(self):
        #: Returns the order specification for this aggregate.
        return self._order_spec

    def _set_order(self, order_spec):
        #: Sets the order specification for this aggregate.
        self._order_spec = order_spec
        self._apply_order()

    order = property(_get_order, _set_order)

    def _get_slice(self):
        #: Returns the slice key for this aggregate.
        return self._slice_key

    def _set_slice(self, slice_key):
        #: Sets the slice key for this aggregate. Filter and order specs
        #: are applied before the slicing operation is performed.
        self._slice_key = slice_key
        self._apply_slice()

    slice = property(_get_slice, _set_slice)

    def _apply_filter(self):
        #: Called when the filter specification has changed.
        raise NotImplementedError('Abstract method')

    def _apply_order(self):
        #: Called when the order specification has changed.
        raise NotImplementedError('Abstract method')

    def _apply_slice(self):
        #: Called when the slice key has changed.
        raise NotImplementedError('Abstract method')

