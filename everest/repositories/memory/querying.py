"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.exceptions import MultipleResultsException
from everest.exceptions import NoResultsException
from everest.querying.filtering import RepositoryFilterSpecificationVisitor
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.querying.ordering import RepositoryOrderSpecificationVisitor
from everest.querying.specifications import eq
from everest.repositories.base import Query
from everest.utils import generative
from itertools import chain
from itertools import islice
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['EvalFilterExpression',
           'MemoryQuery',
           'MemorySessionQuery',
           'ObjectFilterSpecificationVisitor',
           'ObjectOrderSpecificationVisitor',
           ]


class MemoryQueryBase(Query):
    """
    Base class for in-memory queries.
    """
    def __init__(self, entity_class):
        Query.__init__(self)
        self._entity_class = entity_class
        self._filter_expr = None
        self._order_expr = None
        self._slice_key = None

    def __iter__(self):
        raise NotImplementedError('Abstract method.')

    def count(self):
        raise NotImplementedError('Abstract method.')

    def all(self):
        return list(iter(self))

    def one(self):
        ents = self.all()
        if len(ents) == 0:
            raise NoResultsException('No results found when exactly one '
                                     'was expected.')
        elif len(ents) > 1:
            raise MultipleResultsException('More than one result found '
                                           'where exactly one was expected.')
        return ents[0]

    @generative
    def filter(self, filter_expression):
        if not filter_expression is None and not self._filter_expr is None:
            filter_expression = self._filter_expr and filter_expression
        self._filter_expr = filter_expression
        return self

    def filter_by(self, **kw):
        spec = eq(**kw)
        return self.filter(EvalFilterExpression(spec))

    @generative
    def order_by(self, order_expression):
        if not order_expression is None and not self._order_expr is None:
            order_expression = self._order_expr & order_expression
        self._order_expr = order_expression
        return self

    @generative
    def slice(self, start, stop):
        self._slice_key = slice(start, stop)
        return self


class MemoryQuery(MemoryQueryBase):
    """
    Query operating on objects held in a sequence object.
    """
    def __init__(self, entity_class, entities):
        MemoryQueryBase.__init__(self, entity_class)
        self.__entities = entities

    def __iter__(self):
        ents = iter(self.__entities)
        if not self._filter_expr is None:
            ents = self._filter_expr(ents)
        if not self._order_expr is None:
            # Ordering always involves a copy and conversion to a list, so
            # we have to wrap in an iterator.
            ents = iter(self._order_expr(ents))
        if not self._slice_key is None:
            ents = islice(ents, self._slice_key.start, self._slice_key.stop)
        return ents

    def count(self):
        ents = iter(self.__entities)
        if not self._filter_expr is None:
            ents = self._filter_expr(ents)
        return len(list(ents))


class MemorySessionQuery(MemoryQueryBase):
    """
    Query operating on objects kept in a memory session.
    """
    def __init__(self, entity_class, session, repository):
        MemoryQueryBase.__init__(self, entity_class)
        self.__session = session
        self.__repository = repository

    def __iter__(self):
        # We iterate over all entities in the repository minus all entities
        # removed from the session plus all entities added to the session.
        # Filter, order, and slice operations are applied.
        deleted_ids = set([rm_ent.id for rm_ent in self.__session.deleted])
        repo_ents = (repo_ent
                     for repo_ent in self.__repository.retrieve(
                                        self._entity_class,
                                        filter_expression=self._filter_expr)
                     if not repo_ent.id in deleted_ids)
        new_ents = (new_ent for new_ent in self.__session.new
                    if isinstance(new_ent, self._entity_class))
        if not self._filter_expr is None:
            new_ents = self._filter_expr(new_ents)
        if not self._order_expr is None:
            # For a sorted iteration, we need to sort the full sequence of
            # new and fetched entities and then iterate over it.
            all_ents = list(repo_ents)
            all_ents.extend(list(new_ents))
            ord_all_ents = self._order_expr(all_ents)
            if not self._slice_key is None:
                ord_all_ents = ord_all_ents[self._slice_key]
            for ord_all_ent in ord_all_ents:
                yield self.__session.load(self._entity_class, ord_all_ent)
        else:
            # For random iteration, we just chain the iterators for the
            # fetched and new entities.
            all_ents = chain(repo_ents, new_ents)
            if not self._slice_key is None:
                all_ents = islice(all_ents,
                                  self._slice_key.start, self._slice_key.stop)
            for all_ent in all_ents:
                yield self.__session.load(self._entity_class, all_ent)

    def count(self):
        # We count all entities in the repository minus all entities
        # removed from the session plus all entities added to the session.
        # Filter operations are applied.
        deleted_ids = set([rm_ent.id for rm_ent in self.__session.deleted
                           if isinstance(rm_ent, self._entity_class)])
        repo_ents = self.__repository.retrieve(
                                        self._entity_class,
                                        filter_expression=self._filter_expr)
        repo_count = sum(1 for repo_ent in repo_ents
                         if not repo_ent.id in deleted_ids)
        new_ents = (new_ent for new_ent in self.__session.new
                    if isinstance(new_ent, self._entity_class))
        if not self._filter_expr is None:
            new_ents = self._filter_expr(new_ents)
        new_count = sum(1 for _ in new_ents)
        return repo_count + new_count


