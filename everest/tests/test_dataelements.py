"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 7, 2012.
"""
from everest.representers.csv import CsvLinkedDataElement
from everest.representers.dataelements import DataElementAttributeProxy
from everest.representers.dataelements import SimpleCollectionDataElement
from everest.representers.dataelements import SimpleMemberDataElement
from everest.resources.kinds import ResourceKinds
from everest.resources.utils import get_collection_class
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.resources import MyEntityMember
from everest.tests.testapp_db.testing import create_collection

__docformat__ = 'reStructuredText en'
__all__ = ['DataElementsTestCase',
           ]


class DataElementsTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_member_data_element(self):
        rc = object.__new__(MyEntityMember)
        data_el1 = SimpleMemberDataElement.create_from_resource(rc)
        self.assert_equal(data_el1.terminals.keys(), [])
        data_el2 = SimpleMemberDataElement.create_from_resource(rc)
        self.assert_equal(data_el2.nesteds.keys(), [])
        terminal_value = 'foo'
        data_el2.set_terminal('foo', terminal_value)
        data_el2.set_terminal('bar', None)
        self.assert_equal(data_el2.get_terminal('foo'), terminal_value)
        self.assert_equal(data_el2.get_terminal('bar'), None)
        data_el1.set_nested('bar', data_el2)
        self.assert_equal(data_el1.get_nested('bar'), data_el2)
        self.assert_equal(data_el2.terminals.keys(), ['foo', 'bar'])
        self.assert_equal(data_el1.nesteds.keys(), ['bar'])
        self.assert_true(str(data_el1).startswith(data_el1.__class__.__name__))

    def test_collection_data_element(self):
        rc = object.__new__(get_collection_class(IMyEntity))
        data_el = SimpleCollectionDataElement.create_from_resource(rc)
        self.assert_true(str(data_el).startswith(data_el.__class__.__name__))
        self.assert_equal(len(data_el), 0)
        self.assert_equal(data_el.members, [])

    def test_linked_data_element(self):
        rc = create_collection()
        self.assert_raises(ValueError,
                           CsvLinkedDataElement.create_from_resource,
                           rc.get_aggregate())
        data_el = CsvLinkedDataElement.create_from_resource(rc)
        self.assert_equal(data_el.get_title(), 'Collection of MyEntityMember')
        self.assert_not_equal(data_el.get_url().find('/my-entities/'), -1)
        self.assert_equal(data_el.get_kind(), ResourceKinds.COLLECTION)
        self.assert_equal(data_el.get_relation(),
                          'http://test.org/myentity-collection')
        # Can not use data element attribute proxy with a link.
        self.assert_raises(ValueError, DataElementAttributeProxy, data_el)
        self.assert_true(str(data_el).startswith(data_el.__class__.__name__))

