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
        return cls(**data) # ** pylint: disable=W0142

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)


class Aggregate(object):
    """
    The aggregate class. 
    
    An aggregate is an accessor for a set of entities of the same type which 
    are held in some repository. 
    
    The wrapped entity set may be a "root" set of all entities in the 
    repository or a "relation" set defined by a relationship to entities of 
    some other type.

    Supports filtering, sorting, slicing, counting, iteration as well as
    retrieving, adding and removing entities.

    The actual work is delegated to an instance of
    :class:`everest.entities.aggregates.AggregateImpl` to allow for runtime
    selection of implementations.
    """
    implements(IAggregate)

    def __init__(self, implementation):
        self.__implementation = implementation

    def set_implementation(self, implementation):
        """
        Switches the implementation of this aggregate to the given object.
        
        :param implementation: object implementing
          :class:`everest.entities.interfaces.IAggregateImplementation`.
        """
        self.__implementation = implementation

    @classmethod
    def create(cls, implementation):
        """
        Factory method for creating the aggregate.
        """
        return cls(implementation)

    def clone(self):
        """
        Creates a clone of this aggregate.

        :return: A copy of the aggregate object.
        """
        impl_clone = self.__implementation.clone()
        agg = object.__new__(self.__class__)
        agg.__implementation = impl_clone
        return agg

    def count(self):
        """
        Returns the total number of entities in the underlying aggregate.
        If specified, filter specs are applied. A specified slice key is
        ignored.

        :returns: number of aggregate members (:class:`int`)
        """
        return self.__implementation.count()

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
        return self.__implementation.get_by_id(id_key)

    def get_by_slug(self, slug):
        """
        Returns an entity by slug or `None` if the entity is not found.

        :param slug: slug value to look up
        :type slug: `str`
        :raises: :class:`everest.exceptions.DuplicateException` if more than
          one entity is found for the given ID value. 
        :returns: entity or `None`
        """
        return self.__implementation.get_by_slug(slug)

    def iterator(self):
        """
        Returns an iterator for the entities contained in the underlying
        aggregate.

        If specified, filter, order, and slice settings are applied.

        :returns: an iterator for the aggregate entities
        """
        return self.__implementation.iterator()

    def add(self, entity):
        """
        Adds an entity to the aggregate.

        If the entity has an ID, it must be unique within the aggregate.

        :param entity: entity (domain object) to add
        :type entity: object implementing
          :class:`everest.entities.interfaces.IEntity`
        :raise ValueError: if an entity with the same ID exists
        """
        self.__implementation.add(entity)

    def remove(self, entity):
        """
        Removes an entity from the aggregate.

        :param entity: entity (domain object) to remove
        :type entity: object implementing
          :class:`everest.entities.interfaces.IEntity`
        :raise ValueError: entity was not found
        """
        self.__implementation.remove(entity)

    def _get_filter(self):
        """
        Returns the filter specification for this aggregate.
        """
        return self.__implementation.filter

    def _set_filter(self, filter_spec):
        """
        Sets the filter specification for this aggregate.
        
        :param filter_spec: filter specification
        :type filter_spec: instance of
            :class:`everest.querying.specifications.FilterSpecification`
        """
        self.__implementation.filter = filter_spec

    filter = property(_get_filter, _set_filter,
                      doc="Filter specification for the aggregate.")

    def _get_order(self):
        """
        Returns the order specification for this aggregate.
        """
        return self.__implementation.order

    def _set_order(self, order_spec):
        """
        Sets the order specification for this aggregate.

        :param order_spec: order specification
        :type order_spec: instance of 
            :class:`everest.querying.specifications.OrderSpecification`
        """
        self.__implementation.order = order_spec

    order = property(_get_order, _set_order,
                      doc="Order specification for the aggregate.")

    def _get_slice(self):
        """
        Returns the slice key for this aggregate.
        """
        return self.__implementation.slice

    def _set_slice(self, slice_key):
        """
        Sets the slice key for this aggregate.

        If specified, filter and order specs are applied before the slicing
        operation is performed.

        :param slice slice_key: slice to apply.
        :type slice: `slice`
        """
        self.__implementation.slice = slice_key

    slice = property(_get_slice, _set_slice,
                      doc="Slice key for the aggregate.")

    def set_relationship(self, relationship):
        """
        """
        self.__implementation.set_relationship(relationship)
