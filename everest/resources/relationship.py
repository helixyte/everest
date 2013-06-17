"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 12, 2013.
"""
from everest.entities.attributes import get_domain_class_attribute
from everest.relationship import Relationship

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceRelationship',
           ]


class ResourceRelationship(Relationship):
    """
    Relationship between resources.
    """
    @property
    def domain_relationship(self):
        """
        Returns a domain relationship equivalent with this resource
        relationship.
        """
        ent = self.relator.get_entity()
        attr = get_domain_class_attribute(ent, self.descriptor.entity_attr)
        return attr.make_relationship(ent)

    @property
    def specification(self):
        return self._make_specification(self.descriptor.resource_attr,
                                        self.descriptor.resource_backref)


