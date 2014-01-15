"""
Relationships between entities or resources.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Sep 30, 2011.
"""
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import RELATIONSHIP_DIRECTIONS
from everest.interfaces import IRelationship
from everest.querying.utils import get_filter_specification_factory
from everest.utils import get_nested_attribute
from zope.interface import implementer # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['Relationship',
           ]


@implementer(IRelationship)
class Relationship(object):
    """
    Abstract base class for resource and domain relationships.

    A relationship has a source ("relator") and a target ("relatee") and
    implements the relationship operations "ADD", "REMOVE" and "UPDATE".
    """
    def __init__(self, relator, descriptor,
                 direction=RELATIONSHIP_DIRECTIONS.BIDIRECTIONAL):
        self.relator = relator
        self.descriptor = descriptor
        self.direction = direction

    @property
    def specification(self):
        return self.__make_specification()

    def add(self, related, direction=None, safe=False):
        raise NotImplementedError('Abstract method.')

    def remove(self, related, direction=None, safe=False):
        raise NotImplementedError('Abstract method.')

    def _get_specification_attributes(self):
        raise NotImplementedError('Abstract method.')

    def __make_specification(self):
        ref_attr, backref_attr = self._get_specification_attributes()
        #: Builds the filter specification.
        spec_fac = get_filter_specification_factory()
        crd = self.descriptor.cardinality
        if backref_attr is None:
            relatee = get_nested_attribute(self.relator, ref_attr)
            if crd.relatee == CARDINALITY_CONSTANTS.MANY:
                # This is potentially expensive as we may need to iterate over
                # a large collection to create the "contained" specification.
                if len(relatee) > 0:
                    ids = [related.id for related in relatee]
                    spec = spec_fac.create_contained('id', ids)
                else:
                    # Create impossible search criterion.
                    spec = spec_fac.create_equal_to('id', -1)
            else:
                if not relatee is None:
                    spec = spec_fac.create_equal_to('id', relatee.id)
                else:
                    # Create impossible search criterion.
                    spec = spec_fac.create_equal_to('id', -1)
        else:
            if crd.relator == CARDINALITY_CONSTANTS.MANY:
                spec = spec_fac.create_contains(backref_attr, self.relator)
            else:
                spec = spec_fac.create_equal_to(backref_attr, self.relator)
        return spec

    def __str__(self):
        rel_char = '-'
        if self.direction & RELATIONSHIP_DIRECTIONS.FORWARD:
            rel_char += '>'
        if self.direction & RELATIONSHIP_DIRECTIONS.REVERSE:
            rel_char = '<' + rel_char
        return "%s %s%s%s" % (self.__class__.__name__, self.relator,
                              rel_char, self.descriptor.resource_attr)
