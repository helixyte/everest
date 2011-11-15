"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Entity base classes.

Created on May 12, 2011.
"""

from everest.entities.aggregates import MemoryRelationAggregateImpl
from everest.entities.aggregates import MemoryRootAggregateImpl
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.entities.interfaces import IRelationAggregateImplementation
from everest.entities.interfaces import IRootAggregateImplementation
from zope.component import queryUtility as query_utility # pylint: disable=E0611,F0401
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
        self.id = id

    @property
    def slug(self):
        """
        Returns a human-readable and URL-compatible string that is unique
        within all siblings of this entity.

        Note that the slug has to be declared as a (read-only) property
        in derived classes as well.
        """
        return str(self.id)

    @classmethod
    def create_from_data(cls, data):
        return cls(**data) # ** pylint: disable=W0142

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)


class Aggregate(object):
    """
    Abstract base class for all aggregates.

    An aggregate provides a wrapper around a set of entities of a specific
    type which are held in some repository. The wrapped entity set may be
    a "root" set of all entities in the repository or a "relation" set
    defined by a relationship to entities of some other type.

    Supports filtering, sorting, slicing, counting, iteration as well as
    retrieving, adding and removing entities.

    The actual work is delegated to an instance of
    :class:`everest.entities.aggregates.AggregateImpl` to allow for runtime
    selection of implementations.
    """
    implements(IAggregate)

    def __init__(self, implementation):
        if self.__class__ is Aggregate:
            raise NotImplementedError('Abstract class')
        self.__implementation = implementation

    @classmethod
    def create(cls, entity_class, **kw):
        """
        Factory method.
        """
        impl_cls = kw.get('implementation')
        if impl_cls is None:
            # If no implementation is given, we use whichever implementation
            # is registered for the current staging area.
            if not kw.get('relation') is None:
                impl_cls = query_utility(IRelationAggregateImplementation,
                                         default=MemoryRelationAggregateImpl)
            else:
                impl_cls = query_utility(IRootAggregateImplementation,
                                         default=MemoryRootAggregateImpl)
        impl = impl_cls.create(entity_class, **kw)
        return cls(impl)

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
        :param id_key: ID to look up
        :type id_key: `int` or `str`
        :returns: specified entity or `None`

        Returns a single entity from the underlying aggregate by ID.
        """
        return self.__implementation.get_by_id(id_key)

    def get_by_slug(self, slug):
        """
        Returns an entity by slug or `None` if the entity is not found.

        :param slug: slug to look up
        :type id_key: `str`
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
        Adds an entity to the underlying aggregate.

        If the entity has an ID, it must be unique within the aggregate.

        :param entity: entity (domain object) to add
        :type entity: object implementing
          :class:`everest.entities.interfaces.IEntity`
        :raise ValueError: if an entity with the same ID exists
        """
        self.__implementation.add(entity)

    def remove(self, entity):
        """
        Removes an entity from the underlying aggregate.

        :param entity: entity (domain object) to remove
        :type entity: object implementing
          :class:`everest.entities.interfaces.IEntity`
        :raise ValueError: entity was not found
        """
        self.__implementation.remove(entity)

    def filter(self, filter_spec):
        """
        Filters the aggregate by the given filter specification.

        :param spec: an instance of a FilterSpecification
        :type filter_spec: instance of
            :class:`everest.specifications.FilterSpecification`
        """
        self.__implementation.filter(filter_spec)

    def get_filter_spec(self):
        """
        Returns the filter specification for this aggregate.
        """
        return self.__implementation.get_filter_spec()

    def order(self, order_spec):
        """
        Orders the aggregate according to the given order specification.

        :param order_spec: order specification
        :type order_spec: instance of :class:`everest.ordering.OrderSpecification`
        """
        return self.__implementation.order(order_spec)

    def get_order_spec(self):
        """
        Returns the order specification for this aggregate.
        """
        return self.__implementation.get_order_spec()

    def slice(self, slice_key):
        """
        Slices the aggregate with the given slice key.

        If specified, filter and order specs are applied before the slicing
        operation is performed.

        :param slice slice_key: slice to apply.
        """
        return self.__implementation.slice(slice_key)

    def get_slice_key(self):
        """
        Returns the slice key for this aggregate.
        """
        return self.__implementation.get_slice_key()
