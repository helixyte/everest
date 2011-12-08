"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Aggregate implementations.

Created on Sep 25, 2011.
"""

from everest.db import Session
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IRelationAggregateImplementation
from everest.entities.interfaces import IRootAggregateImplementation
from everest.querying.interfaces import IKeyFunctionOrderSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.interfaces import ISqlFilterSpecificationVisitor
from everest.staging import StagingContextManagerBase
from sqlalchemy.orm.exc import NoResultFound
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['MemoryAggregateImpl',
           'OrmAggregateImpl',
           ]


class AggregateImpl(object):
    """
    Abstract base class for all aggregate implementations.
    """

    def __init__(self, entity_class):
        """
        Constructor:

        :param entity_class: the entity class (type) of the entities in this
            aggregate.
        :type entity_class: a class implementing
            :class:`everest.entities.interfaces.IEntity`
        """
        if self.__class__ is AggregateImpl:
            raise NotImplementedError('Abstract class.')
        #: Entity class (type) of the entities in this aggregate.
        self._entity_class = entity_class
        #: Specifications for querying
        #: (:class:`everest.querying.specifications.FilterSpecifications`).
        self._filter_spec = None
        #: Specifications for querying (:class:`everest.ordering.OrderSpecification`).
        self._order_spec = None
        #: Key for slicing. (:type:`slice`).
        self._slice_key = None

    @classmethod
    def create(cls, entity_class, **kw):
        raise NotImplementedError('Abstract method.')

    def clone(self):
        clone = self.__class__.create(self._entity_class)
        clone._filter_spec = self._filter_spec
        clone._order_spec = self._order_spec
        clone._slice_key = self._slice_key
        return clone

    def count(self):
        raise NotImplementedError('Abstract method')

    def get_by_id(self, id_key):
        raise NotImplementedError('Abstract method')

    def get_by_slug(self, slug):
        raise NotImplementedError('Abstract method')

    def iterator(self):
        raise NotImplementedError('Abstract method')

    def add(self, entity):
        raise NotImplementedError('Abstract method')

    def remove(self, entity):
        raise NotImplementedError('Abstract method')

    def filter(self, filter_spec):
        self._filter_spec = filter_spec
        self._apply_filter()

    def get_filter_spec(self):
        return self._filter_spec

    def order(self, order_spec):
        self._order_spec = order_spec
        self._apply_order()

    def get_order_spec(self):
        return self._order_spec

    def slice(self, slice_key):
        self._slice_key = slice_key
        self._apply_slice()

    def get_slice_key(self):
        return self._slice_key

    def _apply_filter(self):
        """
        Called when the filter specification has changed.
        """
        raise NotImplementedError('Abstract method')

    def _apply_order(self):
        """
        Called when the order specification has changed.
        """
        raise NotImplementedError('Abstract method')

    def _apply_slice(self):
        """
        Called when the slice key has changed.
        """
        raise NotImplementedError('Abstract method')


class MemoryAggregateImpl(AggregateImpl):
    """
    In-memory implementation for aggregates.

    :note: Iteration and search in memory aggregates is very slow. Also,
        when "blank" entities without an ID and a slug are added to a
        memory aggregate, they can not be retrieved using the
        :method:`get` method, since there is no mechanism to autogenerate
        ids and/or slugs.
    """
    def __init__(self, entity_class):
        if self.__class__ is MemoryAggregateImpl:
            raise NotImplementedError('Abstract class.')
        AggregateImpl.__init__(self, entity_class)

    def count(self):
        return len(list(self.iterator()))

    def get_by_id(self, id_key):
        ents = self._get_entities()
        try:
            ent = self.__filter_by_attr(ents, 'id', id_key)[0]
        except IndexError:
            ent = None
        return ent

    def get_by_slug(self, slug):
        ents = self._get_entities()
        try:
            ent = self.__filter_by_attr(ents, 'slug', slug)[0]
        except IndexError:
            ent = None
        return ent

    def iterator(self):
        ents = self._get_entities()
        if not self._filter_spec is None:
            ents = [ent for ent in ents
                    if self._filter_spec.is_satisfied_by(ent)]
        if not self._order_spec is None:
            visitor = get_utility(IKeyFunctionOrderSpecificationVisitor)()
            self._order_spec.accept(visitor)
            key_func = visitor.expression
            ents = sorted(ents, key=key_func)
        if not self._slice_key is None:
            ents = ents[self._slice_key]
        for ent in ents:
            yield ent

    def add(self, entity):
        if not isinstance(entity, self._entity_class):
            raise ValueError('Can only add entities of type "%s" to this '
                             'aggregate.' % self._entity_class)
        if not hasattr(entity, 'id'):
            raise ValueError('Entities added to a memory aggregrate have to '
                             'have an ID (`id` attribute).')
        if not hasattr(entity, 'slug'):
            raise ValueError('Entities added to a memory aggregrate have to '
                             'have a slug (`slug` attribute).')
        entity_id = entity.id
        entity_slug = entity.slug
        if not entity_id is None:
            if entity_slug is None:
                raise ValueError('Entities added to a memory aggregate which '
                                 'specify an ID also need to specify a slug.')
            elif self.__check_existing(entity):
                raise ValueError('Entity with ID "%s" or slug "%s" is already '
                                 'present.' % (entity_id, entity_slug))
        ents = self._get_entities()
        ents.append(entity)

    def remove(self, entity):
        ents = self._get_entities()
        ents.remove(entity)

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass

    def _get_entities(self):
        """
        Returns the entities held by this memory aggregate.
        
        :returns:  list of objects implementing 
            :class:`everest.entities.interfaces.IEntity`
        """
        raise NotImplementedError('Abstract method.')

    def _set_entities(self, entities):
        """
        Sets the entities held by this memory aggregate.
        
        :param entities: list of objects implementing 
            :class:`everest.entities.interfaces.IEntity`
        """
        raise NotImplementedError('Abstract method.')

    def __check_existing(self, entity):
        ents = self._get_entities()
        found = [ent for ent in ents
               if ent.id == entity.id or ent.slug == entity.slug]
        return len(found) > 0

    def __filter_by_attr(self, ents, attr, value):
        if self._filter_spec is None:
            filtered_ents = \
                [ent for ent in ents if getattr(ent, attr) == value]
        else:
            filtered_ents = \
                [ent for ent in ents if getattr(ent, attr) == value
                 if self._filter_spec.is_satisfied_by(ent)]
        return filtered_ents


class MemoryRootAggregateImpl(MemoryAggregateImpl):
    implements(IAggregate, IRootAggregateImplementation)

    def __init__(self, entity_class):
        MemoryAggregateImpl.__init__(self, entity_class)
        self.__entities = [] # Holds entities.

    @classmethod
    def create(cls, entity_class, **kw):
        return cls(entity_class)

    def clone(self):
        clone = super(MemoryRootAggregateImpl, self).clone()
        clone.__entities = self.__entities # access private pylint: disable=W0212
        return clone

    def _get_entities(self):
        return self.__entities

    def _set_entities(self, entities):
        self.__entities = entities


class MemoryRelationAggregateImpl(MemoryAggregateImpl):
    implements(IAggregate, IRelationAggregateImplementation)

    def __init__(self, entity_class, relation):
        MemoryAggregateImpl.__init__(self, entity_class)
        # Resource relation (:class:`everest.resources.base.ResourceRelation`).
        self.__relation = relation

    @classmethod
    def create(cls, entity_class, relation=None, **kw):
        return cls(entity_class, relation)

    def clone(self):
        clone = super(MemoryRelationAggregateImpl, self).clone()
        clone.__relation = self.__relation # access private pylint: disable=W0212
        return clone

    def _get_entities(self):
        return self.__relation.relatee

    def _set_entities(self, entities):
        self.__relation.relatee = entities

    def get_filter_spec(self):
        #: Overridden to handle absolute vs. relative specs.
        return self.__relation.make_filter_spec(self._filter_spec)


class OrmAggregateImpl(AggregateImpl):
    """
    Base class for ORM implementations for aggregates.
    """
    def __init__(self, entity_class, session, search_mode=False):
        if self.__class__ is OrmAggregateImpl:
            raise NotImplementedError('Abstract class.')
        AggregateImpl.__init__(self, entity_class)
        self._session = session
        self._search_mode = search_mode

    def count(self):
        if self.__defaults_empty:
            cnt = 0
        else:
            cnt = self.__get_filtered_query(None).count()
        return cnt

    def get_by_id(self, id_key):
        query = self.__get_filtered_query(id_key)
        try:
            ent = query.filter_by(id=id_key).one()
        except NoResultFound:
            ent = None
        return ent

    def get_by_slug(self, slug):
        query = self.__get_filtered_query(slug)
        try:
            ent = query.filter_by(slug=slug).one()
        except NoResultFound:
            ent = None
        return ent

    def iterator(self):
        if self.__defaults_empty:
            yield
        else:
            # We need a flush here because we may have newly added entities
            # in the aggregate which need to get an ID *before* we build the
            # query expression.
            self._session.flush()
            query = self._get_data_query()
            for obj in iter(query):
                yield obj

    def add(self, entity):
        raise NotImplementedError('Abstract method.')

    def remove(self, entity):
        raise NotImplementedError('Abstract method.')

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass

    def _query_generator(self, query, key): # pylint: disable=W0613
        return query

    def _filter_visitor_factory(self):
        visitor_cls = get_utility(ISqlFilterSpecificationVisitor)
        return visitor_cls(self._entity_class)

    def _order_visitor_factory(self):
        visitor_cls = get_utility(IOrderSpecificationVisitor)
        return visitor_cls(self._entity_class)

    def _get_base_query(self):
        raise NotImplementedError('Abstract method.')

    def _get_data_query(self):
        if self._slice_key is None:
            query = self.__get_ordered_query(None)
        else:
            query = self.__get_ordered_query(self._slice_key)
            query = query.slice(self._slice_key.start,
                                self._slice_key.stop)
        return query

    def __get_filtered_query(self, key):
        query = self._query_generator(self._get_base_query(), key)
        if not self._filter_spec is None:
            visitor = self._filter_visitor_factory()
            self._filter_spec.accept(visitor)
            query = query.filter(visitor.expression)
        return query

    def __get_ordered_query(self, key):
        query = self.__get_filtered_query(key)
        if not self._order_spec is None:
            visitor = self._order_visitor_factory()
            self._order_spec.accept(visitor)
            joins = visitor.get_joins()
            if len(joins) > 0:
                query = query.outerjoin(*joins) # pylint: disable=W0142
            query = query.order_by(*visitor.expression)
        return query

    @property
    def __defaults_empty(self):
        return self._filter_spec is None and self._search_mode


class OrmRootAggregateImpl(OrmAggregateImpl):
    """
    ORM implementation for root aggregates (using SQLAlchemy).
    """
    implements(IRootAggregateImplementation)

    @classmethod
    def create(cls, entity_class, **kw):
        search_mode = kw.pop('search_mode', False)
        session = Session()
        return cls(entity_class, session, search_mode=search_mode)

    def add(self, entity):
        self._session.add(entity)

    def remove(self, entity):
        self._session.delete(entity)

    def _get_base_query(self):
        return self._session.query(self._entity_class)


class OrmRelationAggregateImpl(OrmAggregateImpl):
    """
    ORM implementation for relation aggregates (using SQLAlchemy).
    """
    implements(IRelationAggregateImplementation)

    def __init__(self, entity_class, session, relation, search_mode=False):
        OrmAggregateImpl.__init__(self, entity_class, session,
                                  search_mode=search_mode)
        # Resource relation (:class:`everest.resources.base.ResourceRelation`).
        self.__relation = relation

    @classmethod
    def create(cls, entity_class, relation, **kw):
        search_mode = kw.pop('search_mode', False)
        session = Session()
        return cls(entity_class, session, relation, search_mode=search_mode)

    def add(self, entity):
        self.__relation.relatee.append(entity)

    def remove(self, entity):
        self.__relation.relatee.remove(entity)

    def count(self):
        # We need a flush here because we may have newly added entities
        # in the aggregate which need to get an ID *before* we build the
        # relation filter spec.
        self._session.flush()
        return OrmAggregateImpl.count(self)

    def iterator(self):
        # We need a flush here because we may have newly added entities
        # in the aggregate which need to get an ID *before* we build the
        # relation filter spec.
        self._session.flush()
        return OrmAggregateImpl.iterator(self)

    def get_filter_spec(self):
        #: Overridden to handle absolute vs. relative specs.
        return self.__relation.make_filter_spec(self._filter_spec)

    def _get_base_query(self):
        rel_spec = self.__relation.make_relation_spec()
        visitor = self._filter_visitor_factory()
        rel_spec.accept(visitor)
        expr = visitor.expression
        return self._session.query(self._entity_class).filter(expr)

#        # Identify the target model class for the relationship and
#        # construct a query for it.
#        relator = self.__relation.relator
#        mapper = object_mapper(relator)
#        rel_property = \
#                mapper.get_property(self.__relation.relator_attribute)
#        model_class = rel_property.argument
#        assert IEntity in provided_by(object.__new__(model_class))
#        return self._session.query(model_class).with_parent(relator)


class PersistentStagingContextManager(StagingContextManagerBase):
    """
    Staging context manager to use when building/modifying collections that
    are persisted by the ORM.
    """
    root_aggregate_impl = OrmRootAggregateImpl
    relation_aggregate_impl = OrmRelationAggregateImpl

    def __init__(self):
        StagingContextManagerBase.__init__(self)

    def __exit__(self, exc_type, value, tb):
        StagingContextManagerBase.__exit__(self, exc_type, value, tb)
        #
        Session().flush()


class TransientStagingContextManager(StagingContextManagerBase):
    """
    Staging context manager to use when building/modifying collections that
    are transiently held in memory.
    """
    root_aggregate_impl = MemoryRootAggregateImpl
    relation_aggregate_impl = MemoryRelationAggregateImpl

    def __init__(self):
        StagingContextManagerBase.__init__(self)
