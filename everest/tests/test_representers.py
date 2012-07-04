"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 2, 2012.
"""
from collections import OrderedDict
from everest.mime import AtomMime
from everest.mime import CsvMime
from everest.mime import XmlMime
from everest.querying.utils import get_filter_specification_factory
from everest.querying.utils import get_order_specification_factory
from everest.representers.attributes import MappedAttribute
from everest.representers.base import data_element_tree_to_string
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import REPR_NAME_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.csv import CsvData
from everest.representers.csv import CsvResourceRepresenter
from everest.representers.interfaces import IRepresenterRegistry
from everest.representers.urlloader import LazyAttributeLoaderProxy
from everest.representers.urlloader import LazyUrlLoader
from everest.representers.utils import as_representer
from everest.representers.xml import NAMESPACE_MAPPING_OPTION
from everest.representers.xml import XML_NAMESPACE_OPTION
from everest.representers.xml import XML_PREFIX_OPTION
from everest.representers.xml import XML_SCHEMA_OPTION
from everest.representers.xml import XML_TAG_OPTION
from everest.resources.kinds import ResourceKinds
from everest.resources.link import Link
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import new_stage_collection
from everest.testing import Pep8CompliantTestCase
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.entities import MyEntityParent
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityParent
from everest.tests.testapp_db.resources import MyEntityMember
from everest.tests.testapp_db.resources import MyEntityParentMember
from everest.tests.testapp_db.testing import create_collection
from everest.url import url_to_resource
from zope.interface import Interface # pylint: disable=E0611,F0401
import os

__docformat__ = 'reStructuredText en'
__all__ = ['AttributesTestCase',
           'AttributesTestCase',
           'CsvRepresentationTestCase',
           'LazyAttribteLoaderProxyTestCase',
           'RepresenterConfigurationTestCase',
           'RepresenterRegistryTestCase',
           'UpdateResourceFromDataTestCase',
           'XmlRepresentationTestCase',
           ]


class RepresenterRegistryTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_register_representer_class(self):
        rpr_reg = self.config.get_registered_utility(IRepresenterRegistry)
        self.assert_raises(ValueError, rpr_reg.register_representer_class,
                           CsvResourceRepresenter)

    def test_register_representer(self):
        class MyMime(object):
            mime_string = 'application/mymime'
            file_extension = '.mymime'
        rpr_reg = self.config.get_registered_utility(IRepresenterRegistry)
        with self.assert_raises(ValueError) as cm:
            rpr_reg.register(MyEntity, CsvMime)
        exc_msg = 'Representers can only be registered for resource classes'
        with self.assert_raises(ValueError) as cm:
            rpr_reg.register(MyEntityMember, MyMime)
        exc_msg = 'No representer class has been registered for content type'
        self.assert_true(cm.exception.message.startswith(exc_msg))

    def test_autocreate_mapping(self):
        coll = create_collection()
        # This registers a representer (factory) and creates a mapping for
        # the collection.
        coll_rpr = as_representer(coll, CsvMime)
        mb = iter(coll).next()
        # This auto-creates a mapping for the member.
        coll_rpr.data_from_resource(mb)
        rpr_reg = self.config.get_registered_utility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(CsvMime)
        mp_before = mp_reg.find_mapping(type(mb))
        # This registers a representer (factory) for the member and finds
        # the previously created mapping for the member.
        as_representer(mb, CsvMime)
        mp_after = mp_reg.find_mapping(type(mb))
        self.assert_true(mp_before is mp_after)


class AttributesTestCase(Pep8CompliantTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_defaults(self):
        rc_attr = MyEntityMember.get_attributes()['number']
        mp_attr = MappedAttribute(rc_attr)
        self.assert_equal(mp_attr.repr_name, rc_attr.name)
        self.assert_raises(AttributeError, getattr, mp_attr, 'foo')
        self.assert_true(str(mp_attr).startswith(mp_attr.__class__.__name__))

    def test_ignore(self):
        rc_attr = MyEntityMember.get_attributes()['number']
        mp_attr = MappedAttribute(rc_attr,
                                  options={IGNORE_OPTION:False})
        self.assert_true(mp_attr.ignore_on_read is False)
        self.assert_true(mp_attr.ignore_on_write is False)

    def test_clone(self):
        rc_attr = MyEntityMember.get_attributes()['number']
        mp_attr = MappedAttribute(rc_attr)
        mp_attr_clone = mp_attr.clone()
        self.assert_equal(mp_attr.options, mp_attr_clone.options)
        self.assert_equal(mp_attr.name, mp_attr_clone.name)
        self.assert_equal(mp_attr.kind, mp_attr_clone.kind)
        self.assert_equal(mp_attr.value_type, mp_attr_clone.value_type)
        self.assert_equal(mp_attr.entity_name, mp_attr_clone.entity_name)
        self.assert_equal(mp_attr.cardinality, mp_attr_clone.cardinality)


class LazyAttributeLoaderProxyTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_lazy_loading_cornercases(self):
        # Passing no _loader map to constructor raises ValueError.
        self.assert_raises(LazyAttributeLoaderProxy)
        # Passing non-dictionary as _loader_map to constructor raises error.
        self.assert_raises(ValueError, LazyAttributeLoaderProxy,
                           _loader_map=['foo'])
        # Passing empty dictionary as _loader_map to constructor raises error.
        self.assert_raises(ValueError, LazyAttributeLoaderProxy,
                           _loader_map={})
        # No dynamic attribute - create "normal" entity.
        my_entity = LazyAttributeLoaderProxy.create(MyEntity,
                                                    dict(id=0))
        self.assert_false(isinstance(my_entity, LazyAttributeLoaderProxy))

    def test_lazy_loading(self):
        loader = LazyUrlLoader('http://localhost/my-entity-parents/0',
                               url_to_resource)
        my_entity = LazyAttributeLoaderProxy.create(
                                    MyEntity,
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


class TestCsvData(Pep8CompliantTestCase):
    def test_methods(self):
        csvd0 = CsvData()
        csvd1 = CsvData(OrderedDict(foo='foo', bar=1))
        csvd0.expand(csvd1)
        self.assert_equal(csvd0.fields, ['foo', 'bar'])
        self.assert_equal(csvd0.data, [['foo', 1]])
        csvd2 = CsvData(OrderedDict(foo='foo1', bar=2))
        csvd0.append(csvd2)
        self.assert_equal(csvd0.fields, ['foo', 'bar'])
        self.assert_equal(csvd0.data, [['foo', 1], ['foo1', 2]])


class CsvRepresentationTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_data_element_tree_to_string(self):
        coll = create_collection()
        rpr = as_representer(coll, CsvMime)
        attribute_options = \
                {('children',):{IGNORE_OPTION:False,
                                WRITE_AS_LINK_OPTION:False},
                 ('children', 'children'):{IGNORE_OPTION:False,
                                           WRITE_AS_LINK_OPTION:True}
                 }
        rpr.configure(attribute_options=attribute_options)
        data_el = rpr.data_from_resource(coll)
        rpr_str = data_element_tree_to_string(data_el)
        self.assert_true(rpr_str.startswith(data_el.__class__.__name__))
        self.assert_true(rpr_str.endswith(']'))

    def test_csv_with_defaults(self):
        coll = create_collection()
        rpr = as_representer(coll, CsvMime)
        rpr_str = rpr.to_string(coll)
        self.assert_true(len(rpr_str) > 0)
        lines = rpr_str.split(os.linesep)
        self.assert_true(len(lines), 3)
        self.assert_equal(lines[0], '"id","parent","nested_parent","text",'
                                    '"text_rc","number","date_time",'
                                    '"parent_text"')
        self.assert_equal(lines[1][0], '0')
        self.assert_equal(lines[2][0], '1')
        row_data = lines[1].split(',')
        # By default, members are represented as links.
        self.assert_not_equal(row_data[1].find('my-entity-parents/0/'), -1)
        # By default, collections are not processed.
        self.assert_equal(row_data[-1], '"TEXT"')

    def test_csv_with_collection_link(self):
        coll = create_collection()
        rpr = as_representer(coll, CsvMime)
        attribute_options = {('children',):{IGNORE_OPTION:False,
                                            WRITE_AS_LINK_OPTION:True}}
        rpr.configure(attribute_options=attribute_options)
        data = rpr.data_from_resource(coll)
        rpr_str = rpr.representation_from_data(data)
        lines = rpr_str.split(os.linesep)
        row_data = lines[1].split(',')
        # Now, the collection should be a URL.
        self.assert_not_equal(row_data[3].find('my-entities/0/children/'), -1)
        # Reload from URLs.
        rpr.configure(attribute_options=attribute_options)
        reloaded_coll = rpr.resource_from_data(data)
        self.assert_equal(iter(reloaded_coll).next().id,
                          iter(coll).next().id)
        # Reloading collections lazily from URLs is not supported
        self.assert_raises(NotImplementedError,
                           rpr.resource_from_data, data,
                           resolve_urls=False)

    def test_csv_with_member_expanded(self):
        coll = create_collection()
        rpr = as_representer(coll, CsvMime)
        attribute_options = {('parent',):{WRITE_AS_LINK_OPTION:False}}
        rpr.configure(attribute_options=attribute_options)
        data = rpr.data_from_resource(coll)
        rpr_str = rpr.representation_from_data(data)
        lines = rpr_str.split(os.linesep)
        self.assert_equal(lines[0], '"id","parent.id","parent.text",'
                                    '"parent.text_rc","nested_parent","text",'
                                    '"text_rc","number","date_time",'
                                    '"parent_text"')
        row_data = lines[1].split(',')
        # Second field should be the "parent.id" and contain '0'.
        self.assert_equal(row_data[1], '0')

    def test_csv_with_collection_expanded(self):
        coll = create_collection()
        rpr = as_representer(coll, CsvMime)
        attribute_options = {('children',):{IGNORE_OPTION:False,
                                          WRITE_AS_LINK_OPTION:False}}
        rpr.configure(attribute_options=attribute_options)
        data = rpr.data_from_resource(coll)
        rpr_str = rpr.representation_from_data(data)
        lines = rpr_str.split(os.linesep)
        self.assert_equal(lines[0], '"id","parent","nested_parent",'
                                    '"children.id","children.parent",'
                                    '"children.text","children.text_rc",'
                                    '"text","text_rc","number","date_time",'
                                    '"parent_text"')
        row_data = lines[1].split(',')
        # Fourth field should now be "children.id" and contain '0'.
        self.assert_equal(row_data[3], '0')
        # Fifth field should be "children.parent" and contain a link.
        self.assert_not_equal(row_data[4].find('my-entities/0/'), -1)
        # Reload from data, ignoring the parent.
        attribute_options = {('parent',):{IGNORE_OPTION:True, },
                             ('nested_parent',):{IGNORE_OPTION:True, },
                             ('parent_text',):{IGNORE_OPTION:True, }}
        rpr.configure(attribute_options=attribute_options)
        loaded_coll = rpr.resource_from_data(data)
        self.assert_true(iter(loaded_coll).next().parent is None)

    def test_csv_with_two_collections_expanded(self):
        coll = create_collection()
        rpr = as_representer(coll, CsvMime)
        attribute_options = \
            {('children',):{IGNORE_OPTION:False,
                            WRITE_AS_LINK_OPTION:False},
             ('children', 'children'):{IGNORE_OPTION:False,
                                       WRITE_AS_LINK_OPTION:False},
             ('children', 'no_backref_children'):{IGNORE_OPTION:False,
                                                  WRITE_AS_LINK_OPTION:False},
             }
        rpr.configure(attribute_options=attribute_options)
        data = rpr.data_from_resource(coll)
        rpr_str = rpr.representation_from_data(data)
        lines = rpr_str.split(os.linesep)
        row_data = lines[1].split(',')
        # Sixth field should be "children.children.id".
        self.assert_equal(row_data[5], '0')

    def test_csv_unicode_repr_name(self):
        coll = create_collection()
        rpr = as_representer(coll, CsvMime)
        attribute_options = \
            {('children',):{IGNORE_OPTION:True, },
             ('parent',):{IGNORE_OPTION:True, },
             ('nested_parent',):{IGNORE_OPTION:True, },
             ('parent_text',):{IGNORE_OPTION:True, },
             ('text',):{REPR_NAME_OPTION:u'custom_text'}
             }
        rpr.configure(attribute_options=attribute_options)
        data = rpr.data_from_resource(coll)
        rpr_str = rpr.representation_from_data(data)
        lines = rpr_str.split(os.linesep)
        self.assert_equal(lines[0],
                          '"id","custom_text","text_rc","number","date_time"')

    def test_csv_data_from_representation(self):
        rc = object.__new__(get_collection_class(IMyEntity))
        rpr = CsvResourceRepresenter.create_from_resource(rc)
        csv_invalid_field = '"id","text","number","foo"\n0,"abc",0,"xyz"'
        with self.assert_raises(ValueError) as cm:
            rpr.data_from_representation(csv_invalid_field)
        self.assert_true(cm.exception.message.startswith('Invalid field'))
        csv_invalid_row_length = '"id","text","number"\n0,"abc",0,"xyz"'
        with self.assert_raises(ValueError) as cm:
            rpr.data_from_representation(csv_invalid_row_length)
        self.assert_true(
                    cm.exception.message.startswith('Invalid row length'))


class XmlRepresentationTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_rpr.zcml'

    def test_xml_with_defaults(self):
        coll = create_collection()
        rpr = as_representer(coll, XmlMime)
        rpr_str = rpr.to_string(coll)
        self.assert_not_equal(rpr_str.find('<ent:myentityparent id="0">'), -1)

    def test_xml_roundtrip(self):
        coll = create_collection()
        rpr = as_representer(coll, XmlMime)
        attribute_options = \
                {('nested_parent',):{IGNORE_OPTION:True},
                 ('text_rc',):{IGNORE_OPTION:True},
                 ('parent_text',):{IGNORE_OPTION:True},
                 ('children',):{IGNORE_OPTION:False,
                                WRITE_AS_LINK_OPTION:True},
                 }
        rpr.configure(attribute_options=attribute_options)
        data = rpr.data_from_resource(coll)
        self.assert_equal(len(data), 2)
        rpr_str = rpr.representation_from_data(data)
        reloaded_coll = rpr.from_string(rpr_str)
        self.assert_equal(len(reloaded_coll), 2)

    def test_id_attr(self):
        mp = self.__get_member_mapping_and_representer()[0]
        id_attr = mp.get_attribute_map()['id']
        de = mp.data_element_class.create()
        self.assert_true(de.get_mapped_terminal(id_attr) is None)

    def test_terminal_attr(self):
        coll = create_collection()
        mb = iter(coll).next()
        mp = self.__get_member_mapping_and_representer()[0]
        text_attr = mp.get_attribute_map()['text']
        de = mp.map_to_data_element(mb)
        self.assert_equal(de.get_mapped_terminal(text_attr), mb.text)
        mb.text = None
        de1 = mp.map_to_data_element(mb)
        self.assert_true(de1.get_mapped_terminal(text_attr) is None)

    def test_data(self):
        coll = create_collection()
        mb = iter(coll).next()
        mp = self.__get_member_mapping_and_representer()[0]
        de = mp.map_to_data_element(mb)
        self.assert_equal(de.data.keys(),
                          ['text', 'date_time', 'myentityparent', 'number'])

    def test_create(self):
        mp = self.__get_collection_mapping_and_representer()[0]
        xml_tag = mp.configuration.get_option(XML_TAG_OPTION)
        xml_ns = mp.configuration.get_option(XML_NAMESPACE_OPTION)
        de = mp.data_element_class.create()
        self.assert_equal(de.tag, '{%s}%s' % (xml_ns, xml_tag))
        self.assert_equal(de.nsmap[None], xml_ns)

    def test_create_no_namespace(self):
        mp = self.__get_collection_mapping_and_representer()[0]
        xml_tag = mp.configuration.get_option(XML_TAG_OPTION)
        mp.configuration.set_option(XML_NAMESPACE_OPTION, None)
        de = mp.data_element_class.create()
        self.assert_equal(de.tag, xml_tag)

    def test_create_with_attr_namespace(self):
        coll = create_collection()
        mb = iter(coll).next()
        ns = 'foo'
        mp = self.__get_member_mapping_and_representer()[0]
        mp.configuration.set_attribute_option(('parent',),
                                            NAMESPACE_MAPPING_OPTION, ns)
        mp.configuration.set_attribute_option(('parent',),
                                            WRITE_AS_LINK_OPTION, False)
        attr = mp.get_attribute_map()['parent']
        self.assert_equal(attr.namespace, ns)
        de = mp.map_to_data_element(mb)
        parent_de = de.get_mapped_nested(attr)
        self.assert_true(parent_de.tag.startswith('{%s}' % ns))

    def test_create_with_attr_no_namespace(self):
        coll = create_collection()
        mb = iter(coll).next()
        ns = None
        mp = self.__get_member_mapping_and_representer()[0]
        parent_mp = mp.mapping_registry.find_mapping(MyEntityParentMember)
        parent_mp.configuration.set_option(XML_NAMESPACE_OPTION, ns)
        mp.configuration.set_attribute_option(('parent',),
                                              WRITE_AS_LINK_OPTION, False)
        # This is a hack: the parent's text attribute would cause objectify
        # to complain that the "text" attribute is not writable (because the
        # test strips its usual namespace), so we ignore it alltogether.
        mp.configuration.set_attribute_option(('parent', 'text',),
                                              IGNORE_OPTION, True)
        attr = mp.get_attribute_map()['parent']
        self.assert_equal(attr.namespace, ns)
        de = mp.map_to_data_element(mb)
        self.assert_equal(de.data.keys(),
                          ['text', 'date_time', 'myentityparent', 'number'])
        parent_de = de.get_mapped_nested(attr)
        self.assert_equal(parent_de.tag.find('{'), -1)

    def test_create_no_tag_raises_error(self):
        mp = self.__get_collection_mapping_and_representer()[0]
        mp.configuration.set_option(XML_TAG_OPTION, None)
        self.assert_raises(ValueError, mp.data_element_class.create)

    def test_create_link(self):
        coll = create_collection()
        rpr_reg = self.config.get_registered_utility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(XmlMime)
        mp = mp_reg.find_mapping(Link)
        de = mp.data_element_class.create_from_resource(coll)
        link_el = de.iterchildren().next()
        self.assert_equal(link_el.get_kind(), ResourceKinds.COLLECTION)
        self.assert_not_equal(link_el.get_relation().find('myentity'), -1)
        self.assert_true(link_el.get_title().startswith('Collection of'))
        self.assert_true(link_el.get_id() is None)

    def test_create_link_from_non_resource_raises_error(self):
        non_rc = NonResource()
        rpr_reg = self.config.get_registered_utility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(XmlMime)
        mp = mp_reg.find_mapping(Link)
        self.assert_raises(ValueError,
                           mp.data_element_class.create_from_resource,
                           non_rc)

    def test_invalid_xml(self):
        coll = object.__new__(get_collection_class(IMyEntity))
        rpr = as_representer(coll, XmlMime)
        with self.assert_raises(SyntaxError) as cm:
            rpr.from_string('<?xml version="1.0" encoding="UTF-8"?><murks/>')
        exc_msg = 'Could not parse XML document for schema'
        self.assert_not_equal(cm.exception.message.find(exc_msg), -1)

    def test_no_xml_string_as_schema(self):
        mp, rpr = self.__get_collection_mapping_and_representer()
        mp.configuration.set_option(XML_SCHEMA_OPTION,
                                    'everest:tests/testapp_db/NoXml.xsd')
        with self.assert_raises(SyntaxError) as cm:
            rpr.from_string('<?xml version="1.0" encoding="UTF-8"?>')
        exc_msg = 'Could not parse XML schema'
        self.assert_not_equal(cm.exception.message.find(exc_msg), -1)

    def test_no_schema_xml_string_as_schema(self):
        mp, rpr = self.__get_collection_mapping_and_representer()
        mp.configuration.set_option(XML_SCHEMA_OPTION,
                                    'everest:tests/testapp_db/NoSchema.xsd')
        with self.assert_raises(SyntaxError) as cm:
            rpr.from_string('<?xml version="1.0" encoding="UTF-8"?>')
        exc_msg = 'Invalid XML schema'
        self.assert_not_equal(cm.exception.message.find(exc_msg), -1)

    def __get_collection_mapping_and_representer(self):
        rc_type = get_collection_class(IMyEntity)
        return self.__get_mapping_and_representer(rc_type)

    def __get_member_mapping_and_representer(self):
        rc_type = get_member_class(IMyEntity)
        return self.__get_mapping_and_representer(rc_type)

    def __get_mapping_and_representer(self, rc_type):
        rc = object.__new__(rc_type)
        rpr = as_representer(rc, XmlMime)
        mp = rpr._mapping # accessing protected pylint: disable=W0212
        return mp, rpr


class AtomRepresentationTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_rpr.zcml'

    def test_atom_collection(self):
        def _test(rc):
            rpr = as_representer(rc, AtomMime)
            rpr_str = rpr.to_string(rc)
            self.assert_not_equal(
              rpr_str.find('<feed xmlns:ent="http://xml.test.org/tests"'), -1)
        coll = create_collection()
        _test(coll)
        coll.slice = slice(0, 1)
        filter_spec_fac = get_filter_specification_factory()
        filter_spec = filter_spec_fac.create_equal_to('id', 0)
        coll.filter = filter_spec
        order_spec_fac = get_order_specification_factory()
        order_spec = order_spec_fac.create_ascending('id')
        coll.order = order_spec
        _test(coll)

    def test_atom_member(self):
        mb = iter(create_collection()).next()
        rpr = as_representer(mb, AtomMime)
        rpr_str = rpr.to_string(mb)
        self.assert_not_equal(
            rpr_str.find('<entry xmlns:ent="http://xml.test.org/tests"'), -1)


class RepresenterConfigurationTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_rpr.zcml'

    def test_configure_rpr_with_zcml(self):
        coll = create_collection()
        rpr = as_representer(coll, CsvMime)
        rpr_str = rpr.to_string(coll)
        lines = rpr_str.split(os.linesep)
        chld_field_idx = lines[0].split(',').index('"children"')
        row_data = lines[1].split(',')
        # Now, the collection should be a link.
        self.assert_not_equal(
                row_data[chld_field_idx].find('my-entities/0/children/'), -1)

    def test_configure_existing(self):
        foo_namespace = 'http://bogus.org/foo'
        foo_prefix = 'foo'
        my_options = {XML_NAMESPACE_OPTION:foo_namespace,
                      XML_PREFIX_OPTION:foo_prefix}
        my_attribute_options = {('parent',):{IGNORE_OPTION:True}, }
        self.config.add_resource_representer(
                                    MyEntityMember, XmlMime,
                                    options=my_options,
                                    attribute_options=my_attribute_options)
        rpr_reg = self.config.get_registered_utility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(XmlMime)
        mp = mp_reg.find_mapping(MyEntityMember)
        self.assert_equal(mp.configuration.get_option(XML_NAMESPACE_OPTION),
                          foo_namespace)
        self.assert_equal(
                    mp.configuration.get_attribute_option(('parent',),
                                                          IGNORE_OPTION),
                    True)
        #
        self.assert_raises(ValueError, mp.configuration.set_option,
                           'nonsense', True)
        self.assert_raises(ValueError, mp.configuration.set_attribute_option,
                           ('parent',), 'nonsense', True)

    def test_configure_derived(self):
        self.config.add_resource(IDerived, DerivedMyEntityMember,
                                 DerivedMyEntity,
                                 collection_root_name='my-derived-entities',
                                 expose=False)
        self.config.add_resource_representer(DerivedMyEntityMember, XmlMime)
        rpr_reg = self.config.get_registered_utility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(XmlMime)
        mp = mp_reg.find_mapping(DerivedMyEntityMember)
        self.assert_true(mp.data_element_class.mapping is mp)
        self.assert_equal(mp.configuration.get_option(XML_TAG_OPTION),
                          'myentity')

    def test_configure_derived_with_options(self):
        self.config.add_resource(IDerived, DerivedMyEntityMember,
                                 DerivedMyEntity,
                                 collection_root_name='my-derived-entities',
                                 expose=False)
        foo_namespace = 'http://bogus.org/foo'
        bogus_prefix = 'foo'
        my_options = {XML_NAMESPACE_OPTION:foo_namespace,
                      XML_PREFIX_OPTION:bogus_prefix}
        self.config.add_resource_representer(DerivedMyEntityMember, XmlMime,
                                             options=my_options)
        rpr_reg = self.config.get_registered_utility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(XmlMime)
        mp = mp_reg.find_mapping(DerivedMyEntityMember)
        self.assert_true(mp.data_element_class.mapping is mp)
        self.assert_equal(mp.configuration.get_option(XML_NAMESPACE_OPTION),
                          foo_namespace)
        self.assert_equal(mp.configuration.get_option(XML_PREFIX_OPTION),
                          bogus_prefix)
        orig_mp = mp_reg.find_mapping(MyEntityMember)
        self.assert_false(orig_mp is mp)
        self.assert_true(orig_mp.data_element_class.mapping is orig_mp)
        self.assert_not_equal(
                    orig_mp.configuration.get_option(XML_NAMESPACE_OPTION),
                    foo_namespace)
        self.assert_not_equal(
                    orig_mp.configuration.get_option(XML_PREFIX_OPTION),
                    bogus_prefix)


class UpdateResourceFromDataTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_update_collection_from_data_with_id_raises_error(self):
        coll = create_collection()
        rpr = as_representer(coll, CsvMime)
        upd_coll = new_stage_collection(IMyEntity)
        ent = MyEntity(id=2)
        upd_coll.create_member(ent)
        de = rpr.data_from_resource(upd_coll)
        with self.assert_raises(ValueError) as cm:
            coll.update_from_data(de)
        exc_msg = 'New member data should not provide an ID attribute.'
        self.assert_equal(cm.exception.message, exc_msg)

    def test_update_nested_member_from_data(self):
        # Set up member that does not have a parent.
        ent = MyEntity(id=1)
        mb = MyEntityMember.create_from_entity(ent)
        # Set up second member with same ID that does have a parent.
        parent = MyEntityParent(id=0)
        upd_ent = MyEntity(id=1, parent=parent)
        upd_mb = MyEntityMember.create_from_entity(upd_ent)
        rpr = as_representer(mb, CsvMime)
        attribute_options = {('parent',):{WRITE_AS_LINK_OPTION:False}, }
        rpr.configure(attribute_options=attribute_options)
        de = rpr.data_from_resource(upd_mb)
        mb.update_from_data(de)
        self.assert_equal(mb.parent.id, parent.id)


# pylint: disable=W0232
class IDerived(Interface):
    pass
# pylint: enable=W0232


class DerivedMyEntity(MyEntity):
    pass


class DerivedMyEntityMember(MyEntityMember):
    pass


class NonResource(object):
    pass
