"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2011.
"""
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.querying.specifications import FilterSpecificationFactory
from everest.repositories.rdb import SqlFilterSpecificationVisitor
from everest.repositories.rdb.testing import RdbTestCaseMixin
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import RepresenterConfiguration
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.representers.mapping import SimpleMappingRegistry
from everest.resources.attributes import get_resource_class_attribute
from everest.resources.attributes import get_resource_class_attribute_iterator
from everest.resources.attributes import get_resource_class_attribute_names
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.attributes import get_resource_class_collection_attribute_iterator
from everest.resources.attributes import get_resource_class_member_attribute_iterator
from everest.resources.attributes import get_resource_class_relationship_attribute_iterator
from everest.resources.attributes import get_resource_class_terminal_attribute_iterator
from everest.resources.attributes import is_resource_class_collection_attribute
from everest.resources.attributes import is_resource_class_member_attribute
from everest.resources.attributes import is_resource_class_resource_attribute
from everest.resources.attributes import is_resource_class_terminal_attribute
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.base import ResourceToEntityFilterSpecificationVisitor
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_member_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import resource_to_url
from everest.testing import Pep8CompliantTestCase
from everest.testing import ResourceTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild
from everest.tests.complete_app.interfaces import IMyEntityParent
from everest.tests.complete_app.resources import MyEntityMember
from everest.tests.complete_app.resources import MyEntityParentMember
from everest.tests.complete_app.testing import create_collection
from everest.tests.complete_app.testing import create_entity
from mock import patch
import datetime

__docformat__ = 'reStructuredText en'
__all__ = ['AttributesTestCase',
           'MemoryDescriptorsTestCase',
           'RdbDescriptorsTestCase'
           ]

ATTRIBUTE_NAMES = ['id', 'parent', 'children', 'text',
                   'text_rc', 'number', 'date_time', 'parent_text']


class AttributesTestCase(Pep8CompliantTestCase):
    def test_names(self):
        self.assert_equal(
                list(get_resource_class_attribute_names(MyEntityMember)),
                ATTRIBUTE_NAMES)

    def test_terminal_iterator(self):
        it = get_resource_class_terminal_attribute_iterator(MyEntityMember)
        self.assert_equal(set([attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL
                              for attr in it]),
                          set([True]))

    def test_resource_iterator(self):
        it = get_resource_class_relationship_attribute_iterator(MyEntityMember)
        self.assert_equal(set([attr.kind in
                               (RESOURCE_ATTRIBUTE_KINDS.MEMBER,
                                RESOURCE_ATTRIBUTE_KINDS.COLLECTION)
                              for attr in it]),
                          set([True]))

    def test_member_iterator(self):
        it = get_resource_class_member_attribute_iterator(MyEntityMember)
        self.assert_equal(set([attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER
                              for attr in it]),
                          set([True]))

    def test_collection_iterator(self):
        it = get_resource_class_collection_attribute_iterator(MyEntityMember)
        self.assert_equal(set([attr.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION
                              for attr in it]),
                          set([True]))

    def test_types(self):
        attrs = iter(get_resource_class_attributes(MyEntityMember).values())
        attr0 = next(attrs)
        self.assert_equal(attr0.resource_attr, ATTRIBUTE_NAMES[0])
        self.assert_equal(attr0.kind, RESOURCE_ATTRIBUTE_KINDS.TERMINAL)
        self.assert_equal(attr0.entity_attr, 'id')
        self.assert_equal(attr0.attr_type, int)
        attr1 = next(attrs)
        self.assert_equal(attr1.resource_attr, ATTRIBUTE_NAMES[1])
        self.assert_equal(attr1.kind, RESOURCE_ATTRIBUTE_KINDS.MEMBER)
        self.assert_equal(attr1.entity_attr, 'parent')
        self.assert_equal(attr1.attr_type, IMyEntityParent)
        attr2 = next(attrs)
        self.assert_equal(attr2.resource_attr, ATTRIBUTE_NAMES[2])
        self.assert_equal(attr2.kind,
                          RESOURCE_ATTRIBUTE_KINDS.COLLECTION)
        self.assert_equal(attr2.entity_attr, 'children')
        self.assert_equal(attr2.attr_type, IMyEntityChild)
        attr3 = next(attrs)
        self.assert_equal(attr3.resource_attr, ATTRIBUTE_NAMES[3])
        self.assert_equal(attr3.kind, RESOURCE_ATTRIBUTE_KINDS.TERMINAL)
        self.assert_equal(attr3.entity_attr, 'text')
        self.assert_equal(attr3.attr_type, str)
        attr4 = next(attrs)
        self.assert_equal(attr4.resource_attr, ATTRIBUTE_NAMES[4])
        attr5 = next(attrs)
        self.assert_equal(attr5.resource_attr, ATTRIBUTE_NAMES[5])
        self.assert_equal(attr5.kind, RESOURCE_ATTRIBUTE_KINDS.TERMINAL)
        self.assert_equal(attr5.entity_attr, 'number')
        self.assert_equal(attr5.attr_type, int)
        self.assert_true(is_resource_class_member_attribute(MyEntityMember,
                                                            'parent'))
        self.assert_true(is_resource_class_collection_attribute(MyEntityMember,
                                                                'children'))
        self.assert_true(is_resource_class_resource_attribute(MyEntityMember,
                                                              'parent'))
        self.assert_true(is_resource_class_resource_attribute(MyEntityMember,
                                                              'children'))
        self.assert_true(isinstance(getattr(MyEntityMember, 'id'),
                                    terminal_attribute))

    def test_inheritance(self):
        class MyEntityDerivedMember(MyEntityMember):
            text = terminal_attribute(int, 'text')
        attr = get_resource_class_attribute(MyEntityDerivedMember, 'text')
        self.assert_equal(attr.kind,
                          RESOURCE_ATTRIBUTE_KINDS.TERMINAL)
        self.assert_equal(attr.entity_attr, 'text')
        self.assert_equal(attr.attr_type, int)

    def test_invalid_derived_descriptor(self):
        class my_descriptor(member_attribute):
            pass
        with self.assert_raises(TypeError) as cm:
            type('my_rc', (Member,),
                 dict(foo=my_descriptor(IMyEntityParent, 'foo')))
        exc_msg = 'Unknown resource attribute type'
        self.assert_true(str(cm.exception).startswith(exc_msg))

    def test_invalid_descriptor_parameters(self):
        self.assert_raises(ValueError,
                           terminal_attribute, 'not-a-type', 'foo')
        self.assert_raises(ValueError,
                           member_attribute, 'not-a-resource', 'foo')

    def test_entity_backref(self):
        attr = member_attribute(IMyEntityParent, entity_attr='foo')
        self.assert_is_none(attr.resource_backref)
        self.assert_is_none(attr.entity_backref)


class _DescriptorsTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    TEST_TEXT = 'TEST TEXT'
    UPDATED_TEXT = 'UPDATED TEXT'
    PARENT_MAPPING_OPTIONS = {WRITE_AS_LINK_OPTION:False,
                              IGNORE_OPTION:False}
    CHILDREN_MAPPING_OPTIONS = {WRITE_AS_LINK_OPTION:False,
                                IGNORE_OPTION:False}
    GRANDCHILDREN_MAPPING_OPTIONS = {WRITE_AS_LINK_OPTION:False,
                                     IGNORE_OPTION:False}

    def test_attribute_checkers(self):
        self.assert_true(is_resource_class_terminal_attribute(IMyEntity,
                                                              'text'))
        self.assert_true(is_resource_class_member_attribute(IMyEntity,
                                                            'parent'))
        self.assert_true(is_resource_class_collection_attribute(IMyEntity,
                                                                'children'))
        self.assert_true(is_resource_class_resource_attribute(IMyEntity,
                                                              'parent'))
        self.assert_true(is_resource_class_resource_attribute(IMyEntity,
                                                              'children'))
        attr_names = list(get_resource_class_attribute_names(MyEntityMember))
        self.assert_equal(attr_names, ATTRIBUTE_NAMES)
        it = get_resource_class_attribute_iterator(MyEntityMember)
        self.assert_equal([attr.resource_attr for attr in it],
                          ATTRIBUTE_NAMES)

    def test_terminal_access(self):
        entity = MyEntity()
        member = MyEntityMember.create_from_entity(entity)
        self.assert_true(isinstance(member.text, str))
        self.assert_true(isinstance(member.number, int))
        self.assert_true(isinstance(member.date_time, datetime.datetime))

    def test_member_access(self):
        parent = MyEntityParent()
        entity = MyEntity(parent=parent)
        member = MyEntityMember.create_from_entity(entity)
        self.assert_true(isinstance(member.parent, MyEntityParentMember))
        self.assert_true(member.parent.get_entity() is parent)

    def test_collection_access(self):
        parent = MyEntityParent(id=0)
        entity = MyEntity(id=0, parent=parent)
        coll = get_root_collection(IMyEntity)
        member = coll.create_member(entity)
        self.assert_true(isinstance(member.children, Collection))
        child_entity = MyEntityChild()
        member.children.create_member(child_entity)
        self.assert_equal(len(member.children), 1)

    def test_update_from_data_terminal(self):
        my_entity = create_entity()
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        member.text = self.UPDATED_TEXT
        mp = self._make_mapping()
        data_el = mp.map_to_data_element(member)
        del member
        del my_entity
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(context.text, MyEntity.DEFAULT_TEXT)
        context.update(data_el)
        self.assert_equal(context.text, self.UPDATED_TEXT)

    def test_update_from_data_terminal_in_parent(self):
        my_entity = create_entity()
        my_entity.parent.text = self.UPDATED_TEXT
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        mp = self._make_mapping()
        data_el = mp.map_to_data_element(member)
        del member
        del my_entity
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
        context.update(data_el)
        self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_update_from_data_terminal_in_child(self):
        my_entity = create_entity()
        my_entity.children[0].text = self.UPDATED_TEXT
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        mp = self._make_mapping()
        data_el = mp.map_to_data_element(member)
        del member
        del my_entity
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(next(iter(context.children)).text,
                          MyEntity.DEFAULT_TEXT)
        context.update(data_el)
        self.assert_equal(next(iter(context.children)).text,
                          self.UPDATED_TEXT)

    def test_update_from_data_member(self):
        my_entity = create_entity()
        new_parent = MyEntityParent()
        new_parent.text = self.UPDATED_TEXT
        new_parent.id = 2
        my_entity.parent = new_parent
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        mp = self._make_mapping()
        data_el = mp.map_to_data_element(member)
        del member
        del my_entity
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
        context.update(data_el)
        self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_update_from_data_member_from_link(self):
        my_entity = create_entity()
        new_parent = MyEntityParent()
        new_parent.text = self.UPDATED_TEXT
        new_parent.id = 2
        my_entity.parent = new_parent
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        mp = self._make_mapping()
        attribute_options = {('parent',):{WRITE_AS_LINK_OPTION:True},
                             }
        mp_cloned = mp.clone(attribute_options=attribute_options)
        data_el = mp_cloned.map_to_data_element(member)
        # The linked-to parent needs to be in the root collection.
        my_entity.parent = None
        del member
        del my_entity
        parent_coll = get_root_collection(IMyEntityParent)
        parent_coll.create_member(new_parent)
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
        context.update(data_el)
        self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_update_from_data_delete_child(self):
        my_entity = create_entity()
        del my_entity.children[0]
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        mp = self._make_mapping()
        data_el = mp.map_to_data_element(member)
        del member
        del my_entity
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(len(context.children), 1)
        context.update(data_el)
        self.assert_equal(len(context.children), 0)

    def test_update_from_data_delete_grandchild(self):
        my_entity = create_entity()
        del my_entity.children[0].children[0]
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        mp = self._make_mapping()
        data_el = mp.map_to_data_element(member)
        del member
        del my_entity
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(len(next(iter(context.children)).children),
                          1)
        context.update(data_el)
        self.assert_equal(len(next(iter(context.children)).children),
                          0)

    def test_update_from_data_add_child(self):
        my_entity = create_entity()
        new_child = MyEntityChild()
        my_entity.children.append(new_child)
        if new_child.parent is None:
            new_child.parent = my_entity
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        self.assert_equal(len(member.children), 2)
        mp = self._make_mapping()
        data_el = mp.map_to_data_element(member)
        del member
        del my_entity
#        import gc; gc.collect()
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(len(context.children), 1)
        context.update(data_el)
        self.assert_equal(len(context.children), 2)

    def test_add_with_data_element(self):
        my_entity = MyEntity()
        my_entity_parent = MyEntityParent()
        my_entity.parent = my_entity_parent
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        mp = self._make_mapping()
        data_el = mp.map_to_data_element(member)
        del member
        root_coll = get_root_collection(IMyEntity)
        root_coll.add(data_el)
        self.assert_equal(len(coll), 1)

    def test_remove_with_data_element(self):
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        member = coll.create_member(my_entity)
        mp = self._make_mapping()
        data_el = mp.map_to_data_element(member)
        del member
        coll.remove(data_el)
        self.assert_equal(len(coll), 0)

    def test_nested_get(self):
        my_entity = create_entity()
        coll = create_staging_collection(IMyEntity)
        member = coll.create_member(my_entity)
        self.assert_equal(member.parent_text, MyEntityParent.DEFAULT_TEXT)

    def test_nested_set(self):
        ent = MyEntity()
        mb = MyEntityMember.create_from_entity(ent)
        self.assert_true(mb.parent is None)
        self.assert_raises(AttributeError, setattr, mb, 'parent_text', 'foo')

    def test_invalid_descriptors(self):
        with self.assert_raises(ValueError) as cm:
            collection_attribute(IMyEntity)
        exc_msg = 'may be None, but not both.'
        self.assert_true(str(cm.exception).endswith(exc_msg))

    def test_backref_only_collection(self):
        coll = create_collection()
        mb = next(iter(coll))
        child_mb = next(iter(mb.children))
        with patch('%s.resources.MyEntityChildMember.children.entity_attr'
                   % self.package_name, None):
            self.assert_equal(len(child_mb.children), 1)
            grandchild_mb = next(iter(child_mb.children))
            grandchild_mb.parent = None
            self.assert_equal(len(child_mb.children), 0)

    def test_basic_urls(self):
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        mb = coll.create_member(my_entity)
        exp_url = '/my-entities/0/'
        url = resource_to_url(mb)
        self.assert_true(url.endswith(exp_url))
        exp_url = '/my-entity-parents/0/'
        url = resource_to_url(mb.parent)
        self.assert_true(url.endswith(exp_url))
        exp_url = '/my-entity-children/?q=parent:equal-to:' \
                  '"http://0.0.0.0:6543/my-entities/0/"'
        url = resource_to_url(mb.children)
        self.assert_true(url.endswith(exp_url))
        mb_child = mb.children['0']
        self.assert_equal(mb_child.id, 0)
        exp_url = "/my-entity-grandchildren/?q=parent:equal-to:" \
                  "'http://0.0.0.0:6543/my-entity-children/0/'"
        url = resource_to_url(mb_child.children)

    @patch('%s.resources.MyEntityChildMember.children.resource_backref'
           % package_name, None)
    def test_no_backref_collection_url(self):
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        mb = coll.create_member(my_entity)
        mb_child = mb.children['0']
        exp_url = 'my-entity-grandchildren/?q=id:contained:0'
        url = resource_to_url(mb_child.children)
        self.assert_true(url.endswith(exp_url))

    def test_alias(self):
        ent = MyEntityParent()
        mb = MyEntityParentMember.create_from_entity(ent)
        alias_descr = getattr(MyEntityParentMember, 'text_alias')
        self.assert_true(isinstance(alias_descr, attribute_alias))
        self.assert_equal(mb.text_alias, mb.text)
        mb.text_alias = 'altered text'
        self.assert_equal(mb.text, mb.text_alias)

    def test_set_member(self):
        my_entity = create_entity()
        coll = get_root_collection(IMyEntity)
        mb = coll.create_member(my_entity)
        txt = 'FROBNIC'
        new_parent = MyEntityParent(text=txt)
        parent_coll = get_root_collection(IMyEntityParent)
        parent_mb = parent_coll.create_member(new_parent)
        self.assert_not_equal(mb.parent.text, txt)
        mb.parent = parent_mb
        self.assert_equal(mb.parent.text, txt)

    def _make_mapping(self):
        reg = SimpleMappingRegistry()
        mp_opts = {('parent',): self.PARENT_MAPPING_OPTIONS,
                   ('children',): self.CHILDREN_MAPPING_OPTIONS,
                   ('children', 'children'):
                                self.GRANDCHILDREN_MAPPING_OPTIONS,
                   }
        conf = RepresenterConfiguration(attribute_options=mp_opts)
        mp = reg.create_mapping(MyEntityMember, conf)
        reg.set_mapping(mp)
        return mp


class RdbDescriptorsTestCase(RdbTestCaseMixin, _DescriptorsTestCase):
    def test_filter_specification_visitor(self):
        coll = get_root_collection(IMyEntity)
        mb_cls = get_member_class(coll)
        my_entity = create_entity()
        member = coll.create_member(my_entity)
        spec_fac = FilterSpecificationFactory()
        specs = [
                # Terminal access.
                spec_fac.create_equal_to('text', self.TEST_TEXT),
                # Terminal access with different name in entity.
                spec_fac.create_equal_to('text_rc', self.TEST_TEXT),
                # Nested member access with different name in entity.
                spec_fac.create_equal_to('parent.text_rc', self.TEST_TEXT),
                # Nested collection access with different name in entity.
                spec_fac.create_equal_to('children.text_rc', self.TEST_TEXT),
                # Access with dotted entity name in rc attr declaration.
                spec_fac.create_equal_to('parent_text', self.TEST_TEXT),
                # Access to member.
                spec_fac.create_equal_to('parent',
                                         member.parent.get_entity()),
                ]
        expecteds = [('text', MyEntity.text.__eq__(self.TEST_TEXT)),
                     ('text_ent', MyEntity.text_ent.__eq__(self.TEST_TEXT)),
                     ('parent.text_ent',
                      MyEntity.parent.has(
                                    MyEntityParent.text_ent.__eq__(
                                                        self.TEST_TEXT))),
                     ('children.text_ent',
                      MyEntity.children.any(
                                    MyEntityChild.text_ent.__eq__(
                                                        self.TEST_TEXT))),
                     ('parent.text_ent',
                      MyEntity.parent.has(
                                    MyEntityParent.text_ent.__eq__(
                                                        self.TEST_TEXT))),
                     ('parent',
                      MyEntity.parent.__eq__(member.parent.get_entity())),
                     ]
        for spec, expected in zip(specs, expecteds):
            new_attr_name, expr = expected
            visitor = ResourceToEntityFilterSpecificationVisitor(mb_cls)
            spec.accept(visitor)
            new_spec = visitor.expression
            self.assert_equal(new_spec.attr_name, new_attr_name)
            visitor = SqlFilterSpecificationVisitor(MyEntity)
            new_spec.accept(visitor)
            self.assert_equal(str(visitor.expression), str(expr))
        invalid_spec = spec_fac.create_equal_to('foo', self.TEST_TEXT)
        vst = ResourceToEntityFilterSpecificationVisitor(mb_cls)
        self.assert_raises(AttributeError, invalid_spec.accept, vst)


class MemoryDescriptorsTestCase(_DescriptorsTestCase):
    config_file_name = 'configure_no_rdb.zcml'
