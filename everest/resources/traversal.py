"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2013.
"""
from everest.attributes import get_attribute_cardinality
from everest.constants import CARDINALITY_CONSTANTS
from everest.constants import RELATIONSHIP_DIRECTIONS
from everest.interfaces import IDataTraversalProxyFactory
from everest.resources.attributes import get_resource_class_attribute_iterator
from everest.resources.interfaces import ICollectionResource
from everest.traversal import DataTraversalProxy
from everest.traversal import DataTraversalProxyAdapter
from everest.utils import get_nested_attribute
from pyramid.threadlocal import get_current_registry
from everest.entities.utils import get_entity_class

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceDataTraversalProxy',
           'ResourceDataTraversalProxyAdapter',
            ]


class ResourceDataTraversalProxy(DataTraversalProxy):
    def get_id(self):
        return self._data.id

    def _get_entity_type(self):
        return get_entity_class(type(self._data))

    def get_entity(self):
        return self._data.get_entity()

    def _attribute_iterator(self):
        return get_resource_class_attribute_iterator(self._data)

    def _get_relation_attribute_value(self, attribute):
        rc = get_nested_attribute(self._data, attribute.resource_attr)
        if get_attribute_cardinality(attribute) == CARDINALITY_CONSTANTS.MANY:
            value = [mb.get_entity() for mb in rc]
        else:
            value = rc
        return value

    def _get_proxied_attribute_value(self, attribute):
        return get_nested_attribute(self._data, attribute.resource_attr)

    def _make_accessor(self, value_type):
        return self._accessor.get_root_collection(value_type)


class ResourceDataTraversalProxyAdapter(DataTraversalProxyAdapter):
    proxy_class = ResourceDataTraversalProxy

    def make_source_proxy(self, options=None):
        rel_drct = RELATIONSHIP_DIRECTIONS.NONE
        return self.make_proxy(None, rel_drct, options)

    def make_target_proxy(self, accessor,
                          manage_back_references=True, options=None):
        rel_drct = RELATIONSHIP_DIRECTIONS.BIDIRECTIONAL
        if not manage_back_references:
            rel_drct &= ~RELATIONSHIP_DIRECTIONS.REVERSE
        return self.make_proxy(accessor, rel_drct, options)

    def make_proxy(self, accessor, relationship_direction, options=None):
        if ICollectionResource.providedBy(self._data): # pylint:disable=E1101
            reg = get_current_registry()
            prx_fac = reg.getUtility(IDataTraversalProxyFactory)
            prx = prx_fac.make_proxy([mb.get_entity() for mb in self._data],
                                     accessor, relationship_direction,
                                     options=options)
        else:
            prx = DataTraversalProxyAdapter.make_proxy(
                                                self._data.get_entity(),
                                                accessor,
                                                relationship_direction,
                                                options=options)
        return prx
