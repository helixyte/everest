"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 7, 2012.
"""
from everest.mime import CsvMime
from everest.representers.attributes import MappedAttributeKey
from everest.representers.attributes import ResourceAttributeKey
from everest.representers.config import IGNORE_OPTION
from everest.representers.interfaces import IRepresenterRegistry
from everest.testing import ResourceTestCase
from everest.tests.complete_app.resources import MyEntityChildMember
from everest.tests.complete_app.resources import MyEntityMember


__docformat__ = 'reStructuredText en'
__all__ = ['MappingTestCase',
           ]


class MappingTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_rpr.zcml'

    def set_up(self):
        ResourceTestCase.set_up(self)
        rpr_reg = self.config.get_registered_utility(IRepresenterRegistry)
        self.mapping_registry = rpr_reg.get_mapping_registry(CsvMime)
        self.mapping = self.mapping_registry.find_mapping(MyEntityMember)

    def test_attribute_iterators(self):
        self.assert_true(self.mapping.mapped_class is MyEntityMember)
        attrs = list(self.mapping.attribute_iterator())
        t_attrs = list(self.mapping.terminal_attribute_iterator())
        nt_attrs = list(self.mapping.nonterminal_attribute_iterator())
        self.assert_equal(len(attrs), len(t_attrs) + len(nt_attrs))

    def test_register_non_resource_raises_error(self):
        self.assert_raises(ValueError, self.mapping_registry.create_mapping,
                           NonResource)

    def test_mapping_non_resource_raises_error(self):
        non_rc = NonResource()
        self.assert_raises(ValueError, self.mapping.map_to_data_element,
                           non_rc)

    def test_mapping_non_dataelement_raises_error(self):
        non_de = NonDataElement()
        self.assert_raises(ValueError, self.mapping.map_to_resource,
                           non_de)

    def test_mapping_access(self):
        key = MappedAttributeKey(())
        self.assert_true(str(key).startswith(key.__class__.__name__))
        attr_map = self.mapping.get_attribute_map(key=key)
        self.assert_true(attr_map['children'].options[IGNORE_OPTION]
                         is False)


class AttributeKeyTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_rpr.zcml'

    def set_up(self):
        ResourceTestCase.set_up(self)
        self.data = {('children',) : True,
                     ('children', 'children') : True}

    def test_iteration(self):
        key = ResourceAttributeKey((MyEntityMember.children,
                                    MyEntityChildMember.children))
        self.assert_true(iter(key).next() is MyEntityMember.children)
        self.assert_true(key[1] is MyEntityChildMember.children)
        self.assert_equal(len(key), 2)

    def test_attribute_key_pop(self):
        key = ResourceAttributeKey((MyEntityMember.children,))
        attr = key.pop()
        self.assert_equal(attr.resource_attr, 'children')
        self.assert_raises(KeyError, self.data.__getitem__, key)

    def test_attribute_key_append(self):
        key = ResourceAttributeKey((MyEntityMember.children,))
        key.append(MyEntityChildMember.children)
        self.assert_true(self.data[key] is True)

    def test_add(self):
        key = ResourceAttributeKey((MyEntityMember.children,)) \
              + (MyEntityChildMember.children,)
        self.assert_true(self.data[key] is True)


class NonResource(object):
    pass


class NonDataElement(object):
    pass
