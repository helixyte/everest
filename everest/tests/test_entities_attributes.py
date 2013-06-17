"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 11, 2013.
"""
from everest.constants import DomainAttributeKinds
from everest.entities.attributes import get_domain_class_aggregate_attribute_iterator
from everest.entities.attributes import get_domain_class_attribute
from everest.entities.attributes import get_domain_class_attribute_names
from everest.entities.attributes import get_domain_class_attributes
from everest.entities.attributes import get_domain_class_domain_attribute_iterator
from everest.entities.attributes import get_domain_class_entity_attribute_iterator
from everest.entities.attributes import get_domain_class_terminal_attribute_iterator
from everest.entities.attributes import is_domain_class_aggregate_attribute
from everest.entities.attributes import is_domain_class_domain_attribute
from everest.entities.attributes import is_domain_class_entity_attribute
from everest.entities.attributes import is_domain_class_terminal_attribute
from everest.repositories.rdb.utils import RdbTestCaseMixin
from everest.testing import EntityTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.interfaces import IMyEntity

__docformat__ = 'reStructuredText en'
__all__ = ['EntityAttributesTestCase',
           ]


class EntityAttributesTestCase(RdbTestCaseMixin, EntityTestCase):
    package_name = 'everest.tests.complete_app'

    def _test_accessors(self, obj):
        names = get_domain_class_attribute_names(obj)
        self.assert_equal(names,
                          ['id', 'parent', 'children', 'text', 'text_ent',
                           'number', 'date_time', 'parent.text_ent'])
        self.assert_equal(get_domain_class_attributes(obj).keys(),
                          names)
        term_attr_name = 'number'
        term_attr = get_domain_class_attribute(obj, term_attr_name)
        self.assert_equal(term_attr.entity_attr, term_attr_name)
        self.assert_true(
                    is_domain_class_terminal_attribute(obj, term_attr_name))
        ent_attr_name = 'parent'
        ent_attr = get_domain_class_attribute(obj, ent_attr_name)
        self.assert_equal(ent_attr.entity_attr, ent_attr_name)
        self.assert_true(
                    is_domain_class_entity_attribute(obj, ent_attr_name))
        self.assert_true(
                    is_domain_class_domain_attribute(obj, ent_attr_name))
        agg_attr_name = 'children'
        agg_attr = get_domain_class_attribute(obj, agg_attr_name)
        self.assert_equal(agg_attr.entity_attr, agg_attr_name)
        self.assert_true(
                    is_domain_class_aggregate_attribute(obj, agg_attr_name))
        self.assert_true(
                    is_domain_class_domain_attribute(obj, agg_attr_name))
        for attr in get_domain_class_terminal_attribute_iterator(obj):
            self.assert_equal(attr.kind, DomainAttributeKinds.TERMINAL)
        for attr in get_domain_class_entity_attribute_iterator(obj):
            self.assert_equal(attr.kind, DomainAttributeKinds.ENTITY)
        for attr in get_domain_class_aggregate_attribute_iterator(obj):
            self.assert_equal(attr.kind, DomainAttributeKinds.AGGREGATE)
        for attr in get_domain_class_domain_attribute_iterator(obj):
            self.assert_true(attr.kind in (DomainAttributeKinds.ENTITY,
                                           DomainAttributeKinds.AGGREGATE))

    def test_accessors_with_interface(self):
        self._test_accessors(IMyEntity)

    def test_accessors_with_entity_class(self):
        self._test_accessors(MyEntity)
