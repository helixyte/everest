"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 7, 2012.
"""
from collections import OrderedDict
import datetime

import pytest
from pytz import timezone

from everest.constants import RESOURCE_KINDS
from everest.representers.attributes import MappedAttribute
from everest.representers.csv import CsvLinkedDataElement
from everest.representers.dataelements import DataElementAttributeProxy
from everest.representers.dataelements import SimpleCollectionDataElement
from everest.representers.dataelements import SimpleLinkedDataElement
from everest.representers.dataelements import SimpleMemberDataElement
from everest.resources.attributes import get_resource_class_attribute
from everest.tests.complete_app.resources import MyEntityMember

from pyramid.compat import iteritems_


__docformat__ = 'reStructuredText en'
__all__ = ['TestDataElements',
           ]


class TestDataElements(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_member_data_element(self):
        data_el = SimpleMemberDataElement.create()
        # Test nesteds.
        assert list(data_el.nesteds.keys()) == []
        parent_data_el = SimpleMemberDataElement.create()
        rc_nested_attr = \
            get_resource_class_attribute(MyEntityMember, 'parent')
        mp_nested_attr = MappedAttribute(rc_nested_attr)
        data_el.set_nested(mp_nested_attr, parent_data_el)
        assert data_el.get_nested(mp_nested_attr) is parent_data_el
        assert list(data_el.nesteds.keys()) == ['parent']
        # Test terminals.
        assert list(data_el.terminals.keys()) == []
        utc = timezone('UTC')
        ldt = datetime.datetime(2012, 8, 29, 16, 20, 0, tzinfo=utc)
        term_attr_data = OrderedDict(text='foo',
                                     number=0,
                                     date_time=ldt)
        for term_attr_name, term_attr_value in term_attr_data.items():
            rc_attr = get_resource_class_attribute(MyEntityMember,
                                                   term_attr_name)
            mp_attr = MappedAttribute(rc_attr)
            # Check setting to None value.
            data_el.set_terminal(mp_attr, None)
            assert data_el.get_terminal(mp_attr) is None
            data_el.set_terminal_converted(mp_attr, None)
            assert data_el.get_terminal(mp_attr) is None
            # Check setting to value.
            data_el.set_terminal(mp_attr, term_attr_value)
            assert data_el.get_terminal(mp_attr) == term_attr_value
            rpr_val = data_el.get_terminal_converted(mp_attr)
            data_el.set_terminal_converted(mp_attr, rpr_val)
            assert data_el.get_terminal(mp_attr) == term_attr_value
        assert list(data_el.terminals.keys()) == list(term_attr_data.keys())
        # Printing.
        prt_str = str(data_el)
        assert prt_str.startswith(data_el.__class__.__name__)
        assert prt_str.endswith(')')
        # Attribute iteration.
        for attr_name, attr_value in iteritems_(term_attr_data):
            assert data_el.get_attribute(attr_name) == attr_value
        for de_attr_name, de_attr_value in data_el.iterator():
            if de_attr_name in term_attr_data:
                assert de_attr_value == term_attr_data[de_attr_name]

    def test_printing_with_none_value(self):
        data_el = SimpleMemberDataElement.create()
        assert list(data_el.terminals.keys()) == []
        rc_attr = get_resource_class_attribute(MyEntityMember, 'text')
        mp_attr = MappedAttribute(rc_attr)
        data_el.set_terminal(mp_attr, None) # Need one None attr value.
        prt_str = str(data_el)
        assert prt_str.startswith(data_el.__class__.__name__)
        assert prt_str.endswith(')')

    def test_collection_data_element(self):
        coll_data_el = SimpleCollectionDataElement.create()
        mb_data_el1 = SimpleMemberDataElement.create()
        mb_data_el2 = SimpleMemberDataElement.create()
        coll_data_el.add_member(mb_data_el1)
        coll_data_el.add_member(mb_data_el2)
        assert len(coll_data_el) == 2
        assert coll_data_el.members == [mb_data_el1, mb_data_el2]
        # Printing.
        prt_str = str(coll_data_el)
        assert prt_str.startswith(coll_data_el.__class__.__name__)
        assert prt_str.endswith(']')

    def test_linked_collection_data_element(self, collection):
        agg = collection.get_aggregate()
        with pytest.raises(ValueError):
            CsvLinkedDataElement.create_from_resource(agg)
        data_el = CsvLinkedDataElement.create_from_resource(collection)
        assert data_el.get_title() == 'Collection of MyEntityMember'
        assert data_el.get_url().find('/my-entities/') != -1
        assert data_el.get_kind() == RESOURCE_KINDS.COLLECTION
        assert data_el.get_relation() == 'http://test.org/myentity-collection'
        # Can not use data element attribute proxy with a link.
        with pytest.raises(ValueError):
            DataElementAttributeProxy(data_el)
        assert str(data_el).startswith(data_el.__class__.__name__)

    def test_linked_member_data_element(self):
        mb_data_el = SimpleLinkedDataElement.create('http://dummy',
                                                    RESOURCE_KINDS.MEMBER,
                                                    id=0)
        assert mb_data_el.get_kind() == RESOURCE_KINDS.MEMBER
        assert mb_data_el.get_id() == 0
