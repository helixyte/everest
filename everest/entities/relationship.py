"""
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
           ]


class DomainRelationship(Relationship):
    """
    Relationship between entity domain objects.
    """
    def add(self, related, direction=None, check_existing=False):
        """
        Adds the given related entity to the relationship.

        The add operation is performed on both ends of the relationship if
        appropriate entity attribute declarations have been made.
        """
        self.__action(related, RELATION_OPERATIONS.ADD, direction,
                      check_existing)

    def remove(self, related, direction=None, check_existing=False):
        """
        Removes the given related entity from the relationship.

        The remove operation is performed on both ends of the relationship if
        appropriate entity attribute declarations have been made.
        """
        self.__action(related, RELATION_OPERATIONS.REMOVE,
                      direction, check_existing)

    def update(self, related, direction=None):
        """
        Updates the relationship with the given related entity.

        An update only affects attributes with cardinality one.
        """
        self.__action(related, RELATION_OPERATIONS.UPDATE,
                      direction, None)

    def _get_specification_attributes(self):
        return self.descriptor.entity_attr, self.descriptor.entity_backref

    def __action(self, related, rel_op, direction, check_existing):
        if direction is None:
            direction = self.direction
        crd = self.descriptor.cardinality
        if direction & RELATIONSHIP_DIRECTIONS.FORWARD \
           and not self.descriptor.entity_attr is None:
            self.__action_one_direction(crd.relatee, rel_op, self.relator,
                                        related, self.descriptor.entity_attr,
                                        check_existing)
        if direction & RELATIONSHIP_DIRECTIONS.REVERSE \
           and not self.descriptor.entity_backref is None:
            self.__action_one_direction(crd.relator, rel_op, related,
                                        self.relator,
                                        self.descriptor.entity_backref,
                                        check_existing)

    def __action_one_direction(self, cardinality_relatee, rel_op,
                               relator, related, attr_name, check_existing):
        if cardinality_relatee == CARDINALITY_CONSTANTS.ONE:
            if rel_op == RELATION_OPERATIONS.UPDATE:
                set_nested_attribute(relator, attr_name, related)
            else:
                if rel_op == RELATION_OPERATIONS.ADD:
                    set_nested_attribute(relator, attr_name, related)
                elif rel_op == RELATION_OPERATIONS.REMOVE:
                    set_nested_attribute(relator, attr_name, None)
        else:
            if rel_op == RELATION_OPERATIONS.UPDATE:
                set_nested_attribute(relator, attr_name, related)
            else:
                relatee = get_nested_attribute(relator, attr_name)
                if rel_op == RELATION_OPERATIONS.ADD:
                    if not (check_existing and related in relatee):
                        # FIXME: Assuming a list here.
                        relatee.append(related)
                elif rel_op == RELATION_OPERATIONS.REMOVE:
                    if check_existing:
                        # FIXME: Assuming a list here.
                        relatee.remove(related)
                    else:
                        try:
                            relatee.remove(related)
                        except ValueError:
                            pass
