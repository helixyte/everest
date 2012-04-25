"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 25, 2012.
"""
from everest.entities.utils import get_entity_class
from everest.representers.base import RepresentationHandler
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.urlloader import LazyAttributeLoaderProxy
from everest.representers.urlloader import LazyUrlLoader
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.utils import new_stage_collection
from everest.resources.utils import provides_member_resource
from everest.url import url_to_resource
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['DataElementParser',
           'RepresentationParser',
           ]


class DataElementParser(object):
    """
    Parser accepting a data element and returning a resource.
    """
    def __init__(self, resolve_urls=True):
        self._resolve_urls = resolve_urls

    def run(self, data_element):
        if provides_member_resource(data_element.mapped_class):
            rc = self._extract_member_resource(data_element, 0)
        else:
            rc = self._extract_collection_resource(data_element, 0)
        return rc

    def _extract_member_resource(self, mb_data_el, nesting_level):
        """
        Extracts a member resource from the given data element.

        Since all value state of a resource is held in its underlying entity,
        the latter is constructed from the incoming data and then converted
        to a resource.
        """
        data = {}
        mb_cls = mb_data_el.mapped_class
        attrs = mb_data_el.mapper.get_mapped_attributes(mb_cls)
        for attr in attrs.values():
            if attr.ignore is True \
               or (attr.kind == ResourceAttributeKinds.COLLECTION
                   and nesting_level > 0 and not attr.ignore is False):
                continue
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                value = mb_data_el.get_terminal(attr)
            elif attr.kind in (ResourceAttributeKinds.MEMBER,
                               ResourceAttributeKinds.COLLECTION):
                rc_data_el = mb_data_el.get_nested(attr)
                if rc_data_el is None:
                    # Optional attribute.
                    value = None
                else:
                    if attr.kind == ResourceAttributeKinds.MEMBER:
                        if ILinkedDataElement in provided_by(rc_data_el):
                            url = rc_data_el.get_url()
                            if self._resolve_urls:
                                # Resolve URL directly and extract entity.
                                rc = url_to_resource(url)
                                value = rc.get_entity()
                            else:
                                # Prepare for lazy loading from URL.
                                value = LazyUrlLoader(url, url_to_resource)
                        else:
                            rc = self._extract_member_resource(rc_data_el,
                                                            nesting_level + 1)
                            value = rc.get_entity()
                    else:
                        if ILinkedDataElement in provided_by(rc_data_el):
                            url = rc_data_el.get_url()
                            if self._resolve_urls:
                                rc = url_to_resource(url)
                                value = [mb.get_entity() for mb in rc]
                            else:
                                # Prepare for lazy loading from URL.
                                value = LazyUrlLoader(url, url_to_resource)
                        else:
                            rc = self._extract_collection_resource(rc_data_el,
                                                            nesting_level + 1)
                            value = [mb.get_entity() for mb in rc]
            else:
                raise ValueError('Invalid resource attribute kind.')
            if not value is None:
                data[attr.entity_name] = value
        entity_cls = get_entity_class(mb_cls)
        if self._resolve_urls:
            entity = entity_cls.create_from_data(data)
        else:
            entity = LazyAttributeLoaderProxy.create(entity_cls, data)
        return mb_cls.create_from_entity(entity)

    def _extract_collection_resource(self, rc_data_el, nesting_level):
        """
        Extracts a collection resource from the given data element.
        """
        coll_cls = rc_data_el.mapped_class
        coll = new_stage_collection(coll_cls)
        for member_el in rc_data_el.get_members():
            mb = self._extract_member_resource(member_el, nesting_level + 1)
            coll.add(mb)
        return coll


class RepresentationParser(RepresentationHandler):

    def run(self):
        """
        :return: the parsed resource.
        """
        raise NotImplementedError('Abstract method.')


