"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 13, 2013.
"""
from everest.entities.attributes import get_domain_class_attribute
from everest.entities.relationship import DomainRelationship
from everest.querying.specifications import ValueContainedFilterSpecification
from everest.querying.specifications import ValueContainsFilterSpecification
from everest.querying.specifications import ValueEqualToFilterSpecification
from everest.resources.attributes import get_resource_class_attribute
from everest.resources.relationship import ResourceRelationship
from everest.resources.utils import get_root_collection
from everest.testing import EntityTestCase
from everest.testing import ResourceTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild
from everest.tests.complete_app.interfaces import IMyEntityParent
from mock import patch

__docformat__ = 'reStructuredText en'
__all__ = ['DomainRelationshipTestCase',
           ]


class DomainRelationshipTestCase(EntityTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_entity_attr(self):
        attr = get_domain_class_attribute(IMyEntity, 'parent')
        my_parent = MyEntityParent(id=0)
        self._run_test(attr, my_parent, 'child',
                       ValueEqualToFilterSpecification,
                       ValueEqualToFilterSpecification, 0)
        attr = get_domain_class_attribute(IMyEntityChild, 'parent')
        my_child = MyEntityChild(id=1)
        self._run_test(attr, my_child, 'children',
                       ValueContainsFilterSpecification,
                       ValueEqualToFilterSpecification, 1)

    def test_aggregate_attr(self):
        attr = get_domain_class_attribute(IMyEntity, 'children')
        my_child = MyEntityChild(id=0)
        self._run_test(attr, my_child, 'parent',
                       ValueEqualToFilterSpecification,
                       ValueContainedFilterSpecification, [0])

    def test_string_representation(self):
        attr = get_domain_class_attribute(IMyEntity, 'children')
        my_child = MyEntityChild(id=0)
        rel = attr.make_relationship(my_child)
        self.assert_true('<->' in str(rel))

    def _run_test(self, attr, relatee, backref_attr_name,
                  backref_relatee_spec_class,
                  ref_relatee_spec_class, relatee_spec_value):
        my_ent = MyEntity(id=0)
        rel = attr.make_relationship(my_ent)
        # With a backref, the spec references the relator.
        self.assert_true(isinstance(rel.specification,
                                    backref_relatee_spec_class))
        self.assert_equal(rel.specification.attr_name, backref_attr_name)
        self.assert_equal(rel.specification.attr_value, my_ent)
        # Without a backref, the spec references the relatee.
        with patch.object(attr.__class__, 'entity_backref', None):
            self.assert_true(isinstance(rel.specification,
                                        ValueEqualToFilterSpecification))
            self.assert_equal(rel.specification.attr_name, 'id')
            # Without a relatee, we get a non-matching spec.
            self.assert_equal(rel.specification.attr_value, -1)
            # When a relatee, its ID becomes available in the spec.
            rel.add(relatee)
            self.assert_true(isinstance(rel.specification,
                                        ref_relatee_spec_class))
            self.assert_equal(rel.specification.attr_value,
                              relatee_spec_value)


class ResourceRelationshipTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_make_relationship(self):
        ent = MyEntity(id=0)
        coll = get_root_collection(IMyEntity)
        mb = coll.create_member(ent)
        attr = get_resource_class_attribute(IMyEntity, 'parent')
        rel = attr.make_relationship(mb)
        self.assert_true(isinstance(rel, ResourceRelationship))
        parent = MyEntityParent(id=0)
        parent_coll = get_root_collection(IMyEntityParent)
        parent_mb = parent_coll.create_member(parent)
        self.assert_true(ent.parent is None)
        rel.add(parent_mb)
        self.assert_true(ent.parent is parent)
        rel.remove(parent_mb)
        self.assert_true(ent.parent is None)
        rel = attr.make_relationship(ent)
        self.assert_true(isinstance(rel, DomainRelationship))
        self.assert_raises(ValueError, attr.make_relationship, None)
