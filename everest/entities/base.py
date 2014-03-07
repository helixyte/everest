"""
Entity and aggregate base classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 12, 2011.
"""
from everest.constants import RELATIONSHIP_DIRECTIONS
from everest.constants import RELATION_OPERATIONS
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.exceptions import NoResultsException
from everest.querying.utils import get_filter_specification_factory
from everest.utils import get_filter_specification_visitor
from everest.utils import get_order_specification_visitor
from zope.interface import implementer # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['Aggregate',
           'Entity',
           ]


@implementer(IEntity)
class Entity(object):
    """
    Abstract base class for all model entities.

    All entities have an ID which is used as the default value for equality
    comparison. The object may be initialized without an ID.
    """
    #: The (unique) entity ID (integer or string).
    id = None

    def __init__(self, id=None): # redefining id pylint: disable=W0622
        if self.__class__ is Entity:
            raise NotImplementedError('Abstract class.')
        if not id is None:
            self.id = id

    @property
    def slug(self):
        """
        Returns a human-readable and URL-compatible string that is unique
        among all siblings of this entity.
        """
        return None if self.id is None else str(self.id)

    @classmethod
    def create_from_data(cls, data):
        """
        Creates a new instance of this entity from the given data map.
        """
        return cls(**data)

    def __eq__(self, other):
        return id(self) == id(other) \
               or isinstance(other, self.__class__) \
               and self.id == other.id \
               and not (self.id is None and other.id is None)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return id(self)


