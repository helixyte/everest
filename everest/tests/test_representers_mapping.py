"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 7, 2012.
"""
from everest.mime import CsvMime
from everest.representers.attributes import MappedAttributeKey
from everest.representers.config import IGNORE_OPTION
from everest.representers.interfaces import IDataElement
from everest.representers.interfaces import IRepresenterRegistry
from everest.representers.traversal import DataElementTreeTraverser
from everest.representers.utils import NewRepresenterConfigurationContext
from everest.representers.utils import UpdatedRepresenterConfigurationContext
from everest.testing import ResourceTestCase
from everest.tests.complete_app.resources import MyEntityMember
from zope.interface import alsoProvides as also_provides # pylint: disable=E0611,F0401


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

    def test_mapping_invalid_dataelement_raises_error(self):
        invalid_de = InvalidKindDataElement()
        invalid_de.mapping = self.mapping # pylint: disable=W0201
        also_provides(invalid_de, IDataElement)
        trv = DataElementTreeTraverser(invalid_de, self.mapping.as_pruning())
        self.assert_raises(ValueError, trv.run, None)

    def test_mapping_access(self):
        key = MappedAttributeKey(())
        self.assert_true(str(key).startswith(key.__class__.__name__))
        attr_map = self.mapping.get_attribute_map(key=key)
        self.assert_true(attr_map['children'].options[IGNORE_OPTION]
                         is False)

    def test_representer_configuration_contexts(self):
        self.assert_raises(IndexError, self.mapping.pop_configuration)
        opts = dict(parent={IGNORE_OPTION : True})
        self.assert_false(
            self.mapping.configuration.get_attribute_option('parent',
                                                            IGNORE_OPTION))
        self.assert_false(
            self.mapping.configuration.get_attribute_option('children',
                                                            IGNORE_OPTION))
        ctx1 = NewRepresenterConfigurationContext(MyEntityMember, CsvMime,
                                                  attribute_options=opts)
        with ctx1:
            mp1 = self.mapping_registry.find_mapping(MyEntityMember)
            self.assert_true(
                    mp1.configuration.get_attribute_option('parent',
                                                           IGNORE_OPTION))
            # Changed to default.
            self.assert_is_none(
                    mp1.configuration.get_attribute_option('children',
                                                           IGNORE_OPTION))
        ctx2 = UpdatedRepresenterConfigurationContext(MyEntityMember, CsvMime,
                                                      attribute_options=opts)
        with ctx2:
            mp2 = self.mapping_registry.find_mapping(MyEntityMember)
            self.assert_true(
                    mp2.configuration.get_attribute_option('parent',
                                                           IGNORE_OPTION))
            # Unchanged.
            self.assert_false(
                    mp2.configuration.get_attribute_option('children',
                                                           IGNORE_OPTION))

class NonResource(object):
    pass


class NonDataElement(object):
    pass


class InvalidKindDataElement(object):
    def __init__(self):
        self.kind = None
