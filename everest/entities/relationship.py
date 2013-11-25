"""
Entity relationship.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 12, 2013.
"""
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import RELATION_OPERATIONS
from everest.relationship import RELATIONSHIP_DIRECTIONS
from everest.relationship import Relationship
from everest.utils import get_nested_attribute
from everest.utils import set_nested_attribute

__docformat__ = 'reStructuredText en'
__all__ = ['DomainRelationship',
           'LazyDomainRelationship',
           ]


class DomainRelationship(Relationship):
    """
    Relationship between entity domain objects.
    """
    def add(self, related, direction=None, safe=False):
        self.__action(related, RELATION_OPERATIONS.ADD, direction,
                      safe)

    def remove(self, related, direction=None, safe=False):
        self.__action(related, RELATION_OPERATIONS.REMOVE,
                      direction, safe)

    def _get_specification_attributes(self):
        return self.descriptor.entity_attr, self.descriptor.entity_backref

    def __action(self, related, rel_op, direction, safe):
        if direction is None:
            direction = self.direction
        crd = self.descriptor.cardinality
        if direction & RELATIONSHIP_DIRECTIONS.FORWARD \
           and not self.descriptor.entity_attr is None:
            self.__action_one_direction(crd.relatee, rel_op, self.relator,
                                        related, self.descriptor.entity_attr,
                                        safe)
        if direction & RELATIONSHIP_DIRECTIONS.REVERSE \
           and not self.descriptor.entity_backref is None:
            self.__action_one_direction(crd.relator, rel_op, related,
                                        self.relator,
                                        self.descriptor.entity_backref,
                                        safe)

    def __action_one_direction(self, cardinality_relatee, rel_op,
                               relator, related, attr_name, safe):
        if cardinality_relatee == CARDINALITY_CONSTANTS.ONE:
            if rel_op == RELATION_OPERATIONS.ADD:
                set_nested_attribute(relator, attr_name, related)
            elif rel_op == RELATION_OPERATIONS.REMOVE:
                set_nested_attribute(relator, attr_name, None)
        else:
            relatee = get_nested_attribute(relator, attr_name)
            if rel_op == RELATION_OPERATIONS.ADD:
                if not (safe and related in relatee):
                    # FIXME: Assuming a list here.
                    relatee.append(related)
            elif rel_op == RELATION_OPERATIONS.REMOVE:
                # FIXME: Assuming a list here.
                if safe:
                    try:
                        relatee.remove(related)
                    except ValueError:
                        pass
                else:
                    relatee.remove(related)


class LazyDomainRelationship(DomainRelationship):
    """
    Lazy version of a domain relationship.

    Operations are stored and only executed when the relationship is called.
    A lazy relationship can only be used repeatedly for the same operation
    with the same options.
    """
    __relator_proxy = None
    __action = None
    __kw = None

    #: This is the relatee set dynamically through calls to .add and .remove
    relatee = None

    def _set_relator(self, relator):
        self.__relator_proxy = relator

    def _get_relator(self):
        return self.__relator_proxy.get_entity()

    relator = property(_get_relator, _set_relator)

    def add(self, related, direction=None, safe=False):
        self.__lazy_action(DomainRelationship.add, related,
                           dict(direction=direction,
                                safe=safe))

    def remove(self, related, direction=None, safe=False):
        self.__lazy_action(DomainRelationship.remove, related,
                           dict(direction=direction,
                                safe=safe))

    def __call__(self):
        if self.descriptor.cardinality.relatee == CARDINALITY_CONSTANTS.ONE:
            self.__action(self, self.relatee, **self.__kw)
        else:
            for entity in self.relatee:
                self.__action(self, entity, **self.__kw)

    def __lazy_action(self, method, related, kw):
#        # FIXME: These checks ought to be enabled!
#        if not self.__action is None and method != self.__action:
#            raise ValueError('Must use the same action for repeated use '
#                             'of a lazy relationship.')
        self.__action = method
#        if not self.__kw is None and kw != self.__kw:
#            raise ValueError('Must use the same options for repeated use '
#                             'of a lazy relationship.')
        self.__kw = kw
        if self.descriptor.cardinality.relatee == CARDINALITY_CONSTANTS.ONE:
            self.relatee = related
        else:
            if self.relatee is None:
                self.relatee = []
            self.relatee.append(related)
