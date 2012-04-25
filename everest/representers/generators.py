"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 25, 2012.
"""
from everest.representers.base import RepresentationHandler
from everest.representers.interfaces import ICustomDataElement
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.link import Link
from everest.resources.utils import provides_member_resource
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['DataElementGenerator',
           'RepresentationGenerator',
           ]


class DataElementGenerator(object):
    """
    Generator accepting a resource and returning a data element.
    """
    def __init__(self, data_element_registry):
        self._data_element_registry = data_element_registry

    def run(self, resource, mapping_info=None):
        if provides_member_resource(type(resource)):
            data_el = self._inject_member_resource(resource, 0,
                                                   mapping_info)
        else:
            data_el = self._inject_collection_resource(resource, 0,
                                                       mapping_info)
        return data_el

    def _inject_member_resource(self, member, nesting_level, mapping_info):
        de_reg = self._data_element_registry
        de_cls = de_reg.get_data_element_class(type(member))
        mb_data_el = de_cls.create_from_resource(member)
        mapped_attrs = mb_data_el.mapper.get_mapped_attributes(
                                                    mb_data_el.mapped_class,
                                                    info=mapping_info)
        self._inject_member_content(mb_data_el, member, mapped_attrs.values(),
                                    nesting_level)
        return mb_data_el

    def _inject_collection_resource(self, collection, nesting_level,
                                    mapping_info):
        de_reg = self._data_element_registry
        coll_de_cls = de_reg.get_data_element_class(type(collection))
        coll_data_el = coll_de_cls.create_from_resource(collection)
        if ICustomDataElement in provided_by(coll_data_el):
            # Custom resource injection.
            coll_data_el.inject(collection)
        else:
            for member in collection:
                mapped_attrs = \
                  coll_data_el.mapper.get_mapped_attributes(type(member),
                                                            info=mapping_info)
                mb_de_cls = de_reg.get_data_element_class(type(member))
                mb_data_el = mb_de_cls.create_from_resource(member)
                self._inject_member_content(mb_data_el, member,
                                            mapped_attrs.values(),
                                            nesting_level + 1)
                coll_data_el.add_member(mb_data_el)
        return coll_data_el

    def _inject_member_content(self, data_element, member, mapped_attributes,
                               nesting_level):
        if ICustomDataElement in provided_by(data_element):
            # Custom resource injection.
            data_element.inject(member)
        else:
            for attr in mapped_attributes:
                if self._is_ignored_attr(attr, nesting_level):
                    continue
                value = getattr(member, attr.name)
                if value is None:
                    # None values are ignored.
                    continue
                self._inject_attribute(data_element, attr, value,
                                       nesting_level)

    def _inject_attribute(self, data_element, attr, value, nesting_level):
        """
        Injects the given value as attribute of the given name into the given
        data element (inverse operation to `_extract_attribute`).

        :param data_element: data element to inject an attribute into
          (:class:`DateElement` instance).
        :param attr: mapped attribute (:class:`MappedAttribute` instance).
        :param value: value to inject.
        :param int nesting_level: nesting level of this data element in the
          tree
        """
        if attr.kind == ResourceAttributeKinds.TERMINAL:
            data_element.set_terminal(attr, value)
        else:
            if not attr.write_as_link is False:
                rc_data_el = self._inject_link(value)
            else:
                if attr.kind == ResourceAttributeKinds.MEMBER:
                    rc_data_el = self._inject_member_resource(value,
                                                              nesting_level + 1,
                                                              None)
                else:
                    rc_data_el = \
                            self._inject_collection_resource(value,
                                                             nesting_level + 1,
                                                             None)
            data_element.set_nested(attr, rc_data_el)

    def _inject_link(self, rc):
        de_reg = self._data_element_registry
        link_de_cls = de_reg.get_data_element_class(Link)
        return link_de_cls.create_from_resource(rc)

    def _is_ignored_attr(self, attr, nesting_level):
        """
        Checks whether the given attribute should be ignored at the given
        nesting level.

        The default behavior is to ignore nested collection attributes.
        """
        return attr.ignore is True \
                or (attr.kind == ResourceAttributeKinds.COLLECTION
                    and nesting_level > 0 and not attr.ignore is False)


class RepresentationGenerator(RepresentationHandler):

    def run(self, data_element):
        """
        :param data_element: the `class:`DataElement` to be serialized.
        """
        raise NotImplementedError('Abstract method.')

