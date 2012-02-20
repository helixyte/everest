"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Aggregate implementations.

Created on Sep 25, 2011.
"""

from everest.entities.base import Aggregate
from everest.exceptions import DuplicateException
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['MemoryAggregate',
           'OrmAggregate',
           ]


class MemoryAggregate(Aggregate):
    """
    In-memory implementation for aggregates.

    :note: When "blank" entities without an ID and a slug are added to a
        memory aggregate, they can not be retrieved using the
        :method:`get_by_id` or :method:`get_by_slug` methods since there 
        is no mechanism to autogenerate IDs or slugs.
    """

    def clone(self):
        clone = super(MemoryAggregate, self).clone()
        if self._relationship is None:
            clone._session = self._session
        return clone

    def count(self):
        if self._relationship is None:
            count = len(self._session.get_all(self.entity_class))
        else:
            count = len(self._relationship.children)
        return count

    def get_by_id(self, id_key):
        if self._relationship is None:
            ent = self._session.get_by_id(self.entity_class, id_key)
        else:
            ent = self.__filter_by_attr(self._relationship.children,
                                        'id', id_key)
        return ent

    def get_by_slug(self, slug):
        if self._relationship is None:
            ent = self._session.get_by_slug(self.entity_class, slug)
        else:
            ent = self.__filter_by_attr(self._relationship.children,
                                        'slug', slug)
        return ent

    def iterator(self):
        if self._relationship is None:
            ents = self._session.get_all(self.entity_class)
        else:
            ents = self._relationship.children
        if not self._filter_spec is None:
            visitor = get_utility(IFilterSpecificationVisitor,
                                  name=EXPRESSION_KINDS.EVAL)()
            self._filter_spec.accept(visitor)
            ents = visitor.expression(ents)
        if not self._order_spec is None:
            visitor = get_utility(IOrderSpecificationVisitor,
                                  name=EXPRESSION_KINDS.EVAL)()
            self._order_spec.accept(visitor)
            ents = visitor.expression(ents)
        if not self._slice_key is None:
            ents = ents[self._slice_key]
        for ent in ents:
            yield ent

    def add(self, entity):
        if not isinstance(entity, self.entity_class):
            raise ValueError('Can only add entities of type "%s" to this '
                             'aggregate.' % self.entity_class)
        if not hasattr(entity, 'id'):
            raise ValueError('Entities added to a memory aggregrate have to '
                             'have an ID (`id` attribute).')
        if not hasattr(entity, 'slug'):
            raise ValueError('Entities added to a memory aggregrate have to '
                             'have a slug (`slug` attribute).')
        if self._relationship is None:
            self._session.add(self.entity_class, entity)
        else:
            if not entity.id is None \
               and self.__check_existing(self._relationship.children, entity):
                raise ValueError('Duplicate ID or slug.')
            self._relationship.children.append(entity)

    def remove(self, entity):
        if self._relationship is None:
            self._session.remove(self.entity_class, entity)
        else:
            self._relationship.children.remove(entity)

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass

    def __check_existing(self, ents, entity):
        found = [ent for ent in ents
                 if ent.id == entity.id or ent.slug == entity.slug]
        return len(found) > 0

    def __filter_by_attr(self, ents, attr, value):
        if self._filter_spec is None:
            matching_ents = \
                [ent for ent in ents if getattr(ent, attr) == value]
        else:
            matching_ents = \
                [ent for ent in ents if getattr(ent, attr) == value
                 if self._filter_spec.is_satisfied_by(ent)]
        if len(matching_ents) == 1:
            ent = matching_ents[0]
        elif len(matching_ents) == 0:
            ent = None
        else:
            raise DuplicateException('Duplicates found for "%s" value of '
                                     '"%s" attribue.' % (value, attr))
        return ent


class OrmAggregate(Aggregate):
    """
    ORM implementation for aggregates.
    """
    def __init__(self, entity_class, session, search_mode=False):
        Aggregate.__init__(self, entity_class, session)
        self._search_mode = search_mode

    def count(self):
        if not self._relationship is None:
            # We need a flush here because we may have newly added entities
            # in the aggregate which need to get an ID *before* we build the
            # relation filter spec.
            self._session.flush()
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
        except MultipleResultsFound:
            raise DuplicateException('Duplicates found for ID "%s".' % id_key)
        return ent

    def get_by_slug(self, slug):
        query = self.__get_filtered_query(slug)
        try:
            ent = query.filter_by(slug=slug).one()
        except NoResultFound:
            ent = None
        except MultipleResultsFound:
            raise DuplicateException('Duplicates found for slug "%s".' % slug)
        return ent

    def iterator(self):
        if not self._relationship is None:
            # We need a flush here because we may have newly added entities
            # in the aggregate which need to get an ID *before* we build the
            # relation filter spec.
            self._session.flush()
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
        if self._relationship is None:
            self._session.add(entity)
        else:
            self._relationship.children.append(entity)

    def remove(self, entity):
        if self._relationship is None:
            self._session.delete(entity)
        else:
            self._relationship.children.remove(entity)

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass

    def _query_generator(self, query, key): # unused pylint: disable=W0613
        return query

    def _filter_visitor_factory(self):
        visitor_cls = get_utility(IFilterSpecificationVisitor,
                                  name=EXPRESSION_KINDS.SQL)
        return visitor_cls(self.entity_class)

    def _order_visitor_factory(self):
        visitor_cls = get_utility(IOrderSpecificationVisitor,
                                  name=EXPRESSION_KINDS.SQL)
        return visitor_cls(self.entity_class)

    def _get_base_query(self):
        if self._relationship is None:
            query = self._session.query(self.entity_class)
        else:
            # Pre-filter the base query with the relation specification.
            rel_spec = self._relationship.specification
            visitor = self._filter_visitor_factory()
            rel_spec.accept(visitor)
            expr = visitor.expression
            query = self._session.query(self.entity_class).filter(expr)
        return query

    def _get_data_query(self):
        query = self.__get_ordered_query(self._slice_key)
        if not self._slice_key is None:
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
            for join_expr in visitor.get_joins():
                # FIXME: only join when needed here # pylint:disable=W0511
                query = query.outerjoin(join_expr)
            query = query.order_by(*visitor.expression)
        return query

    @property
    def __defaults_empty(self):
        return self._filter_spec is None and self._search_mode