@implementer(IAggregate)
class Aggregate(object):
    """
    Abstract base class for aggregates.

    An aggregate is an accessor for a set of entities of the same type.

    Supports filtering, sorting, slicing, counting, iteration as well as
    retrieving, adding and removing entities.
    """
    #: Entity class (type) of the entities in this aggregate.
    entity_class = None

    def __init__(self):
        if self.__class__ is Aggregate:
            raise NotImplementedError('Abstract class.')
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

    def clone(self):
        """
        Returns a clone of this aggregate.
        """
        clone = self.__class__.__new__(self.__class__)
        # Access protected member pylint: disable=W0212
        clone._filter_spec = self._filter_spec
        clone._order_spec = self._order_spec
        clone._slice_key = self._slice_key
        # pylint: enable=W0212
        return clone

    def iterator(self):
        """
        Returns an iterator for the entities contained in the underlying
        aggregate.

        If specified, filter, order, and slice settings are applied.

        :returns: An iterator for the aggregate entities.
        """
        return iter(self._get_ordered_query(None))

    def __iter__(self):
        return self.iterator()

    def count(self):
        """
        Returns the total number of entities in the underlying aggregate.
        If specified, filter specs are applied. A specified slice key is
        ignored.

        :returns: Number of aggregate members (:class:`int`).
        """
        return self._get_filtered_query(None).count()

    def get_by_id(self, id_key):
        """
        Returns an entity by ID  or `None` if the entity is not found.

        :note: If a filter is set which matches the requested entity, it
          will not be found.
        :param id_key: ID value to look up.
        :type id_key: `int` or `str`
        :raises: :class:`everest.exceptions.MultipleResultsException` if more
          than one entity is found for the given ID value.
        :returns: Specified entity or `None`.
        """
        raise NotImplementedError('Abstract method.')

    def get_by_slug(self, slug):
        """
        Returns an entity by slug or `None` if the entity is not found.

        :note: If a filter is set which matches the requested entity, it
          will not be found.
        :param slug: Slug value to look up.
        :type slug: `str`
        :raises: :class:`everest.exceptions.MultipleResultsException` if more
          than one entity is found for the given ID value.
        :returns: Entity or `None`
        """
        raise NotImplementedError('Abstract method.')

    def add(self, data):
        """
        Adds the given entity data to the aggregate.

        If the entity has an ID, it must be unique within the aggregate.

        :param data: Any object that can be adapted to
          :class:`everest.interfaces.IDataTraversalProxyAdapter`.
        :type entity: Object implementing
          :class:`everest.entities.interfaces.IEntity`.
        :raise ValueError: If an entity with the same ID exists.
        """
        raise NotImplementedError('Abstract method.')

    def remove(self, data):
        """
        Removes the given entity data from the aggregate.

        :param data: Any object that can be adapted to
          :class:`everest.interfaces.IDataTraversalProxyAdapter`.
        :raise ValueError: If the given entity was not found.
        """
        raise NotImplementedError('Abstract method.')

    def update(self, data, target=None):
        """
        Updates an existing entity data with the given data.

        Relies on the underlying repository for the implementation of the
        state update.

        :param data: Source entity data for the update.
        :type data: Any object that can be adapted to
          :class:`everest.interfaces.IDataTraversalProxyAdapter`.
        :param target: Target entity to transfer state to. If this is not
          given, the target is looked up by the ID of the given source
          data.
        :type source_entity: Object implementing
          :class:`everest.entities.interfaces.IEntity`.
        """
        raise NotImplementedError('Abstract method.')

    def query(self, **options):
        """
        Returns a query for this aggregate.
        """
        raise NotImplementedError('Abstract method.')

    def sync_with_repository(self):
        """
        Flushes all pending state to the repository and updates all loaded
        entities.
        """
        raise NotImplementedError('Abstract method.')

    @property
    def expression_kind(self):
        """
        Returns the kind of filter and order expression this aggregate builds.
        """
        raise NotImplementedError('Abstract property.')

    def get_root_aggregate(self, rc):
        """
        Returns a root aggregate for the given registered resource.

        The aggregate is retrieved from the same repository that was used to
        create this aggregate.
        """
        raise NotImplementedError('Abstract method.')

    def _get_filter(self):
        #: Returns the filter specification for this aggregate.
        return self._filter_spec

    def _set_filter(self, filter_spec):
        #: Sets the filter specification for this aggregate.
        self._filter_spec = filter_spec

    filter = property(_get_filter, _set_filter)

    def _get_order(self):
        #: Returns the order specification for this aggregate.
        return self._order_spec

    def _set_order(self, order_spec):
        #: Sets the order specification for this aggregate.
        self._order_spec = order_spec

    order = property(_get_order, _set_order)

    def _get_slice(self):
        #: Returns the slice key for this aggregate.
        return self._slice_key

    def _set_slice(self, slice_key):
        #: Sets the slice key for this aggregate. Filter and order specs
        #: are applied before the slicing operation is performed.
        self._slice_key = slice_key

    slice = property(_get_slice, _set_slice)

    def _query_optimizer(self, query, slice_key): # unused pylint: disable=W0613
        """
        Override this to generate optimized queries based on the given
        slice key.

        This default implementation just returns the given query as is.

        :param query: Query to optimize as returned from the data source.
        :param key: Slice key to use for the query or `None`, if no slicing
          was applied.
        """
        return query

    def _filter_visitor_factory(self):
        """
        Override this to create filter visitors with custom clauses.
        """
        visitor_cls = get_filter_specification_visitor(self.expression_kind)
        return visitor_cls(self.entity_class)

    def _order_visitor_factory(self):
        """
        Override this to create order visitors with custom clauses.
        """
        visitor_cls = get_order_specification_visitor(self.expression_kind)
        return visitor_cls(self.entity_class)

    def _get_filtered_query(self, key):
        #: Returns a query filtered by the current filter specification.
        query = self._query_optimizer(self.query(), key)
        query = self.__filter_query(query)
        return self.__slice_query(query)

    def _get_ordered_query(self, key):
        #: Returns a filtered query ordered by the current order
        #: specification.
        query = self._query_optimizer(self.query(), key)
        query = self.__filter_query(query)
        query = self.__order_query(query)
        return self.__slice_query(query)

    def __filter_query(self, query):
        if not self.filter is None:
            vst = self._filter_visitor_factory()
            self.filter.accept(vst)
            query = vst.filter_query(query)
        return query

    def __order_query(self, query):
        if not self._order_spec is None:
            vst = self._order_visitor_factory()
            self._order_spec.accept(vst)
            query = vst.order_query(query)
        return query

    def __slice_query(self, query):
        if not self._slice_key is None:
            query = query.slice(self._slice_key.start,
                                self._slice_key.stop)
        return query


