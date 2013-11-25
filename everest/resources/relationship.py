"""
Resource relationship class.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 12, 2013.
"""
from everest.relationship import RELATIONSHIP_DIRECTIONS
from everest.relationship import Relationship

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceRelationship',
           ]


class ResourceRelationship(Relationship):
    """
    Relationship between resources.
    """
    def __init__(self, relator, descriptor,
                 direction=RELATIONSHIP_DIRECTIONS.BIDIRECTIONAL):
        Relationship.__init__(self, relator, descriptor, direction)
        self.__domain_relationship = None

    @property
    def domain_relationship(self):
        """
        Returns a domain relationship equivalent with this resource
        relationship.
        """
        if self.__domain_relationship is None:
            ent = self.relator.get_entity()
            self.__domain_relationship = \
                    self.descriptor.make_relationship(ent)
        return self.__domain_relationship

    def add(self, related, direction=None, safe=False):
        self.domain_relationship.add(related.get_entity(),
                                     direction=direction,
                                     safe=safe)

    def remove(self, related, direction=None, safe=False):
        self.domain_relationship.remove(related.get_entity(),
                                        direction=direction,
                                        safe=safe)

    def _get_specification_attributes(self):
        return self.descriptor.resource_attr, self.descriptor.resource_backref


