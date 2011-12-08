"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Resource relation classes.

Created on Sep 30, 2011.
"""

from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from everest.querying.specifications import IFilterSpecificationFactory

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceRelation',
           ]

class ResourceRelation(object):
    """
    Represents a relation between two resources (relator and relatee).

    :ivar relator: relator entity
    :ivar relatee: relatee entity collection
    :ivar relator_attribute: name of the attribute holding the
        collection of entities in this relation
    :ivar relatee_attribute: if given, this specifies the name of an
        attribute of the entities in this relation that references the
        relator entity.
    """
    def __init__(self, resource, relator_attribute,
                 relatee_attribute=None, make_absolute=True):
        self.__resource = resource
        self.relator_attribute = relator_attribute
        self.relatee_attribute = relatee_attribute
        self.make_absolute = make_absolute

    @property
    def relator(self):
        return self.__resource.get_entity()

    @property
    def relatee(self):
        ent = self.__resource.get_entity()
        return getattr(ent, self.relator_attribute)

    def make_relation_spec(self):
        # Build a relation spec we need to build an absolute URL for this
        # relation aggregate.
        spec_fac = get_utility(IFilterSpecificationFactory)
        if not self.relatee_attribute is None:
            # Simple 1:n case: Build a related.attr_name == resource
            # specification.
            rel_spec = spec_fac.create_equal_to(self.relatee_attribute,
                                                self.__resource)
        else:
            # Complex n:m case: Iterate over the entities in the
            # collection and union id == entity.id specifications.
            entities = getattr(self.relator, self.relator_attribute)
            if len(entities) > 0:
                ids = [entity.id for entity in entities]
                rel_spec = spec_fac.create_contained('id', ids)
#                specs = [spec_fac.create_equal_to('id', entity.id)
#                         for entity in entities]
#                rel_spec = reduce(spec_fac.create_disjunction, specs)
            else:
                # Create impossible search criterion for empty collection.
                rel_spec = spec_fac.create_equal_to('id', -1)
        return rel_spec

    def make_filter_spec(self, filter_spec):
        if self.make_absolute:
            rel_spec = self.make_relation_spec()
            if filter_spec is None:
                spec = rel_spec
            else:
                spec_fac = get_utility(IFilterSpecificationFactory)
                spec = spec_fac.create_conjunction((rel_spec, filter_spec))
        else:
            spec = filter_spec
        return spec

