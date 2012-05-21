"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 2, 2012.
"""
from everest.mime import AtomMime
from everest.mime import CsvMime
from everest.mime import XmlMime
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.urlloader import LazyAttributeLoaderProxy
from everest.representers.urlloader import LazyUrlLoader
from everest.representers.utils import as_representer
from everest.resources.utils import get_root_collection
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.entities import MyEntityParent
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityParent
from everest.tests.testapp_db.resources import MyEntityParentMember
from everest.tests.testapp_db.testing import create_entity
from everest.url import url_to_resource
import os

__docformat__ = 'reStructuredText en'
__all__ = ['CsvRepresentationTestCase',
           'LazyAttribteLoaderProxyTestCase',
           'RepresenterConfigurationTestCase',
           ]


def _make_collection():
    my_entity0 = create_entity(entity_id=0)
    my_entity1 = create_entity(entity_id=1)
    coll = get_root_collection(IMyEntity)
    coll.create_member(my_entity0)
    coll.create_member(my_entity1)
    return coll


class LazyAttribteLoaderProxyTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_lazy_loading(self):
        loader = LazyUrlLoader('http://localhost/my-entity-parents/0',
                               url_to_resource)
        my_entity = LazyAttributeLoaderProxy.create(MyEntity,
                                                    dict(id=0, parent=loader))
        self.assert_true(isinstance(my_entity, LazyAttributeLoaderProxy))
        coll = get_root_collection(IMyEntity)
        mb = coll.create_member(my_entity)
        del my_entity
        # When the dynamically loaded parent is not found, the parent attribute
        # will be None; once it is in the root collection, resolving works.
        self.assert_is_none(mb.parent)
        my_parent = MyEntityParent(id=0)
        coll = get_root_collection(IMyEntityParent)
        coll.create_member(my_parent)
        self.assert_true(isinstance(mb.parent, MyEntityParentMember))
        self.assert_true(isinstance(mb.parent.get_entity(),
                                    MyEntityParent))
        # The entity class reverts back to MyEntity once loading completed
        # successfully.
        self.assert_false(isinstance(mb.parent.get_entity(),
                                     LazyAttributeLoaderProxy))


class CsvRepresentationTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_csv_with_defaults(self):
        coll = _make_collection()
        rpr = as_representer(coll, CsvMime)
        rpr_str = rpr.to_string(coll)
        self.assert_true(len(rpr_str) > 0)
        lines = rpr_str.split(os.linesep)
        self.assert_true(len(lines), 3)
        self.assert_equal(lines[0], '"id","parent","nested_parent","children"'
                                    ',"text","text_rc","number","date_time",'
                                    '"parent_text"')
        self.assert_equal(lines[1][0], '0')
        self.assert_equal(lines[2][0], '1')
        row_data = lines[1].split(',')
        self.assert_not_equal(row_data[1].find('my-entity-parents/0/'), -1)
        # By default, collections are not processed.
        self.assert_equal(row_data[3], '""')

    def test_csv_with_collection_link(self):
        coll = _make_collection()
        rpr = as_representer(coll, CsvMime)
        mapping_options = {('children',):{IGNORE_OPTION:False,
                                          WRITE_AS_LINK_OPTION:True}}
        data = rpr.data_from_resource(coll, mapping_options=mapping_options)
        rpr_str = rpr.representation_from_data(data)
        lines = rpr_str.split(os.linesep)
        row_data = lines[1].split(',')
        # Now, the collection should be a link.
        self.assert_not_equal(row_data[3].find('my-entities/0/children/'), -1)

    def test_csv_with_collection_expanded(self):
        coll = _make_collection()
        rpr = as_representer(coll, CsvMime)
        mapping_options = {('children',):{IGNORE_OPTION:False,
                                          WRITE_AS_LINK_OPTION:False}}
        data = rpr.data_from_resource(coll, mapping_options=mapping_options)
        rpr_str = rpr.representation_from_data(data)
        lines = rpr_str.split(os.linesep)
        self.assert_equal(lines[0], '"id","parent","nested_parent",'
                                    '"children.id","children.children",'
                                    '"children.no_backref_children",'
                                    '"children.text","children.text_rc",'
                                    '"text","text_rc","number","date_time",'
                                    '"parent_text"')
        row_data = lines[1].split(',')
        # Third field should now be "children.id" and contains 0.
        self.assert_equal(row_data[3], '0')


class XmlRepresentationTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_rpr.zcml'

    def test_xml_with_defaults(self):
        coll = _make_collection()
        rpr = as_representer(coll, XmlMime)
        rpr_str = rpr.to_string(coll)
        self.assert_not_equal(rpr_str.find('<ent:myentityparent id="0">'), -1)

    def test_xml_roundtrip(self):
        coll = _make_collection()
        rpr = as_representer(coll, XmlMime)
        mapping_options = {('nested_parent',):{IGNORE_OPTION:True},
                           ('text_rc',):{IGNORE_OPTION:True},
                           ('parent_text',):{IGNORE_OPTION:True},
                           ('children',):{IGNORE_OPTION:False,
                                          WRITE_AS_LINK_OPTION:True},
                           }
        data = rpr.data_from_resource(coll, mapping_options=mapping_options)
        rpr_str = rpr.representation_from_data(data)
        reloaded_coll = rpr.from_string(rpr_str)
        self.assert_equal(len(reloaded_coll), 2)


class AtomRepresentationTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_rpr.zcml'

    def test_atom_with_defaults(self):
        coll = _make_collection()
        rpr = as_representer(coll, AtomMime)
        rpr_str = rpr.to_string(coll)
        self.assert_not_equal(
            rpr_str.find('<feed xmlns:ent="http://test.org/myentity"'), -1)


class RepresenterConfigurationTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_rpr.zcml'

    def test_configure_rpr_with_zcml(self):
        coll = _make_collection()
        rpr = as_representer(coll, CsvMime)
        rpr_str = rpr.to_string(coll)
        lines = rpr_str.split(os.linesep)
        chld_field_idx = lines[0].split(',').index('"children"')
        row_data = lines[1].split(',')
        # Now, the collection should be a link.
        self.assert_not_equal(
                row_data[chld_field_idx].find('my-entities/0/children/'), -1)
