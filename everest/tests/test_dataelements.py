"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 7, 2012.
"""
from everest.representers.csv import CsvCollectionDataElement
from everest.representers.csv import CsvLinkedDataElement
from everest.resources.utils import get_collection_class
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.testing import create_collection
from everest.resources.kinds import ResourceKinds
from everest.representers.dataelements import DataElementAttributeProxy

__docformat__ = 'reStructuredText en'
__all__ = ['DataElementsTestCase',
           ]


class DataElementsTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_basics(self):
        rc_cls = get_collection_class(IMyEntity)
        rc = object.__new__(rc_cls)
        data_el = CsvCollectionDataElement.create_from_resource(rc)
        self.assert_true(str(data_el).startswith(data_el.__class__.__name__))

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

