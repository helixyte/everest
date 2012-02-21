"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2011.
"""

from everest.db import get_metadata
from everest.db import reset_metadata
from everest.querying.filtering import SqlFilterSpecificationVisitor
from everest.querying.specifications import FilterSpecificationFactory
from everest.repository import REPOSITORIES
from everest.representers.base import DataElementGenerator
from everest.representers.base import RepresenterConfiguration
from everest.representers.base import SimpleDataElementRegistry
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.base import Collection
from everest.resources.base import ResourceToEntityFilterSpecificationVisitor
from everest.resources.descriptors import terminal_attribute
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import new_stage_collection
from everest.testing import Pep8CompliantTestCase
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.entities import MyEntityChild
from everest.tests.testapp_db.entities import MyEntityGrandchild
from everest.tests.testapp_db.entities import MyEntityParent
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityChild
from everest.tests.testapp_db.interfaces import IMyEntityParent
from everest.tests.testapp_db.resources import MyEntityChildMember
from everest.tests.testapp_db.resources import MyEntityGrandchildMember
from everest.tests.testapp_db.resources import MyEntityMember
from everest.tests.testapp_db.resources import MyEntityParentMember
from everest.url import resource_to_url
from pkg_resources import resource_filename # pylint: disable=E0611

__docformat__ = 'reStructuredText en'
__all__ = ['AttributesTestCase',
           'DescriptorsTestCase',
           ]


def teardown():
    # Module level teardown.
    if not DescriptorsTestCase.metadata is None:
        DescriptorsTestCase.metadata.drop_all()
        DescriptorsTestCase.metadata = None
    reset_metadata()


class AttributesTestCase(Pep8CompliantTestCase):
    def test_names(self):
        self.assert_equal(
                    MyEntityMember.get_attribute_names(),
                    ['id', 'parent', 'nested_parent', 'children', 'text',
                     'text_rc', 'number', 'parent_text'])

    def test_types(self):
        attrs = MyEntityMember.get_attributes().values()
        self.assert_equal(attrs[0].name, 'id')
        self.assert_equal(attrs[0].kind, ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attrs[0].entity_name, 'id')
        self.assert_equal(attrs[0].value_type, int)
        self.assert_equal(attrs[1].name, 'parent')
        self.assert_equal(attrs[1].kind, ResourceAttributeKinds.MEMBER)
        self.assert_equal(attrs[1].entity_name, 'parent')
        self.assert_equal(attrs[1].value_type, IMyEntityParent)
        self.assert_equal(attrs[3].name, 'children')
        self.assert_equal(attrs[3].kind,
                          ResourceAttributeKinds.COLLECTION)
        self.assert_equal(attrs[3].entity_name, 'children')
        self.assert_equal(attrs[3].value_type, IMyEntityChild)
        self.assert_equal(attrs[4].name, 'text')
        self.assert_equal(attrs[4].kind, ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attrs[4].entity_name, 'text')
        self.assert_equal(attrs[4].value_type, str)
        self.assert_equal(attrs[6].name, 'number')
        self.assert_equal(attrs[6].kind, ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attrs[6].entity_name, 'number')
        self.assert_equal(attrs[6].value_type, int)

    def test_inheritance(self):
        class MyEntityDerivedMember(MyEntityMember):
            text = terminal_attribute('text', int)
        attrs = MyEntityDerivedMember.get_attributes()
        attr = attrs['text']
        self.assert_equal(attr.kind,
                          ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attr.entity_name, 'text')
        self.assert_equal(attr.value_type, int)


class DescriptorsTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    ini_file_path = resource_filename('everest.tests.testapp_db',
                                      'testapp.ini')
    ini_section_name = 'app:testapp_db'

    metadata = None

    TEST_TEXT = 'TEST TEXT'
    UPDATED_TEXT = 'UPDATED TEXT'

    def set_up(self):
        if DescriptorsTestCase.metadata is None:
            reset_metadata()
        ResourceTestCase.set_up(self)

    def tear_down(self):
        if DescriptorsTestCase.metadata is None:
            DescriptorsTestCase.metadata = get_metadata(REPOSITORIES.ORM)
        ResourceTestCase.tear_down(self)

    def test_terminal_access(self):
        entity = MyEntity()
        member = MyEntityMember.create_from_entity(entity)
        self.assert_true(isinstance(member.text, str))
        self.assert_true(isinstance(member.number, int))

    def test_member_access(self):
        parent = MyEntityParent()
        entity = MyEntity(parent=parent)
        member = MyEntityMember.create_from_entity(entity)
        self.assert_true(isinstance(member.parent, MyEntityParentMember))
        self.assert_true(member.parent.get_entity() is parent)

    def test_collection_access(self):
        parent = MyEntityParent()
        entity = MyEntity(parent=parent)
        coll = get_root_collection(IMyEntity)
        member = coll.create_member(entity)
        self.assert_true(isinstance(member.children, Collection))
        i = 0
        n = 5
        while i < n:
            child_entity = MyEntityChild()
            member.children.create_member(child_entity)
            i += 1
        self.assert_equal(len(member.children), n)

    def test_update_terminal(self):
        my_entity = self.__create_entity()
        coll = new_stage_collection(IMyEntity)
        member = coll.create_member(my_entity)
        member.text = self.UPDATED_TEXT
        gen = self._make_data_element_generator()
        data_el = gen.run(member)
        del member
        del my_entity
        my_entity = self.__create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(context.text, MyEntity.DEFAULT_TEXT)
        context.update_from_data(data_el)
        self.assert_equal(context.text, self.UPDATED_TEXT)

    def test_update_terminal_in_parent(self):
        my_entity = self.__create_entity()
        my_entity.parent.text = self.UPDATED_TEXT
        coll = new_stage_collection(IMyEntity)
        member = coll.create_member(my_entity)
        gen = self._make_data_element_generator()
        data_el = gen.run(member)
        del member
        del my_entity
        my_entity = self.__create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
        context.update_from_data(data_el)
        self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_update_terminal_in_child(self):
        my_entity = self.__create_entity()
        my_entity.children[0].text = self.UPDATED_TEXT
        coll = new_stage_collection(IMyEntity)
        member = coll.create_member(my_entity)
        gen = self._make_data_element_generator()
        data_el = gen.run(member)
        del member
        del my_entity
        my_entity = self.__create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(iter(context.children).next().text,
                          MyEntity.DEFAULT_TEXT)
        context.update_from_data(data_el)
        self.assert_equal(iter(context.children).next().text,
                          self.UPDATED_TEXT)

    def test_update_member(self):
        my_entity = self.__create_entity()
        new_parent = MyEntityParent()
        new_parent.text = self.UPDATED_TEXT
        new_parent.id = 2
        my_entity.parent = new_parent
        coll = new_stage_collection(IMyEntity)
        member = coll.create_member(my_entity)
        gen = self._make_data_element_generator()
        data_el = gen.run(member)
        del member
        del my_entity
        my_entity = self.__create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
        context.update_from_data(data_el)
        self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_update_member_with_link(self):
        my_entity = self.__create_entity()
        new_parent = MyEntityParent()
        new_parent.text = self.UPDATED_TEXT
        new_parent.id = 2
        my_entity.parent = new_parent
        coll = new_stage_collection(IMyEntity)
        member = coll.create_member(my_entity)
        gen = self._make_data_element_generator()
        data_el = gen.run(member,
                          mapping_info=
                            dict(parent=dict(write_as_link=True),
                                 nested_parent=dict(ignore=True)))
        # The linked-to parent needs to be in the root collection.
        my_entity.parent = None
        del member
        del my_entity
        parent_coll = get_root_collection(IMyEntityParent)
        parent_coll.create_member(new_parent)
        my_entity = self.__create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
        context.update_from_data(data_el)
        self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_delete_child(self):
        my_entity = self.__create_entity()
        del my_entity.children[0]
        coll = new_stage_collection(IMyEntity)
        member = coll.create_member(my_entity)
        gen = self._make_data_element_generator()
        data_el = gen.run(member)
        del member
        del my_entity
        my_entity = self.__create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(len(context.children), 1)
        context.update_from_data(data_el)
        self.assert_equal(len(context.children), 0)

    def test_delete_grandchild(self):
        my_entity = self.__create_entity()
        del my_entity.children[0].children[0]
        coll = new_stage_collection(IMyEntity)
        member = coll.create_member(my_entity)
        gen = self._make_data_element_generator()
        data_el = gen.run(member)
        del member
        del my_entity
        my_entity = self.__create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(len(iter(context.children).next().children),
                          1)
        context.update_from_data(data_el)
        self.assert_equal(len(iter(context.children).next().children),
                          0)

    def test_add_child(self):
        my_entity = self.__create_entity()
        new_child = MyEntityChild()
        my_entity.children.append(new_child)
        coll = new_stage_collection(IMyEntity)
        member = coll.create_member(my_entity)
        self.assert_equal(len(member.children), 2)
        gen = self._make_data_element_generator()
        data_el = gen.run(member)
        del member
        del my_entity
        my_entity = self.__create_entity()
        coll = get_root_collection(IMyEntity)
        context = coll.create_member(my_entity)
        self.assert_equal(len(context.children), 1)
        context.update_from_data(data_el)
        self.assert_equal(len(context.children), 2)

    def test_filter_specification_visitor(self):
        coll = get_root_collection(IMyEntity)
        mb_cls = get_member_class(coll)
        my_entity = self.__create_entity()
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
                spec_fac.create_equal_to('parent', member.parent.get_entity()),
                ]
        expecteds = [('text', MyEntity.text.__eq__(self.TEST_TEXT)),
                     ('text_ent', MyEntity.text_ent.__eq__(
                                                        self.TEST_TEXT)),
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

    def test_nested_access(self):
        my_entity = self.__create_entity()
        coll = new_stage_collection(IMyEntity)
        member = coll.create_member(my_entity)
        self.assert_equal(member.parent_text, MyEntityParent.DEFAULT_TEXT)

    def test_urls(self):
        my_entity = self.__create_entity()
        coll = get_root_collection(IMyEntity)
        mb = coll.create_member(my_entity)
        self.assert_equal(resource_to_url(mb),
                          'http://0.0.0.0:6543/my-entities/0/')
        self.assert_equal(resource_to_url(mb.parent),
                          'http://0.0.0.0:6543/my-entity-parents/0/')
        self.assert_equal(resource_to_url(mb.nested_parent),
                        'http://0.0.0.0:6543/my-entities/0/nested-parent/')
        self.assert_equal(resource_to_url(mb.children),
                          'http://0.0.0.0:6543/my-entities/0/children/')
        mb_child = mb.children['0']
        self.assert_equal(mb_child.id, 0)
        self.assert_equal(resource_to_url(mb_child.children),
                          'http://0.0.0.0:6543/my-entity-grandchildren/'
                          '?q=parent:equal-to:'
                          'http://0.0.0.0:6543/my-entities/0/children/0/')
        self.assert_equal(resource_to_url(mb_child.no_backref_children),
                          'http://0.0.0.0:6543/my-entity-grandchildren/'
                          '?q=id:contained:0')

    def _make_data_element_generator(self):
        reg = SimpleDataElementRegistry()
        # Fine tune DataElementGenerator configuration.
        repr_config = RepresenterConfiguration()
        repr_config.set_option('mapping',
                               dict(parent=dict(write_as_link=False,
                                                ignore=False),
                                    nested_parent=dict(write_as_link=False,
                                                       ignore=False),
                                    children=dict(write_as_link=False,
                                                  ignore=False)))
        for cls in (MyEntityMember,):
            de_cls = reg.create_data_element_class(cls, repr_config)
            reg.set_data_element_class(de_cls)
        repr_config = RepresenterConfiguration()
        repr_config.set_option('mapping',
                               dict(children=dict(write_as_link=False,
                                                  ignore=False),
                                    no_backref_children=dict(ignore=True)))
        for cls in (MyEntityChildMember,
                    get_collection_class(MyEntityChildMember)):
            de_cls = reg.create_data_element_class(cls, repr_config)
            reg.set_data_element_class(de_cls)
        repr_config = RepresenterConfiguration()
        repr_config.set_option('mapping',
                               dict(parent=dict(ignore=True)))
        for cls in (MyEntityGrandchildMember,
                    get_collection_class(MyEntityGrandchildMember)):
            de_cls = reg.create_data_element_class(cls, repr_config)
            reg.set_data_element_class(de_cls)
        repr_config = RepresenterConfiguration()
        for cls in (MyEntityParentMember,):
            de_cls = reg.create_data_element_class(cls, repr_config)
            reg.set_data_element_class(de_cls)
        gen = DataElementGenerator(reg)
        return gen

    def __create_entity(self):
        my_entity = MyEntity()
        my_entity.id = 0
        my_entity_parent = MyEntityParent()
        my_entity_parent.id = 0
        my_entity.parent = my_entity_parent
        my_entity_child = MyEntityChild()
        my_entity_child.id = 0
        my_entity.children.append(my_entity_child)
        my_entity_grandchild = MyEntityGrandchild()
        my_entity_grandchild.id = 0
        my_entity_child.children.append(my_entity_grandchild)
        return my_entity
