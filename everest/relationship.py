"""
Relationships between entities or resources.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Sep 30, 2011.
"""
from everest.constants import CARDINALITY_CONSTANTS
from everest.querying.utils import get_filter_specification_factory

__docformat__ = 'reStructuredText en'
__all__ = ['Relationship',
           ]


class Relationship(object):
    """
    Abstract base class for resource and domain relationships.
    """
    def __init__(self, relator, descriptor):
        self.relator = relator
        self.descriptor = descriptor

    @property
    def specification(self):
        """
        Returns a filter specification for the objects defined by this
        relationship.
        """
        raise NotImplementedError('Abstract method.')

    def _make_specification(self, ref_attr, backref_attr):
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
