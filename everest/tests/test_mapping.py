"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 9, 2012.
"""
from everest.mime import CsvMime
from everest.mime import XmlMime
from everest.representers.config import IGNORE_ON_READ_OPTION
from everest.representers.config import IGNORE_ON_WRITE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.dataelements import DataElementAttributeProxy
from everest.representers.utils import get_mapping_registry
from everest.representers.xml import XML_NAMESPACE_OPTION
from everest.representers.xml import XML_TAG_OPTION
from everest.resources.utils import get_collection_class
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.resources import MyEntityMember
from everest.tests.testapp_db.testing import create_entity
from everest.tests.test_entities import MyEntity
from everest.representers.dataelements import LinkedDataElement

__docformat__ = 'reStructuredText en'
__all__ = ['MappingTestCase',
           ]


class MappingTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_rpr.zcml'

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
        parent_attrs = mp.get_attribute_map(key=key)
        self.assert_true(
            parent_attrs['text'].options.get(IGNORE_ON_READ_OPTION) is None)
        self.assert_true(
            parent_attrs['text'].options.get(IGNORE_ON_WRITE_OPTION) is None)

    def test_clone_with_options(self):
        mp_reg = get_mapping_registry(CsvMime)
        mp = mp_reg.find_or_create_mapping(MyEntityMember)
        mp1 = mp.clone(
                attribute_options={('parent', 'text'):
                                        {IGNORE_ON_READ_OPTION:True}})
        key = ('parent',)
        parent_attrs = mp1.get_attribute_map(key=key)
        self.assert_true(
            parent_attrs['text'].options.get(IGNORE_ON_READ_OPTION) is True)

    def test_map_to_data_element(self):
        def _test(cnt_type, parent_repr_name, children_repr_name):
            entity = create_entity()
            mb = MyEntityMember.create_from_entity(entity)
            mp_reg = get_mapping_registry(cnt_type)
            mp = mp_reg.find_or_create_mapping(MyEntityMember)
            de = mp.map_to_data_element(mb)
            prx = DataElementAttributeProxy(de)
            self.assert_true(prx.get_data_element() is de)
            self.assert_equal(prx.id, 0)
            self.assert_equal(prx.text, 'TEXT')
            self.assert_equal(prx.number, 1)
            # The parent and children attributes are links.
            self.assert_true(isinstance(getattr(prx, parent_repr_name),
                                        LinkedDataElement))
            children_el = getattr(prx, children_repr_name)
            if cnt_type is XmlMime:
                self.assert_is_none(children_el)
            else:
                self.assert_true(isinstance(children_el, LinkedDataElement))
            # Nonexisting attribute raises error.
            self.assert_raises(AttributeError, getattr, prx, 'foo')
            self.assert_raises(AttributeError, setattr, prx, 'foo', 'murks')
            # Set terminal attribute.
            prx.id = 1
            self.assert_equal(prx.id, 1)
            # Set nested attribute.
            setattr(prx, parent_repr_name, None)
            self.assert_is_none(getattr(prx, parent_repr_name))
            self.assert_raises(ValueError, setattr, prx, parent_repr_name,
                               1)
        _test(XmlMime, 'myentityparent', 'myentitychildren')
        _test(CsvMime, 'parent', 'children')

    def test_map_to_data_element_with_member(self):
        entity = create_entity()
        mb = MyEntityMember.create_from_entity(entity)
        mp_reg = get_mapping_registry(CsvMime)
        mp = mp_reg.find_or_create_mapping(MyEntityMember)
        mp1 = mp.clone(
            attribute_options={('parent',):{WRITE_AS_LINK_OPTION:False},
                             })
        de = mp1.map_to_data_element(mb)
        prx = DataElementAttributeProxy(de)
        self.assert_is_not_none(prx.parent)
        #
        entity.parent = None
        de1 = mp1.map_to_data_element(mb)
        prx1 = DataElementAttributeProxy(de1)
        self.assert_is_none(prx1.parent)

    def test_map_to_data_element_with_collection(self):
        entity = create_entity()
        mb = MyEntityMember.create_from_entity(entity)
        mp_reg = get_mapping_registry(CsvMime)
        mp = mp_reg.find_or_create_mapping(MyEntityMember)
        mp1 = mp.clone(
            attribute_options={('children',):{IGNORE_ON_WRITE_OPTION:False,
                                            WRITE_AS_LINK_OPTION:False},
                             ('children', 'children'):
                                        {IGNORE_ON_WRITE_OPTION:False,
                                         WRITE_AS_LINK_OPTION:False}
                             })
        de = mp1.map_to_data_element(mb)
        prx = DataElementAttributeProxy(de)
        self.assert_equal(len(prx.children), 1)
        self.assert_equal(len(prx.children[0].children), 1)

    def test_mapping_duplicate_prefix(self):
        mp_reg = get_mapping_registry(XmlMime)
        mp = mp_reg.find_or_create_mapping(get_collection_class(IMyEntity))
        ns = 'foo'
        mp.configuration.set_option(XML_NAMESPACE_OPTION, ns)
        with self.assert_raises(ValueError) as cm:
            mp.mapping_registry.set_mapping(mp)
        exc_msg = 'is already registered for namespace'
        self.assert_not_equal(cm.exception.message.find(exc_msg), -1)

    def test_mapping_duplicate_tag(self):
        mp_reg = get_mapping_registry(XmlMime)
        mp = mp_reg.find_or_create_mapping(get_collection_class(IMyEntity))
        mb_mp = mp_reg.find_or_create_mapping(MyEntityMember)
        mb_tag = mb_mp.configuration.get_option(XML_TAG_OPTION)
        mp.configuration.set_option(XML_TAG_OPTION, mb_tag)
        mp.mapping_registry.set_mapping(mp)
        with self.assert_raises(ValueError) as cm:
            getattr(mp.mapping_registry, 'parsing_lookup')
        exc_msg = 'Duplicate tag "%s" ' % mb_tag
        self.assert_not_equal(cm.exception.message.find(exc_msg), -1)

    def test_mapping_reset_lookup(self):
        mp_reg = get_mapping_registry(XmlMime)
        old_lookup = mp_reg.parsing_lookup
        mp = mp_reg.find_or_create_mapping(get_collection_class(IMyEntity))
        new_tag = 'my-new-entities'
        mp.configuration.set_option(XML_TAG_OPTION, new_tag)
        mp_reg.set_mapping(mp)
        new_lookup = mp_reg.parsing_lookup
        self.assert_false(old_lookup is new_lookup)
        ns = mp.configuration.get_option(XML_NAMESPACE_OPTION)
        cls_map = new_lookup.get_namespace(ns)
        self.assert_equal(cls_map[new_tag], mp.data_element_class)

    def test_mapping_polymorhpic(self):
        # pylint: disable=W0232
        class IMyDerivedEntity(IMyEntity):
            pass
        class MyDerivedEntity(MyEntity):
            pass
        class MyDerivedEntityMember(MyEntityMember):
            pass
        class MyDerivedEntityCollection(get_collection_class(IMyEntity)):
            pass
        # pylint: enable=W0232
        self.config.add_resource(IMyDerivedEntity, MyDerivedEntityMember,
                                 MyDerivedEntity, MyDerivedEntityCollection,
                                 expose=False)
        self.config.add_resource_representer(
                                    IMyDerivedEntity,
                                    XmlMime,
                                    attribute_options=
                                            {('parent',):dict(ignore=True)})
        mp_reg = get_mapping_registry(XmlMime)
        mp = mp_reg.find_or_create_mapping(get_collection_class(IMyEntity))
        for rc in (MyDerivedEntityMember, MyDerivedEntityCollection):
            attr = None
            for attr in mp.attribute_iterator(rc):
                if attr.name == 'parent':
                    break
            self.assert_is_not_none(attr)
            self.assert_equal(attr.ignore_on_write, True)
            self.assert_equal(attr.ignore_on_read, True)
