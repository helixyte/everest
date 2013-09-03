"""
Relationships between entities or resources.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Sep 30, 2011.
"""
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import RELATIONSHIP_DIRECTIONS
from everest.querying.utils import get_filter_specification_factory

__docformat__ = 'reStructuredText en'
__all__ = ['Relationship',
           ]


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
        self.__specification = None

    @property
    def specification(self):
        """
        Returns a filter specification for the objects defined by this
        relationship.
        """
        if self.__specification is None:
            self.__specification = self.__make_specification()
        return self.__specification

    def _get_specification_attributes(self):
        raise NotImplementedError('Abstract method.')

    def __make_specification(self):
        ref_attr, backref_attr = self._get_specification_attributes()
        #: Builds the filter specification.
        spec_fac = get_filter_specification_factory()
        crd = self.descriptor.cardinality
        if backref_attr is None:
            relatee = getattr(self.relator, ref_attr)
            if crd.relatee == CARDINALITY_CONSTANTS.MANY:
                # This is potentially expensive as we may need to iterate over
                # a large collection to create the "contained" specification.
                if len(relatee) > 0:
                    ids = [related.id for related in relatee]
                    spec = spec_fac.create_contained('id', ids)
                else:
                    # Create impossible search criterion.
                    spec = spec_fac.create_equal_to('id', None)
            else:
                if not relatee is None:
                    spec = spec_fac.create_equal_to('id', relatee.id)
                else:
                    # Create impossible search criterion.
                    spec = spec_fac.create_equal_to('id', None)
        else:
            if crd.relator == CARDINALITY_CONSTANTS.MANY:
                spec = spec_fac.create_contains(backref_attr, self.relator)
            else:
                spec = spec_fac.create_equal_to(backref_attr, self.relator)
        return spec

    def add(self, related, direction=None, check_existing=False):
        raise NotImplementedError('Abstract method.')

    def remove(self, related, direction=None, check_existing=False):
        raise NotImplementedError('Abstract method.')

    def update(self, related, direction=None):
        raise NotImplementedError('Abstract method.')
