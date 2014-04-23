"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 2, 2012.
"""
from collections import OrderedDict
import os

from pyramid.compat import binary_type
from pyramid.compat import bytes_
from pyramid.compat import text_type
import pytest

from everest.constants import RESOURCE_KINDS
from everest.entities.attributes import get_domain_class_attribute
from everest.mime import AtomMime
from everest.mime import CsvMime
from everest.mime import JsonMime
from everest.mime import XmlMime
from everest.querying.utils import get_filter_specification_factory
from everest.querying.utils import get_order_specification_factory
from everest.representers.attributes import MappedAttribute
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import REPR_NAME_OPTION
from everest.representers.config import RepresenterConfiguration
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.csv import CsvData
from everest.representers.csv import CsvResourceRepresenter
from everest.representers.dataelements import CollectionDataElement
from everest.representers.dataelements import MemberDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.representers.interfaces import IRepresenterRegistry
from everest.representers.json import JsonDataTreeTraverser
from everest.representers.traversal import \
                        DataElementBuilderRepresentationDataVisitor
from everest.representers.utils import as_representer
from everest.representers.xml import NAMESPACE_MAPPING_OPTION
from everest.representers.xml import XML_NAMESPACE_OPTION
from everest.representers.xml import XML_PREFIX_OPTION
from everest.representers.xml import XML_SCHEMA_OPTION
from everest.representers.xml import XML_TAG_OPTION
from everest.resources.attributes import get_resource_class_attribute
from everest.resources.link import Link
from everest.resources.staging import create_staging_collection
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.resources import MyEntityMember
from everest.tests.complete_app.resources import MyEntityParentMember
from zope.interface import Interface # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['TestAtomRepresenter',
           'TestAttributes',
           'TestCsvData',
           'TestCsvRepresenter',
           'TestJsonRepresenter',
           'TestRepresenterConfiguration',
           'TestRepresenterConfigurationNoTypes',
           'TestRepresenterConfigurationOldStyleAttrs',
           'TestRepresenterRegistry',
           'TestUpdateResourceFromData',
           'TestXmlRepresenter',
           ]


class TestRepresenterRegistry(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_register_representer_class(self, configurator):
        configurator.begin()
        try:
            rpr_reg = configurator.get_registered_utility(IRepresenterRegistry)
            with pytest.raises(ValueError):
                rpr_reg.register_representer_class(CsvResourceRepresenter)
        finally:
            configurator.end()

    def test_register_representer(self, configurator):
        class MyMime(object):
            mime_string = 'application/mymime'
            file_extension = '.mymime'
        configurator.begin()
        try:
            rpr_reg = configurator.get_registered_utility(IRepresenterRegistry)
            with pytest.raises(ValueError) as cm:
                rpr_reg.register(MyEntity, CsvMime)
            exc_msg = 'Representers can only be registered for resource classes'
            assert str(cm.value).startswith(exc_msg)
            with pytest.raises(ValueError) as cm:
                rpr_reg.register(MyEntityMember, MyMime)
            exc_msg = 'No representer class has been registered for content type'
            assert str(cm.value).startswith(exc_msg)
        finally:
            configurator.end()

    def test_autocreate_mapping(self, collection, configurator):
        # This registers a representer (factory) and creates a mapping for
        # the collection.
        coll_rpr = as_representer(collection, CsvMime)
        mb = next(iter(collection))
        # This auto-creates a mapping for the member.
        coll_rpr.resource_to_data(mb)
        rpr_reg = configurator.get_registered_utility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(CsvMime)
        mp_before = mp_reg.find_mapping(type(mb))
        # This registers a representer (factory) for the member and finds
        # the previously created mapping for the member.
        as_representer(mb, CsvMime)
        mp_after = mp_reg.find_mapping(type(mb))
        assert mp_before is mp_after


class TestAttributes(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_defaults(self):
        rc_attr = get_resource_class_attribute(MyEntityMember, 'number')
        mp_attr = MappedAttribute(rc_attr)
        assert mp_attr.repr_name == rc_attr.entity_attr
        with pytest.raises(AttributeError):
            getattr(mp_attr, 'foo')
        assert str(mp_attr).startswith(mp_attr.attr_type.__name__)

    def test_ignore(self):
        rc_attr = get_resource_class_attribute(MyEntityMember, 'number')
        mp_attr = MappedAttribute(rc_attr,
                                  options={IGNORE_OPTION:False})
        assert getattr(mp_attr, IGNORE_OPTION) is False

    def test_clone(self):
        rc_attr = get_resource_class_attribute(MyEntityMember, 'number')
        mp_attr = MappedAttribute(rc_attr)
        mp_attr_clone = mp_attr.clone()
        assert mp_attr.options == mp_attr_clone.options
        assert mp_attr.name == mp_attr_clone.name
        assert mp_attr.kind == mp_attr_clone.kind
        assert mp_attr.value_type == mp_attr_clone.value_type
        assert mp_attr.entity_name == mp_attr_clone.entity_name
        assert mp_attr.cardinality == mp_attr_clone.cardinality


class TestCsvData(object):
    def test_methods(self):
        csvd0 = CsvData()
        od1 = OrderedDict()
        od1['foo'] = 'foo'
        od1['bar'] = 1
        csvd1 = CsvData(od1)
        csvd0.expand(csvd1)
        csvd0.fields == ['foo', 'bar'] # pylint: disable=W0104
        csvd0.data == [['foo', 1]] # pylint: disable=W0104
        od2 = OrderedDict()
        od2['foo'] = 'foo1'
        od2['bar'] = 2
        csvd2 = CsvData(od2)
        csvd0.append(csvd2)
        assert csvd0.fields == ['foo', 'bar']
        assert csvd0.data == [['foo', 1], ['foo1', 2]]


class _TestRepresenter(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_member_representer(self, member_representer, collection,
                                monkeypatch):
        mb = next(iter(collection))
        rpr_str = member_representer.to_string(mb)
        mb_reloaded = member_representer.from_string(rpr_str)
        assert mb.id == mb_reloaded.id
        # Check unicode handling.
        mb.text = u'h\xfclfe'
        bytes_val = bytes_(mb.text, encoding=member_representer.encoding)
        attr = get_domain_class_attribute(MyEntity, 'text')
        def test(member, exp_val):
            rpr_text = member_representer.to_string(member)
            assert isinstance(rpr_text, text_type)
            rpr_bytes = member_representer.to_bytes(member)
            assert isinstance(rpr_bytes, binary_type)
            mb_reloaded_str = member_representer.from_string(rpr_text)
            assert isinstance(mb_reloaded_str.text, attr.attr_type)
            assert mb_reloaded_str.text == exp_val
            mb_reloaded_bytes = member_representer.from_bytes(rpr_bytes)
            assert isinstance(mb_reloaded_bytes.text, attr.attr_type)
            assert mb_reloaded_bytes.text == exp_val
            #
            de = member_representer.resource_to_data(member)
            assert isinstance(de, MemberDataElement)
            rpr_data_bytes = member_representer.data_to_bytes(de)
            assert isinstance(rpr_data_bytes, binary_type)
        # In PY3, the attr type will be text, in PY2 bytes.
        if not issubclass(attr.attr_type, binary_type):
            monkeypatch.setattr(attr, 'attr_type', binary_type)
        test(mb, bytes_val)
        # In PY3, the attr type will be text, in PY2 bytes.
        if not issubclass(attr.attr_type, text_type):
            monkeypatch.setattr(attr, 'attr_type', text_type)
        test(mb, mb.text)

    def _test_with_defaults(self, representer, collection, check_string,
                            do_roundtrip=True):
        self._test_rpr(representer, collection, None, check_string,
                       self._check_nested_member if do_roundtrip else None)

    def _test_with_collection_link(self, representer, collection, check_string,
                                   do_roundtrip=True):
        attribute_options = {('children',):{IGNORE_OPTION:False,
                                            WRITE_AS_LINK_OPTION:True}}
        self._test_rpr(representer, collection, attribute_options,
                       check_string,
                    self._check_nested_collection if do_roundtrip else None)

    def _test_with_member_expanded(self, representer, collection,
                                   check_string, do_roundtrip=True):
        attribute_options = {('parent',):{WRITE_AS_LINK_OPTION:False}}
        self._test_rpr(representer, collection, attribute_options,
                       check_string,
                       self._check_nested_member if do_roundtrip else None)

    def _test_with_collection_expanded(self, representer, collection,
                                       check_string, do_roundtrip=True):
        attribute_options = {('children',):{IGNORE_OPTION:False,
                                            WRITE_AS_LINK_OPTION:False}}
        self._test_rpr(representer, collection, attribute_options,
                       check_string,
                    self._check_nested_collection if do_roundtrip else None)

    def _test_with_two_collections_expanded(self, representer, collection,
                                            check_string, do_roundtrip=True):
        attribute_options = \
            {('children',):{IGNORE_OPTION:False,
                            WRITE_AS_LINK_OPTION:False},
             ('children', 'children'):{IGNORE_OPTION:False,
                                       WRITE_AS_LINK_OPTION:False},
             }
        self._test_rpr(representer, collection, attribute_options,
                       check_string,
                    self._check_nested_collection if do_roundtrip else None)

    def _test_rpr(self, representer, collection, attribute_options,
                  str_checker, coll_checker):
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            rpr_str = representer.to_string(collection)
            assert len(rpr_str) > 0
            if not str_checker is None:
                str_checker(rpr_str)
            if not coll_checker is None:
                reloaded_coll = representer.from_string(rpr_str)
                assert len(reloaded_coll) == len(collection)
                coll_checker(reloaded_coll)

    def _check_id(self, collection):
        assert next(iter(collection)).id == next(iter(collection).id)

    def _check_nested_member(self, collection):
        assert next(iter(collection)).parent.id \
                        == next(iter(collection)).parent.id

    def _check_nested_collection(self, collection):
        assert next(iter(next(iter(collection)).children)).id \
                        == next(iter(next(iter(collection)).children)).id


class TestJsonRepresenter(_TestRepresenter):
    content_type = JsonMime

    def test_json_with_defaults(self, representer, collection):
        def check_string(rpr_str):
            assert rpr_str.startswith('[{') and rpr_str.endswith('}]')
        self._test_with_defaults(representer, collection, check_string)

    def test_json_with_collection_link(self, representer, collection):
        def check_string(rpr_str):
            assert rpr_str.find('my-entity-children/?q=parent') != -1
        self._test_with_collection_link(representer, collection, check_string)

    def test_json_with_member_expanded(self, representer, collection):
        def check_string(rpr_str):
            assert rpr_str.find('parent_text') != -1
        self._test_with_member_expanded(representer, collection, check_string)

    def test_json_with_two_collections_expanded(self, representer, collection):
        self._test_with_two_collections_expanded(representer, collection, None)

    def test_json_data_tree_traverser(self, configurator):
        configurator.begin()
        try:
            rpr_reg = configurator.registry.queryUtility(IRepresenterRegistry)
            mp_reg = rpr_reg.get_mapping_registry(JsonMime)
            default_mp = mp_reg.find_or_create_mapping(MyEntityMember)
            attr_opts = {('parent',):{WRITE_AS_LINK_OPTION:False}}
            mp = default_mp.clone(attribute_options=attr_opts)
            vst = DataElementBuilderRepresentationDataVisitor(mp)
            for json_data, exc_msg in ((object, 'Need dict (member),'),
                                       ({'parent':
                                            {'__jsonclass__':'http://foo.org'}},
                                        'Expected data for'),):
                trv = JsonDataTreeTraverser(json_data, mp)
                with pytest.raises(ValueError) as cm:
                    trv.run(vst)
                assert str(cm.value).startswith(exc_msg)
        finally:
            configurator.end()


class TestCsvRepresenter(_TestRepresenter):
    content_type = CsvMime

    def test_csv_with_defaults(self, representer, collection):
        def check_string(rpr_str):
            lines = rpr_str.strip().split(os.linesep)
            assert len(lines) == 3
            assert lines[0] == '"id","parent","text",' \
                               '"text_rc","number","date_time",' \
                               '"parent_text"'
            assert lines[1][0] == '0'
            assert lines[2][0] == '1'
            row_data = lines[1].split(',')
            # By default, members are represented as links.
            assert row_data[1].find('my-entity-parents/0/') != -1
            # By default, collections are not processed.
            assert row_data[-1] == '"TEXT"'
        self._test_with_defaults(representer, collection, check_string)

    def test_csv_with_collection_link(self, representer, collection):
        def check_string(rpr_str):
            lines = rpr_str.split(os.linesep)
            row_data = lines[1].split(',')
            # Now, the collection should be a URL.
            assert row_data[2].find('my-entity-children/?q=parent') != -1
        self._test_with_collection_link(representer, collection, check_string)

    def test_csv_with_member_expanded(self, representer, collection):
        def check_string(rpr_str):
            lines = rpr_str.split(os.linesep)
            assert lines[0] == '"id","parent.id","parent.text",' \
                               '"parent.text_rc","text",' \
                               '"text_rc","number","date_time",' \
                               '"parent_text"'
            row_data = lines[1].split(',')
            # Second field should be the "parent.id" and contain '0'.
            assert row_data[1] == '0'
        # Ensure unique representation names for nested attributes.
        attribute_options = {
            ('parent', 'id') : {REPR_NAME_OPTION:'parent.id'},
            ('parent', 'text') : {REPR_NAME_OPTION:'parent.text'},
            ('parent', 'text_rc') : {REPR_NAME_OPTION:'parent.text_rc'},
             }
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            self._test_with_member_expanded(representer, collection,
                                            check_string)

    def test_csv_with_collection_expanded(self, representer, collection):
        def check_string(rpr_str):
            lines = rpr_str.split(os.linesep)
            assert lines[0] == '"id","parent","children.id",' \
                               '"children.text","children.text_rc",' \
                               '"text","text_rc","number","date_time",' \
                               '"parent_text"'
            row_data = lines[1].split(',')
            # Fourth field should now be "children.id" and contain 0.
            assert row_data[2] == '0'
            # Fifth field should be "children.text" and contain "TEXT".
            assert row_data[3] == '"TEXT"'
        # Ensure unique representation names for nested attributes.
        attribute_options = {
            ('children', 'id') : {REPR_NAME_OPTION:'children.id'},
            ('children', 'parent') : {IGNORE_OPTION:True},
            ('children', 'text') : {REPR_NAME_OPTION:'children.text'},
            ('children', 'text_rc') : {REPR_NAME_OPTION:'children.text_rc'},
             }
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            self._test_with_collection_expanded(representer, collection,
                                                check_string)

    def test_csv_collection_to_data_roundtrip(self, representer, collection):
        attribute_options = {('parent',):{IGNORE_OPTION:True, },
                             ('parent_text',):{IGNORE_OPTION:True, }}
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            data_el = representer.resource_to_data(collection)
            loaded_coll = representer.resource_from_data(data_el)
            assert next(iter(loaded_coll)).parent is None

    def test_csv_member_to_data_roundtrip_in_place(self, representer,
                                                   collection):
        mb = collection['0']
        parent = mb.parent
        data_el = representer.resource_to_data(mb)
        representer.resource_from_data(data_el, resource=mb)
        assert mb.parent.get_entity() is parent.get_entity()

    def test_csv_with_two_collections_expanded(self, representer, collection):
        def check_string(rpr_str):
            lines = rpr_str.split(os.linesep)
            row_data = lines[1].split(',')
            #  field should be "children.children.id".
            assert row_data[4] == '0'
        self._test_with_two_collections_expanded(representer, collection,
                                                 check_string,
                                                 do_roundtrip=False)

    def test_csv_unicode_repr_name(self, representer, collection):
        attribute_options = \
            {('children',):{IGNORE_OPTION:True, },
             ('parent',):{IGNORE_OPTION:True, },
             ('parent_text',):{IGNORE_OPTION:True, },
             ('text',):{REPR_NAME_OPTION:u'custom_text'}
             }
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            data = representer.resource_to_data(collection)
            rpr_str = representer.data_to_string(data)
            lines = rpr_str.split(os.linesep)
            assert lines[0] == '"id","custom_text","text_rc","number","date_time"'

    def test_csv_data_from_string(self, representer):
        csv_invalid_field = '"id","text","number","foo"\n0,"abc",0,"xyz"'
        with pytest.raises(ValueError) as cm:
            representer.data_from_string(csv_invalid_field)
        assert str(cm.value).startswith('Invalid field')
        csv_invalid_row_length = '"id","text","number"\n0,"abc",0,"xyz",5'
        with pytest.raises(ValueError) as cm:
            representer.data_from_string(csv_invalid_row_length)
        assert str(cm.value).startswith('Invalid row length')
        csv_value_for_ignored_field = '"id","children"\n' \
                                      '0,"http://0.0.0.0/my-entity-parents/0"'
        with pytest.raises(ValueError) as cm:
            representer.data_from_string(csv_value_for_ignored_field)
        assert str(cm.value).startswith('Value for attribute')
        csv_invalid_link = '"id","parent"\n0,"my-entity-parents/0"'
        with pytest.raises(ValueError) as cm:
            representer.data_from_string(csv_invalid_link)
        assert str(cm.value).startswith('Value for nested attribute')

    def test_csv_with_two_collections_expanded_fails(self, representer):
        attribute_options = {
            ('children',) : {IGNORE_OPTION:False},
            ('children', 'id') : {REPR_NAME_OPTION:'children.id'},
            ('children', 'children',) : {IGNORE_OPTION:False},
            ('children', 'children', 'id') :
                            {REPR_NAME_OPTION:'children.children.id'},
             }
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            csv_two_colls_expanded = \
                    '"id","children.id","children.children.id"\n0,0,0'
            with pytest.raises(ValueError) as cm:
                representer.data_from_string(csv_two_colls_expanded)
            assert str(cm.value).startswith('All but one nested collection')

    def test_csv_with_multiple_nested_members(self, representer):
        attribute_options = {
            ('children',) : {IGNORE_OPTION:False},
            ('children', 'id') : {REPR_NAME_OPTION:'children.id'},
            }
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            csv_multiple_nested_members = '"id","children.id"\n0,0\n0,1'
            data_el = representer.data_from_string(csv_multiple_nested_members)
            assert len(data_el) == 1
            mb_el = data_el.members[0]
            assert mb_el.data['children'].members[1].data['children.id'] == 1

    def test_csv_none_attribute_value(self, representer, collection):
        ent = collection['0'].get_entity()
        ent.text = None
        def check_string(rpr_str):
            lines = rpr_str.strip().split(os.linesep)
            assert len(lines) == 3
            # Make sure the header is correct.
            assert lines[0] == '"id","parent","text",' \
                               '"text_rc","number","date_time",' \
                               '"parent_text"'
            # None value represented as the empty string.
            assert lines[1].split(',')[2] == '""'
            assert lines[2].split(',')[2] == '"too1"'
        self._test_with_defaults(representer, collection, check_string)


class TestXmlRepresenter(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_rpr.zcml'
    content_type = XmlMime

    def test_xml_with_defaults(self, representer, collection):
        rpr_str = representer.to_string(collection)
        assert rpr_str.find('<ent:myentityparent id="0">') != -1
        de = representer.resource_to_data(collection)
        assert isinstance(de, CollectionDataElement)
        rpr_data_bytes = representer.data_to_bytes(de)
        assert isinstance(rpr_data_bytes, binary_type)

    def test_xml_roundtrip(self, representer, collection):
        attribute_options = \
                {('text_rc',):{IGNORE_OPTION:True},
                 ('parent_text',):{IGNORE_OPTION:True},
                 ('children',):{IGNORE_OPTION:False,
                                WRITE_AS_LINK_OPTION:True},
                 }
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            data = representer.resource_to_data(collection)
            assert len(data) == 2
            rpr_str = representer.data_to_string(data)
            reloaded_coll = representer.from_string(rpr_str)
            assert len(reloaded_coll) == 2

    def test_id_attr(self, member_mapping):
        id_attr = member_mapping.get_attribute_map()['id']
        de = member_mapping.data_element_class.create()
        assert de.get_terminal(id_attr) is None

    def test_terminal_attr(self, collection, member_mapping):
        mb = next(iter(collection))
        text_attr = member_mapping.get_attribute_map()['text']
        de = member_mapping.map_to_data_element(mb)
        assert de.get_terminal(text_attr) == mb.text
        mb.text = None
        de1 = member_mapping.map_to_data_element(mb)
        assert de1.get_terminal(text_attr) is None

    @pytest.mark.parametrize(
                        'attribute_options,check_for_link',
                        [({('parent',):{WRITE_AS_LINK_OPTION:False}}, False),
                         ({('parent',):{WRITE_AS_LINK_OPTION:True}}, True)])
    def test_data(self, collection, representer, attribute_options,
                  check_for_link):
        mb = next(iter(collection))
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            de = representer.resource_to_data(mb)
            assert list(de.data.keys()) \
                    == ['id', 'myentityparent', 'text', 'number', 'date_time']
            assert de.get_attribute('number') == 1
            parent = de.get_attribute('myentityparent')
            with pytest.raises(AttributeError):
                dummy = de.get_attribute('foo')
            with pytest.raises(AttributeError):
                de.set_attribute('foo', 'bar')
            if not check_for_link:
                assert IMemberDataElement.providedBy(parent) # pylint:disable=E1101
            else:
                assert ILinkedDataElement.providedBy(parent) # pylint:disable=E1101

    def test_create(self, mapping):
        xml_tag = mapping.configuration.get_option(XML_TAG_OPTION)
        xml_ns = mapping.configuration.get_option(XML_NAMESPACE_OPTION)
        de = mapping.data_element_class.create()
        assert de.tag == '{%s}%s' % (xml_ns, xml_tag)
        assert de.nsmap[None] == xml_ns

    def test_create_no_namespace(self, representer, mapping):
        xml_tag = mapping.configuration.get_option(XML_TAG_OPTION)
        options = {XML_NAMESPACE_OPTION:None}
        with representer.with_updated_configuration(options=options):
            de = mapping.data_element_class.create()
            assert de.tag == xml_tag

    def test_create_with_attr_namespace(self, collection, representer,
                                        mapping):
        mb = next(iter(collection))
        ns = 'foo'
        attribute_options = {('parent',):{NAMESPACE_MAPPING_OPTION:ns,
                                          WRITE_AS_LINK_OPTION:False}}
        with representer.with_updated_configuration(attribute_options=
                                                        attribute_options):
            attr = mapping.get_attribute_map()['parent']
            assert attr.namespace == ns
            de = representer.resource_to_data(mb)
            parent_de = de.get_nested(attr)
            assert parent_de.tag.startswith('{%s}' % ns)

    def test_create_with_attr_no_namespace(self, member, new_configurator):
        new_configurator.begin()
        try:
            rpr_reg = \
                new_configurator.get_registered_utility(IRepresenterRegistry)
            mp_reg = rpr_reg.get_mapping_registry(XmlMime)
            ns = None
            options = {XML_NAMESPACE_OPTION:ns}
            mp = mp_reg.find_or_create_mapping(MyEntityParentMember)
            with mp.with_updated_configuration(options=options):
                # We need to do this so the namespace lookup is rebuilt.
                mp_reg.set_mapping(mp)
                attr = mp.get_attribute('id')
                assert attr.namespace == ns
                de = mp.map_to_data_element(member.parent)
                assert list(de.data.keys()) == ['id', 'text', 'text_rc']
                assert de.tag.find('{') == -1
        finally:
            new_configurator.end()

    def test_create_no_tag_raises_error(self, mapping):
        options = {XML_TAG_OPTION:None}
        with mapping.with_updated_configuration(options=options):
            with pytest.raises(ValueError):
                mapping.data_element_class.create()

    def test_create_link(self, collection, configurator):
        rpr_reg = configurator.get_registered_utility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(XmlMime)
        mp = mp_reg.find_mapping(Link)
        de = mp.data_element_class.create_from_resource(collection)
        link_el = next(de.iterchildren())
        assert link_el.get_kind() == RESOURCE_KINDS.COLLECTION
        assert link_el.get_relation().find('myentity') != -1
        assert link_el.get_title().startswith('Collection of')
        assert link_el.get_id() is None

    def test_create_link_from_non_resource_raises_error(self, configurator):
        configurator.begin()
        try:
            non_rc = NonResource()
            rpr_reg = configurator.get_registered_utility(IRepresenterRegistry)
            mp_reg = rpr_reg.get_mapping_registry(XmlMime)
            mp = mp_reg.find_mapping(Link)
            with pytest.raises(ValueError):
                mp.data_element_class.create_from_resource(non_rc)
        finally:
            configurator.end()

    def test_invalid_xml(self, representer):
        with pytest.raises(SyntaxError) as cm:
            representer.from_string('<murks/>')
        exc_msg = 'Could not parse XML document for schema'
        assert str(cm.value).find(exc_msg) != -1

    def test_no_xml_string_as_schema(self, representer):
        options = {XML_SCHEMA_OPTION:'everest:tests/complete_app/NoXml.xsd'}
        with representer.with_updated_configuration(options=options):
            with pytest.raises(SyntaxError) as cm:
                representer.from_string('')
            exc_msg = 'Could not parse XML schema'
            assert str(cm.value).find(exc_msg) != -1

    def test_no_schema_xml_string_as_schema(self, representer):
        options = \
            {XML_SCHEMA_OPTION:'everest:tests/complete_app/NoSchema.xsd'}
        with representer.with_updated_configuration(options=options):
            with pytest.raises(SyntaxError) as cm:
                representer.from_string('')
            exc_msg = 'Invalid XML schema'
            assert str(cm.value).find(exc_msg) != -1


class TestAtomRepresenter(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_rpr.zcml'
    content_type = AtomMime

    def test_atom_collection(self, collection, representer):
        rpr_str1 = representer.to_string(collection)
        assert rpr_str1.find('<feed xmlns:') != -1
        collection.slice = slice(0, 1)
        filter_spec_fac = get_filter_specification_factory()
        filter_spec = filter_spec_fac.create_equal_to('id', 0)
        collection.filter = filter_spec
        order_spec_fac = get_order_specification_factory()
        order_spec = order_spec_fac.create_ascending('id')
        collection.order = order_spec
        rpr_str2 = representer.to_string(collection)
        assert rpr_str2.find('<feed xmlns:') != -1

    def test_atom_member(self, collection, member_representer):
        mb = next(iter(collection))
        rpr_str = member_representer.to_string(mb)
        assert \
            rpr_str.find('<entry xmlns:ent="http://xml.test.org/tests"') != -1


class _TestRepresenterConfiguration(object):
    package_name = 'everest.tests.complete_app'
    content_type = CsvMime

    def test_configure_rpr_with_zcml(self, collection, representer):
        rpr_str = representer.to_string(collection)
        lines = rpr_str.split(os.linesep)
        fields = lines[0].split(',')
        # Parent should be inline.
        assert '"parent.id"' in fields
        chld_field_idx = fields.index('"children"')
        row_data = lines[1].split(',')
        # Collection should be a link.
        assert \
          row_data[chld_field_idx].find('my-entity-children/?q=parent') != -1


class TestRepresenterConfigurationOldStyleAttrs(
                                            _TestRepresenterConfiguration):
    config_file_name = 'configure_rpr_oldstyle_attrs.zcml'


class TestRepresenterConfigurationNoTypes(_TestRepresenterConfiguration):
    config_file_name = 'configure_rpr_no_types.zcml'


class TestRepresenterConfiguration(_TestRepresenterConfiguration):
    config_file_name = 'configure_rpr.zcml'

    def test_custom_config(self):
        class MyRepresenterConfiguration(RepresenterConfiguration):
            _default_config_options = dict(
                list(RepresenterConfiguration._default_config_options.items())
                     + [('foo', None)])
        foo_val = 1
        rpr_cnf = MyRepresenterConfiguration(
                        options=dict(foo=foo_val),
                        attribute_options=dict(foo={IGNORE_OPTION:True}))
        rpr_cnf_cp = rpr_cnf.copy()
        assert rpr_cnf.get_option('foo') == foo_val
        assert rpr_cnf_cp.get_option('foo') == foo_val
        for key in (('foo',), ['foo']):
            assert rpr_cnf.get_attribute_option(key, IGNORE_OPTION) is True
            assert rpr_cnf_cp.get_attribute_option(key, IGNORE_OPTION) is True

    def test_non_existing_attribute_fails(self, resource_repo):
        coll = resource_repo.get_collection(IMyEntity)
        ent = MyEntity(id=1)
        mb = coll.create_member(ent)
        rpr = as_representer(mb, CsvMime)
        attr_name = 'invalid'
        attribute_options = {(attr_name,):{IGNORE_OPTION:False,
                                           WRITE_AS_LINK_OPTION:True}}
        with pytest.raises(AttributeError) as cm:
            with rpr.with_updated_configuration():
                rpr.configure(attribute_options=attribute_options)
        msg = 'Trying to configure non-existing resource attribute "%s"' \
              % attr_name
        assert str(cm.value)[:len(msg)] == msg

    def test_configure_existing(self, new_configurator):
        new_configurator.begin()
        try:
            foo_namespace = 'http://bogus.org/foo'
            foo_prefix = 'foo'
            my_options = {XML_NAMESPACE_OPTION:foo_namespace,
                          XML_PREFIX_OPTION:foo_prefix}
            my_attribute_options = {('parent',):{IGNORE_OPTION:True}, }
            new_configurator.add_resource_representer(
                                        MyEntityMember, XmlMime,
                                        options=my_options,
                                        attribute_options=
                                                    my_attribute_options)
            rpr_reg = \
                new_configurator.get_registered_utility(IRepresenterRegistry)
            mp_reg = rpr_reg.get_mapping_registry(XmlMime)
            mp = mp_reg.find_mapping(MyEntityMember)
            assert mp.configuration.get_option(XML_NAMESPACE_OPTION) \
                    == foo_namespace
            assert mp.configuration.get_attribute_option(('parent',),
                                                         IGNORE_OPTION) \
                    is True
            with pytest.raises(ValueError):
                with mp.with_updated_configuration():
                    mp.configuration.set_option('nonsense', True)
            with pytest.raises(ValueError):
                with mp.with_updated_configuration():
                    mp.configuration.set_attribute_option(('parent',),
                                                          'nonsense', True)
        finally:
            new_configurator.end()

    def test_configure_derived(self, new_configurator):
        new_configurator.begin()
        try:
            new_configurator.add_resource(IDerived, DerivedMyEntityMember,
                                          DerivedMyEntity,
                                          collection_root_name=
                                                  'my-derived-entities',
                                          expose=False)
            new_configurator.add_resource_representer(DerivedMyEntityMember,
                                                      XmlMime)
            rpr_reg = \
                new_configurator.get_registered_utility(IRepresenterRegistry)
            mp_reg = rpr_reg.get_mapping_registry(XmlMime)
            mp = mp_reg.find_mapping(DerivedMyEntityMember)
            assert mp.data_element_class.mapping is mp
            assert mp.configuration.get_option(XML_TAG_OPTION) == 'myentity'
        finally:
            new_configurator.end()

    def test_configure_derived_with_options(self, new_configurator):
        new_configurator.begin()
        try:
            new_configurator.add_resource(IDerived, DerivedMyEntityMember,
                                          DerivedMyEntity,
                                          collection_root_name=
                                                    'my-derived-entities',
                                          expose=False)
            foo_namespace = 'http://bogus.org/foo'
            bogus_prefix = 'foo'
            my_options = {XML_NAMESPACE_OPTION:foo_namespace,
                          XML_PREFIX_OPTION:bogus_prefix}
            new_configurator.add_resource_representer(DerivedMyEntityMember,
                                                      XmlMime,
                                                      options=my_options)
            rpr_reg = \
                new_configurator.get_registered_utility(IRepresenterRegistry)
            mp_reg = rpr_reg.get_mapping_registry(XmlMime)
            mp = mp_reg.find_mapping(DerivedMyEntityMember)
            assert mp.data_element_class.mapping is mp
            assert mp.configuration.get_option(XML_NAMESPACE_OPTION) \
                    == foo_namespace
            assert mp.configuration.get_option(XML_PREFIX_OPTION) \
                    == bogus_prefix
            orig_mp = mp_reg.find_mapping(MyEntityMember)
            assert not orig_mp is mp
            assert orig_mp.data_element_class.mapping is orig_mp
            assert orig_mp.configuration.get_option(XML_NAMESPACE_OPTION) \
                    != foo_namespace
            assert orig_mp.configuration.get_option(XML_PREFIX_OPTION) \
                    != bogus_prefix
        finally:
            new_configurator.end()


class TestUpdateResourceFromData(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_update_nested_member_from_data(self, resource_repo):
        # Set up member that does not have a parent.
        coll = resource_repo.get_collection(IMyEntity)
        ent = MyEntity(id=1)
        mb = coll.create_member(ent)
        # Set up second member with same ID that does have a parent.
        tmp_coll = create_staging_collection(IMyEntity)
        parent = MyEntityParent(id=0)
        upd_ent = MyEntity(id=1, parent=parent)
        upd_mb = tmp_coll.create_member(upd_ent)
        rpr = as_representer(mb, CsvMime)
        attribute_options = {('parent',):{WRITE_AS_LINK_OPTION:False}}
        with rpr.with_updated_configuration(attribute_options=
                                                attribute_options):
            de = rpr.resource_to_data(upd_mb)
            mb.update(de)
            assert mb.parent.id == parent.id

    def test_update_nested_collection_from_data(self, resource_repo):
        # Set up member that has one child.
        coll = resource_repo.get_collection(IMyEntity)
        ent = MyEntity(id=1)
        child0 = MyEntityChild(id=0)
        ent.children.append(child0)
        mb = coll.create_member(ent)
        # Set up another member with two children with different IDs.
        tmp_coll = create_staging_collection(IMyEntity)
        upd_ent = MyEntity(id=1)
        child1 = MyEntityChild(id=1)
        child1.parent = upd_ent
        child2 = MyEntityChild(id=2)
        child2.parent = upd_ent
        upd_ent.children.append(child1)
        upd_ent.children.append(child2)
        upd_mb = tmp_coll.create_member(upd_ent)
        rpr = as_representer(mb, CsvMime)
        attribute_options = {('children',):{IGNORE_OPTION:False,
                                            WRITE_AS_LINK_OPTION:False}, }
        with rpr.with_updated_configuration(attribute_options=
                                                    attribute_options):
            de = rpr.resource_to_data(upd_mb)
            mb.update(de)
            assert set([mb.id for mb in mb.children]) == set([1, 2])


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