class EvalFilterExpression(object):
    """
    Evaluation filter expression.
    """
    def __init__(self, spec):
        self.__spec = spec

    def __call__(self, entities):
        return self.__evaluator(self.__spec, entities)

    def __and__(self, other):
        return EvalFilterExpression(self.__spec & other.__spec) # pylint: disable=W0212

    def __or__(self, other):
        return EvalFilterExpression(self.__spec | other.__spec) # pylint: disable=W0212

    def __invert__(self):
        return EvalFilterExpression(~self.__spec)

    @staticmethod
    def __evaluator(spec, entities):
        return (ent for ent in entities if spec.is_satisfied_by(ent))


@implementer(IFilterSpecificationVisitor)
class ObjectFilterSpecificationVisitor(RepositoryFilterSpecificationVisitor):
    """
    Filter specification visitor building an evaluator for in-memory
    filtering.
    """

    def filter_query(self, query):
        return query.filter(self.expression)

    def _conjunction_op(self, spec, *expressions):
        return EvalFilterExpression(spec)

    def _disjunction_op(self, spec, *expressions):
        return EvalFilterExpression(spec)

    def _negation_op(self, spec, expression):
        return EvalFilterExpression(spec)

    def _starts_with_op(self, spec):
        return EvalFilterExpression(spec)

    def _ends_with_op(self, spec):
        return EvalFilterExpression(spec)

    def _contains_op(self, spec):
        return EvalFilterExpression(spec)

    def _contained_op(self, spec):
        return EvalFilterExpression(spec)

    def _equal_to_op(self, spec):
        return EvalFilterExpression(spec)

    def _less_than_op(self, spec):
        return EvalFilterExpression(spec)

    def _less_than_or_equal_to_op(self, spec):
        return EvalFilterExpression(spec)

    def _greater_than_op(self, spec):
        return EvalFilterExpression(spec)

    def _greater_than_or_equal_to_op(self, spec):
        return EvalFilterExpression(spec)

    def _in_range_op(self, spec):
        return EvalFilterExpression(spec)


class EvalOrderExpression(object):
    """
    Evaluation order expression.
    """
    def __init__(self, spec):
        self.__spec = spec

    def __call__(self, entities):
        return sorted(entities, cmp=self.__spec.cmp)

    def __and__(self, other):
        return EvalOrderExpression(self.__spec & other.__spec) # pylint: disable=W0212


@implementer(IOrderSpecificationVisitor)
class ObjectOrderSpecificationVisitor(RepositoryOrderSpecificationVisitor):
    """
    Order specification visitor building an evaluator for in-memory
    ordering.
    """

    def order_query(self, query):
        return query.order_by(self.expression)

    def _conjunction_op(self, spec, *expressions):
        return lambda entities: sorted(entities, cmp=spec.cmp)

    def _asc_op(self, spec):
        return lambda entities: sorted(entities, cmp=spec.cmp)

    def _desc_op(self, spec):
        return lambda entities: sorted(entities, cmp=spec.cmp)