class RootAggregate(Aggregate):
    """
    Abstract base class for root aggregates.

    A root aggregate provides access to all entities of a particular type
    in an underlying repository. It also holds a session factory which creates
    a thread-local session that stages operations on the repository.
    """
    #: This holds the value for the expression_kind property (the kind of
    #: filter and order expression this root aggregate builds).
    _expression_kind = None

    def __init__(self, entity_class, session_factory, repository):
        """
        Constructor.

        :param entity_class: The entity class (type) of the entities in this
            aggregate.
        :type entity_class: A class implementing
            :class:`everest.entities.interfaces.IEntity`.
        :param session_factory: The session factory for this aggregate.
        :param repository: The repository that created this aggregate.
        """
        if self.__class__ is RootAggregate:
            raise NotImplementedError('Abstract class.')
        Aggregate.__init__(self)
        #: The entity class managed by this aggregate.
        self.entity_class = entity_class
        #: The session factory.
        self._session_factory = session_factory
        # The repository that holds the entities.
        self.__repository = repository

    @classmethod
    def create(cls, entity_class, session_factory, repository):
        """
        Factory class method to create a new aggregate.
        """
        return cls(entity_class, session_factory, repository)

    def clone(self):
        clone = Aggregate.clone(self)
        clone.entity_class = self.entity_class
         # protected pylint: disable=W0212
        clone._session_factory = self._session_factory
        clone.__repository = self.__repository
         # enable=W0212
        return clone

    def get_by_id(self, id_key):
        ent = self._session.get_by_id(self.entity_class, id_key)
        if ent is None:
            try:
                ent = self.query().filter_by(id=id_key).one()
            except NoResultsException:
                pass
        if not ent is None \
           and not self._filter_spec is None \
           and not self._filter_spec.is_satisfied_by(ent):
            ent = None
        return ent

    def get_by_slug(self, slug):
        ent = self._session.get_by_slug(self.entity_class, slug)
        if ent is None:
            try:
                ent = self.query().filter_by(slug=slug).one()
            except NoResultsException:
                pass
        if not ent is None \
           and not self._filter_spec is None \
           and not self._filter_spec.is_satisfied_by(ent):
            ent = None
        return ent

    def add(self, data):
        self._session.add(self.entity_class, data)

    def remove(self, data):
        self._session.remove(self.entity_class, data)

    def update(self, data, target=None):
        return self._session.update(self.entity_class, data, target=target)

    def query(self, **options):
        return self._session.query(self.entity_class, **options)

    def sync_with_repository(self):
        self._session.flush()

    @property
    def expression_kind(self):
        return self._expression_kind

    def get_root_aggregate(self, rc):
        return self.__repository.get_aggregate(rc)

    def make_relationship_aggregate(self, relationship):
        """
        Returns a new relationship aggregate for the given relationship.

        :param relationship: Instance of
          :class:`everest.entities.relationship.DomainRelationship`.
        """
        if not self._session.IS_MANAGING_BACKREFERENCES:
            relationship.direction &= ~RELATIONSHIP_DIRECTIONS.REVERSE
        return RelationshipAggregate(self, relationship)

    @property
    def _session(self):
        return self._session_factory()


class RelationshipAggregate(Aggregate):
    """
    An aggregate that references a subset of a root aggregate defined through
    a relationship.
    """
    def __init__(self, root_aggregate, relationship):
        Aggregate.__init__(self)
        self._root_aggregate = root_aggregate
        self._relationship = relationship

    def get_by_id(self, id_key):
        ent = self._root_aggregate.get_by_id(id_key)
        if not ent is None and not self.filter.is_satisfied_by(ent):
            ent = None
        return ent

    def get_by_slug(self, slug):
        ent = self._root_aggregate.get_by_slug(slug)
        if not ent is None and not self.filter.is_satisfied_by(ent):
            ent = None
        return ent

    def query(self):
        return self._root_aggregate.query()

    def sync_with_repository(self):
        self._root_aggregate.sync_with_repository()

    @property
    def entity_class(self):
        return self._root_aggregate.entity_class

    @property
    def expression_kind(self):
        return self._root_aggregate.expression_kind

    def get_root_aggregate(self, rc):
        return self._root_aggregate.get_root_aggregate(rc)

    def add(self, entity):
        csc = self._relationship.descriptor.cascade
        add_to_root = csc & RELATION_OPERATIONS.ADD
        if add_to_root:
            self._root_aggregate.add(entity)
        self._relationship.add(entity, safe=True)

    def remove(self, entity):
        csc = self._relationship.descriptor.cascade
        remove_from_root = \
            csc & RELATION_OPERATIONS.REMOVE and not entity.id is None
        if remove_from_root:
            self._root_aggregate.remove(entity)
        self._relationship.remove(entity, safe=True)

    def update(self, entity, target=None):
        csc = self._relationship.descriptor.cascade
        if csc & RELATION_OPERATIONS.UPDATE:
            upd_entity = self._root_aggregate.update(entity, target=target)
        else:
            upd_entity = entity
        return upd_entity

    def _get_filter(self):
        # Overwrite to prepend relationship specification to filter spec.
        rel_spec = self._relationship.specification
        if not self._filter_spec is None:
            spec_fac = get_filter_specification_factory()
            filter_spec = spec_fac.create_conjunction(rel_spec,
                                                      self._filter_spec)
        else:
            filter_spec = rel_spec
        return filter_spec

    filter = property(_get_filter, Aggregate._set_filter)
