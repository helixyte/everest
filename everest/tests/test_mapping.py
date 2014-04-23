"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 9, 2012.
"""
import pytest

from everest.mime import CsvMime
from everest.mime import XmlMime
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.dataelements import DataElementAttributeProxy
from everest.representers.dataelements import LinkedDataElement
from everest.representers.interfaces import IRepresenterRegistry
from everest.representers.utils import get_mapping_registry
from everest.representers.xml import XML_NAMESPACE_OPTION
from everest.representers.xml import XML_TAG_OPTION
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.resources import MyEntityMember
from everest.tests.complete_app.testing import create_collection
from everest.tests.complete_app.testing import create_entity
from everest.tests.test_entities import MyEntity
from everest.mime import JsonMime


__docformat__ = 'reStructuredText en'
__all__ = ['TestMapping',
           ]


class TestMapping(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_rpr.zcml'

    def test_defaults(self, mapping_registry_factory):
        mp = mapping_registry_factory(CsvMime).find_or_create_mapping(
                                                                MyEntityMember)
        attrs = mp.get_attribute_map()
        assert attrs['text'].options.get(IGNORE_OPTION) is None
        assert attrs['parent'].options.get(IGNORE_OPTION) is False
        key = ('parent',)
        parent_attrs = mp.get_attribute_map(key=key)
        assert parent_attrs['text'].options.get(IGNORE_OPTION) is None

    def test_clone_update_attributes(self, mapping_registry_factory):
        key = ('parent', 'text')
        mp = mapping_registry_factory(CsvMime).find_or_create_mapping(
                                                                MyEntityMember)
        mp1 = mp.clone(attribute_options={key:{IGNORE_OPTION:True}})
        p_key = ('parent',)
        parent_attrs = mp1.get_attribute_map(key=p_key)
        assert parent_attrs['text'].options.get(IGNORE_OPTION) is True
        mp1.update(attribute_options={key:{IGNORE_OPTION:False}})
        parent_attrs_upd = mp1.get_attribute_map(key=p_key)
        assert parent_attrs_upd['text'].options.get(IGNORE_OPTION) is False

    @pytest.mark.parametrize('mime,rpr_attr',
                             [(CsvMime, 'parent'),
                              (XmlMime, 'myentityparent'),
                              (JsonMime, 'parent')
                              ])
    def test_attribute_access(self, mapping_registry_factory, mime, rpr_attr):
        #
        mp = mapping_registry_factory(mime).find_or_create_mapping(
                                                                MyEntityMember)
        assert mp.has_attribute('parent')
        assert mp.has_attribute_repr(rpr_attr)
        attr = mp.get_attribute('parent')
        assert attr is mp.get_attribute_map()['parent']
        with pytest.raises(AttributeError):
            dummy = mp.get_attribute('prnt')

    def test_map_to_data_element(self, resource_repo):
        def _test(mb, cnt_type, parent_repr_name, children_repr_name):
            mp_reg = get_mapping_registry(cnt_type)
            mp = mp_reg.find_or_create_mapping(MyEntityMember)
            de = mp.map_to_data_element(mb)
            prx = DataElementAttributeProxy(de)
            assert prx.get_data_element() is de
            assert prx.id == 0
            assert prx.text == 'TEXT'
            assert prx.number == 1
            if cnt_type is XmlMime:
                # The parent attribute is a link.
                assert isinstance(getattr(prx, parent_repr_name),
                                  LinkedDataElement)
                with pytest.raises(AttributeError):
                    dummy = getattr(prx, children_repr_name)
            else:
                assert isinstance(getattr(prx, parent_repr_name),
                                  DataElementAttributeProxy)
                children_el = getattr(prx, children_repr_name)
                assert isinstance(children_el, LinkedDataElement)
            # Nonexisting attribute raises error.
            with pytest.raises(AttributeError):
                dummy = getattr(prx, 'foo')
            with pytest.raises(AttributeError):
                setattr(prx, 'foo', 'murks')
            # Set terminal attribute.
            prx.id = 1
            assert prx.id == 1
            # Set nested attribute.
            setattr(prx, parent_repr_name, None)
            assert getattr(prx, parent_repr_name) is None
            with pytest.raises(ValueError):
                setattr(prx, parent_repr_name, 1)
        entity = create_entity()
        coll = resource_repo.get_collection(IMyEntity)
        mb = coll.create_member(entity)
        _test(mb, XmlMime, 'myentityparent', 'myentitychildren')
        _test(mb, CsvMime, 'parent', 'children')

    def test_map_to_data_element_with_member(self, resource_repo):
        entity = create_entity()
        coll = resource_repo.get_collection(IMyEntity)
        mb = coll.create_member(entity)
        mp_reg = get_mapping_registry(CsvMime)
        mp = mp_reg.find_or_create_mapping(MyEntityMember)
        mp1 = mp.clone(
            attribute_options={('parent',):{WRITE_AS_LINK_OPTION:False},
                             })
        de = mp1.map_to_data_element(mb)
        prx = DataElementAttributeProxy(de)
        assert not prx.parent is None
        #
        entity.parent = None
        de1 = mp1.map_to_data_element(mb)
        prx1 = DataElementAttributeProxy(de1)
        with pytest.raises(AttributeError):
            dummy = getattr(prx1, 'parent')

    def test_map_to_data_element_with_collection(self, resource_repo):
        entity = create_entity()
        coll = resource_repo.get_collection(IMyEntity)
        mb = coll.create_member(entity)
        assert len(entity.children) == 1
        assert len(mb.children) == 1
        mb_child = next(iter(mb.children))
        assert len(mb_child.children) == 1
        mp_reg = get_mapping_registry(CsvMime)
        mp = mp_reg.find_or_create_mapping(MyEntityMember)
        mp1 = mp.clone(
            attribute_options={('children',):{IGNORE_OPTION:False,
                                            WRITE_AS_LINK_OPTION:False},
                               ('children', 'children'):
                                             {IGNORE_OPTION:False,
                                              WRITE_AS_LINK_OPTION:False}
                                })
        de = mp1.map_to_data_element(mb)
        prx = DataElementAttributeProxy(de)
        assert len(prx.children) == 1
        assert len(prx.children[0].children) == 1

    def test_mapping_duplicate_prefix(self, new_configurator):
        coll_cls = new_configurator.registry.getUtility(IMyEntity,
                                                    name='collection-class')
        rpr_reg = new_configurator.registry.queryUtility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(XmlMime)
        mp = mp_reg.find_or_create_mapping(coll_cls)
        ns = 'foo'
        mp.configuration.set_option(XML_NAMESPACE_OPTION, ns)
        with pytest.raises(ValueError) as cm:
            mp.mapping_registry.set_mapping(mp)
        exc_msg = 'is already registered for namespace'
        assert str(cm.value).find(exc_msg) != -1

    def test_mapping_duplicate_tag(self, new_configurator):
        coll_cls = new_configurator.registry.getUtility(IMyEntity,
                                                name='collection-class')
        rpr_reg = new_configurator.registry.queryUtility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(XmlMime)
        mp = mp_reg.find_or_create_mapping(coll_cls)
        mb_mp = mp_reg.find_or_create_mapping(MyEntityMember)
        mb_tag = mb_mp.configuration.get_option(XML_TAG_OPTION)
        mp.configuration.set_option(XML_TAG_OPTION, mb_tag)
        mp.mapping_registry.set_mapping(mp)
        with pytest.raises(ValueError) as cm:
            getattr(mp.mapping_registry, 'parsing_lookup')
        assert str(cm.value).startswith('Duplicate tag')

    def test_mapping_reset_lookup(self, new_configurator):
        coll_cls = new_configurator.registry.getUtility(IMyEntity,
                                                    name='collection-class')
        rpr_reg = new_configurator.registry.queryUtility(IRepresenterRegistry)
        mp_reg = rpr_reg.get_mapping_registry(XmlMime)
        old_lookup = mp_reg.parsing_lookup
        mp = mp_reg.find_or_create_mapping(coll_cls)
        new_tag = 'my-new-entities'
        mp.configuration.set_option(XML_TAG_OPTION, new_tag)
        mp_reg.set_mapping(mp)
        new_lookup = mp_reg.parsing_lookup
        assert not old_lookup is new_lookup
        ns = mp.configuration.get_option(XML_NAMESPACE_OPTION)
        cls_map = new_lookup.get_namespace(ns)
        assert cls_map[new_tag] == mp.data_element_class

    def test_mapping_linked_xml_data_element_with_string_id(self,
                                                mapping_registry_factory,
                                                resource_repo): # pylint: disable=W0613
        # FIXME: Using resource_repo only for its side effect here.
        mp_reg = mapping_registry_factory(XmlMime)
        mb_mp = mp_reg.find_or_create_mapping(MyEntityMember)
        coll = create_collection()
        mb = next(iter(coll))
        mb_id = 'unique'
        mb.id = mb_id
        data_el = mb_mp.create_linked_data_element_from_resource(mb)
        link_el = next(data_el.iterchildren())
        assert link_el.get_id() == mb.id

    def test_mapping_polymorhpic(self, new_configurator,
                                 mapping_registry_factory):
        coll_cls = new_configurator.registry.getUtility(IMyEntity,
                                                        name='collection-class')
        # pylint: disable=W0232
        class IMyDerivedEntity(IMyEntity):
            pass
        class MyDerivedEntity(MyEntity):
            pass
        class MyDerivedEntityMember(MyEntityMember):
            pass
        class MyDerivedEntityCollection(coll_cls):
            pass
        # pylint: enable=W0232
        new_configurator.add_resource(IMyDerivedEntity, MyDerivedEntityMember,
                                      MyDerivedEntity,
                                      MyDerivedEntityCollection,
                                      expose=False)
        new_configurator.add_resource_representer(
                                            IMyDerivedEntity,
                                            XmlMime,
                                            attribute_options=
                                            {('parent',):dict(ignore=True)})
        new_configurator.begin()
        try:
            mp_reg = mapping_registry_factory(XmlMime)
            mp = mp_reg.find_or_create_mapping(coll_cls)
            for rc in (MyDerivedEntityMember, MyDerivedEntityCollection):
                attr = None
                for attr in mp.attribute_iterator(rc):
                    if attr.name == 'parent':
                        break
                assert not attr is None
                assert getattr(attr, IGNORE_OPTION) is True
        finally:
            new_configurator.end()
