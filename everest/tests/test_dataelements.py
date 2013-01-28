"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 7, 2012.
"""
from collections import OrderedDict
from everest.representers.attributes import MappedAttribute
from everest.representers.csv import CsvLinkedDataElement
from everest.representers.dataelements import DataElementAttributeProxy
from everest.representers.dataelements import SimpleCollectionDataElement
from everest.representers.dataelements import SimpleMemberDataElement
from everest.resources.kinds import ResourceKinds
from everest.testing import ResourceTestCase
from everest.tests.complete_app.resources import MyEntityMember
from everest.tests.complete_app.testing import create_collection
from pytz import timezone
import datetime

__docformat__ = 'reStructuredText en'
__all__ = ['DataElementsTestCase',
           ]


class DataElementsTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_member_data_element(self):
        data_el = SimpleMemberDataElement.create()
        # Test nesteds.
        self.assert_equal(data_el.nesteds.keys(), [])
        parent_data_el = SimpleMemberDataElement.create()
        rc_nested_attr = MyEntityMember.get_attributes()['parent']
        mp_nested_attr = MappedAttribute(rc_nested_attr)
        data_el.set_nested(mp_nested_attr, parent_data_el)
        self.assert_true(data_el.get_nested(mp_nested_attr) is parent_data_el)
        self.assert_equal(data_el.nesteds.keys(), ['parent'])
        # Test terminals.
        self.assert_equal(data_el.terminals.keys(), [])
        utc = timezone('UTC')
        ldt = datetime.datetime(2012, 8, 29, 16, 20, 0, tzinfo=utc)
        term_attr_data = OrderedDict(text='foo',
                                     number=0,
                                     date_time=ldt)
        for term_attr_name, term_attr_value in term_attr_data.items():
            rc_attr = MyEntityMember.get_attributes()[term_attr_name]
            mp_attr = MappedAttribute(rc_attr)
            # Check setting to None value.
            data_el.set_terminal(mp_attr, None)
            self.assert_true(data_el.get_terminal(mp_attr) is None)
            data_el.set_terminal_converted(mp_attr, None)
            self.assert_true(data_el.get_terminal(mp_attr) is None)
            # Check setting to value.
            data_el.set_terminal(mp_attr, term_attr_value)
            self.assert_equal(data_el.get_terminal(mp_attr), term_attr_value)
            rpr_val = data_el.get_terminal_converted(mp_attr)
            data_el.set_terminal_converted(mp_attr, rpr_val)
            self.assert_equal(data_el.get_terminal(mp_attr), term_attr_value)
        self.assert_equal(data_el.terminals.keys(), term_attr_data.keys())
        # Printing.
        prt_str = str(data_el)
        self.assert_true(prt_str.startswith(data_el.__class__.__name__))
        self.assert_true(prt_str.endswith(')'))

    def test_printing_with_none_value(self):
        data_el = SimpleMemberDataElement.create()
        self.assert_equal(data_el.terminals.keys(), [])
        rc_attr = MyEntityMember.get_attributes()['text']
        mp_attr = MappedAttribute(rc_attr)
        data_el.set_terminal(mp_attr, None) # Need one None attr value.
        prt_str = str(data_el)
        self.assert_true(prt_str.startswith(data_el.__class__.__name__))
        self.assert_true(prt_str.endswith(')'))

    def test_collection_data_element(self):
        coll_data_el = SimpleCollectionDataElement.create()
        mb_data_el1 = SimpleMemberDataElement.create()
        mb_data_el2 = SimpleMemberDataElement.create()
        coll_data_el.add_member(mb_data_el1)
        coll_data_el.add_member(mb_data_el2)
        self.assert_equal(len(coll_data_el), 2)
        self.assert_equal(coll_data_el.members, [mb_data_el1, mb_data_el2])
        # Printing.
        prt_str = str(coll_data_el)
        self.assert_true(prt_str.startswith(coll_data_el.__class__.__name__))
        self.assert_true(prt_str.endswith(']'))

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

