"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 9, 2012.
"""
from everest.mime import CsvMime
from everest.representers.config import IGNORE_ON_READ_OPTION
from everest.representers.config import IGNORE_ON_WRITE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.dataelements import DataElementAttributeProxy
from everest.representers.utils import get_mapping_registry
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.resources import MyEntityMember
from everest.tests.testapp_db.testing import create_entity

__docformat__ = 'reStructuredText en'
__all__ = []


class MappingTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_defaults(self):
        mp_reg = get_mapping_registry(CsvMime)
        mp = mp_reg.find_or_create_mapping(MyEntityMember)
        attrs = mp.get_attribute_map()
        self.assert_true(
            attrs['text'].options.get(IGNORE_ON_READ_OPTION) is None)
        self.assert_true(
            attrs['text'].options.get(IGNORE_ON_WRITE_OPTION) is None)
        self.assert_true(
            attrs['parent'].options.get(IGNORE_ON_READ_OPTION) is None)
        self.assert_true(
            attrs['parent'].options.get(IGNORE_ON_WRITE_OPTION) is None)
        key = ('parent',)
        parent_attrs = mp.get_attribute_map(key)
        self.assert_true(
            parent_attrs['text'].options.get(IGNORE_ON_READ_OPTION) is None)
        self.assert_true(
            parent_attrs['text'].options.get(IGNORE_ON_WRITE_OPTION) is None)

    def test_clone_with_options(self):
        mp_reg = get_mapping_registry(CsvMime)
        mp = mp_reg.find_or_create_mapping(MyEntityMember)
        mp1 = mp.clone(
                mapping_options={('parent', 'text'):
                                        {IGNORE_ON_READ_OPTION:True}})
        key = ('parent',)
        parent_attrs = mp1.get_attribute_map(key)
        self.assert_true(
            parent_attrs['text'].options.get(IGNORE_ON_READ_OPTION) is True)

    def test_map_to_data_element(self):
        entity = create_entity()
        mb = MyEntityMember.create_from_entity(entity)
        mp_reg = get_mapping_registry(CsvMime)
        mp = mp_reg.find_or_create_mapping(MyEntityMember)
        de = mp.map_to_data_element(mb)
        prx = DataElementAttributeProxy(de)
        self.assert_equal(prx.id, 0)
        self.assert_equal(prx.text, 'TEXT')
        self.assert_equal(prx.number, 1)
        self.assert_is_not_none(prx.parent)
        self.assert_is_none(prx.children)

    def test_map_to_data_element_with_collection(self):
        entity = create_entity()
        mb = MyEntityMember.create_from_entity(entity)
        mp_reg = get_mapping_registry(CsvMime)
        mp = mp_reg.find_or_create_mapping(MyEntityMember)
        mp1 = mp.clone(
            mapping_options={('children',):{IGNORE_ON_WRITE_OPTION:False,
                                            WRITE_AS_LINK_OPTION:False},
                             ('children', 'children'):
                                        {IGNORE_ON_WRITE_OPTION:False}
                             })
        de = mp1.map_to_data_element(mb)
        prx = DataElementAttributeProxy(de)
        self.assert_true(len(prx.children), 1)
        self.assert_true(len(prx.children[0].children), 1)
