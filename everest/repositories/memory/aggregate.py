"""
Memory aggregate.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.entities.base import Aggregate
from everest.exceptions import DuplicateException
from everest.querying.base import EXPRESSION_KINDS
from everest.utils import get_filter_specification_visitor
from everest.utils import get_order_specification_visitor

__docformat__ = 'reStructuredText en'
__all__ = ['MemoryAggregate',
           ]


class MemoryAggregate(Aggregate):
    """
    Aggregate implementation for the in-memory repository. 

    :note: When "blank" entities without an ID and a slug are added to a
        memory aggregate, they can not be retrieved using the
        :meth:`get_by_id` or :meth:`get_by_slug` methods since there 
        is no mechanism to autogenerate IDs or slugs.
    """

    def count(self):
        return self.__get_entities()[1]

    def get_by_id(self, id_key):
        if self._relationship is None or self._relationship.children is None:
            ent = self._session.get_by_id(self.entity_class, id_key)
            if not self._filter_spec is None \
               and not self._filter_spec.is_satisfied_by(ent):
                ent = None
        else:
            ent = self.__filter_by_attr(self._relationship.children,
                                        'id', id_key)
        return ent

    def get_by_slug(self, slug):
        if self._relationship is None or self._relationship.children is None:
            ent = self._session.get_by_slug(self.entity_class, slug)
            if not self._filter_spec is None \
               and not self._filter_spec.is_satisfied_by(ent):
                ent = None
        else:
            ent = self.__filter_by_attr(self._relationship.children,
                                        'slug', slug)
        return ent

    def iterator(self):
        for ent in self.__get_entities()[0]:
            yield ent

    def add(self, entity):
        if not isinstance(entity, self.entity_class):
            raise ValueError('Can only add entities of type "%s" to this '
                             'aggregate.' % self.entity_class)
        self._session.add(self.entity_class, entity)
        if not self._relationship is None \
           and not self._relationship.children is None:
            self._relationship.children.append(entity)

    def remove(self, entity):
        self._session.remove(self.entity_class, entity)
        if not self._relationship is None \
           and not self._relationship.children is None:
            self._relationship.children.remove(entity)

    def update(self, entity, source_entity):
        # FIXME: We need a proper __getstate__ method here.
        entity.__dict__.update(
                    dict([(k, v)
                          for (k, v) in source_entity.__dict__.iteritems()
                          if not k.startswith('_')]))

    def _apply_filter(self):
        pass

    def _apply_order(self):
        pass

    def _apply_slice(self):
        pass

    def __get_entities(self):
        if self._relationship is None:
            ents = list(self._session.iterator(self.entity_class))
        else:
            if self._relationship.children is None:
                ents = list(self._session.iterator(self.entity_class))
                visitor = \
                    get_filter_specification_visitor(EXPRESSION_KINDS.EVAL)()
                self._relationship.specification.accept(visitor)
                ents = visitor.expression(ents)
            else:
                ents = self._relationship.children
        if not self._filter_spec is None:
            visitor = get_filter_specification_visitor(EXPRESSION_KINDS.EVAL)()
            self._filter_spec.accept(visitor)
            ents = visitor.expression(ents)
        # Record the total count of matching entities.
        count = len(ents)
        if not self._order_spec is None:
            visitor = get_order_specification_visitor(EXPRESSION_KINDS.EVAL)()
            self._order_spec.accept(visitor)
            ents = visitor.expression(ents)
        if not self._slice_key is None:
            ents = ents[self._slice_key]
        return ents, count

    def __filter_by_attr(self, ents, attr, value):
        if self._filter_spec is None:
            matching_ents = \
                [ent for ent in ents if getattr(ent, attr) == value]
        else:
            matching_ents = \
                [ent for ent in ents
                 if (getattr(ent, attr) == value
                     and self._filter_spec.is_satisfied_by(ent))]
        if len(matching_ents) == 1:
            ent = matching_ents[0]
        elif len(matching_ents) == 0:
            ent = None
        else:
            raise DuplicateException('Duplicates found for "%s" value of ' # pragma: no cover
                                     '"%s" attribue.' % (value, attr))
        return ent
