"""

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 12, 2013.
"""
from everest.constants import CARDINALITY_CONSTANTS
from everest.relationship import Relationship
from everest.utils import get_nested_attribute
from everest.utils import set_nested_attribute
from everest.constants import CASCADES

__docformat__ = 'reStructuredText en'
__all__ = ['DomainRelationship',
           ]


class DomainRelationship(Relationship):
    """
    Relationship between entity domain objects.
    """
    @property
    def specification(self):
        return self._make_specification(self.descriptor.entity_attr,
                                        self.descriptor.entity_backref)

    def add(self, related):
        """
        Adds the given related entity to the relationship.

        The add operation is performed on both ends of the relationship if
        appropriate entity attribute declarations have been made.
        """
        self.__action(related, CASCADES.ADD)
        crd = self.descriptor.cardinality
        if not self.descriptor.entity_attr is None:
            if crd.relatee == CARDINALITY_CONSTANTS.ONE:
                rel_val = get_nested_attribute(self.relator,
                                               self.descriptor.entity_attr)
                if rel_val is None:
                    set_nested_attribute(self.relator,
                                         self.descriptor.entity_attr, related)
            else:
                relatee = get_nested_attribute(self.relator,
                                               self.descriptor.entity_attr)
                if not related in relatee:
                    # FIXME: Assuming a list here.
                    relatee.append(related)
        if not self.descriptor.entity_backref is None:
            if crd.relator == CARDINALITY_CONSTANTS.ONE:
                rel_val = get_nested_attribute(related,
                                               self.descriptor.entity_backref)
                if rel_val is None:
                    set_nested_attribute(related,
                                         self.descriptor.entity_backref,
                                         self.relator)
            else:
                seq = get_nested_attribute(related,
                                           self.descriptor.entity_backref)
                if not self.relator in seq:
                    # FIXME: Assuming a list here.
                    seq.append(self.relator)


    def remove(self, related):
        """
        Removes the given related entity from the relationship.

        The remove operation is performed on both ends of the relationship if
        appropriate entity attribute declarations have been made.
        """
        self.__action(related, CASCADES.REMOVE)

    def update(self, related):
        """
        Updates the relationship with the given related entity.

        An update only affects attributes with cardinality one.
        """
        self.__action(related, CASCADES.UPDATE)

    def __action(self, related, cascade_op):
        crd = self.descriptor.cardinality
        if not self.descriptor.entity_attr is None:
            if crd.relatee == CARDINALITY_CONSTANTS.ONE:
                if cascade_op & CASCADES.REMOVE:
                    set_nested_attribute(self.relator,
                                         self.descriptor.entity_attr,
                                         None)
                if cascade_op & CASCADES.ADD:
                    rel_val = \
                        get_nested_attribute(self.relator,
                                             self.descriptor.entity_attr)
                    if rel_val is None:
                        set_nested_attribute(self.relator,
                                             self.descriptor.entity_attr,
                                             related)
            else:
                relatee = get_nested_attribute(self.relator,
                                               self.descriptor.entity_attr)
                if cascade_op == CASCADES.REMOVE:
                    try:
                        # FIXME: Assuming a list here.
                        relatee.remove(related)
                    except ValueError:
                        pass
                elif cascade_op == CASCADES.ADD:
                    if not related in relatee:
                        # FIXME: Assuming a list here.
                        relatee.append(related)
        if not self.descriptor.entity_backref is None:
            if crd.relator == CARDINALITY_CONSTANTS.ONE:
                if cascade_op & CASCADES.REMOVE:
                    set_nested_attribute(related,
                                         self.descriptor.entity_backref,
                                         None)
                if cascade_op & CASCADES.ADD:
                    rel_val = \
                        get_nested_attribute(related,
                                             self.descriptor.entity_backref)
                    if rel_val is None:
                        set_nested_attribute(related,
                                             self.descriptor.entity_backref,
                                             self.relator)
            else:
                seq = get_nested_attribute(related,
                                           self.descriptor.entity_backref)
                if cascade_op == CASCADES.REMOVE:
                    try:
                        # FIXME: Assuming a list here.
                        seq.remove(self.relator)
                    except ValueError:
                        pass
                elif cascade_op == CASCADES.ADD:
                    if not self.relator in seq:
                        # FIXME: Assuming a list here.
                        seq.append(self.relator)
