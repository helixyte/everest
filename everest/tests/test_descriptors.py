"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2011.
"""

from everest.db import Session
from everest.db import reset_db_engine
from everest.db import reset_metadata
from everest.db import set_db_engine
from everest.querying.filtering import SqlFilterSpecificationVisitor
from everest.querying.specifications import FilterSpecificationFactory
from everest.representers.base import DataElementGenerator
from everest.representers.base import RepresenterConfiguration
from everest.representers.base import SimpleDataElementRegistry
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.base import Collection
from everest.resources.base import ResourceToEntityFilterSpecificationVisitor
from everest.resources.descriptors import terminal_attribute
from everest.resources.utils import get_collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.staging import STAGING_CONTEXT_MANAGERS
from everest.testing import Pep8CompliantTestCase
from everest.testing import ResourceTestCase
from everest.tests.testapp_db import TestApp
from everest.tests.testapp_db.db import create_metadata
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
from sqlalchemy.engine import create_engine
from zope.component import createObject as create_object # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['AttributesTestCase',
           'DescriptorsTestCase',
           ]


def setup():
    # Module level setup.
    reset_db_engine()
    reset_metadata()
    db_string = 'sqlite://'
    engine = create_engine(db_string)
    set_db_engine(engine)
    DescriptorsTestCase.metadata = create_metadata()
    DescriptorsTestCase.metadata.bind = engine
    DescriptorsTestCase.metadata.create_all()
    # 
    Session.remove()


def teardown():
    # Module level teardown.
    if not DescriptorsTestCase.metadata is None:
        DescriptorsTestCase.metadata.drop_all()
        DescriptorsTestCase.metadata = None
    # We want to clear the mappers and ensure the metadata gets rebuilt.
    reset_metadata()
    reset_db_engine()


class AttributesTestCase(Pep8CompliantTestCase):
    def test_names(self):
        self.assert_equal(
                    get_resource_class_attributes(MyEntityMember).keys(),
                    ['id', 'parent', 'children', 'text',
                     'text_rc', 'number', 'parent_text'])

    def test_types(self):
        attrs = get_resource_class_attributes(MyEntityMember).values()
        self.assert_equal(attrs[0].name, 'id')
        self.assert_equal(attrs[0].kind, ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attrs[0].entity_name, 'id')
        self.assert_equal(attrs[0].value_type, int)
        self.assert_equal(attrs[1].name, 'parent')
        self.assert_equal(attrs[1].kind, ResourceAttributeKinds.MEMBER)
        self.assert_equal(attrs[1].entity_name, 'parent')
        self.assert_equal(attrs[1].value_type, IMyEntityParent)
        self.assert_equal(attrs[2].name, 'children')
        self.assert_equal(attrs[2].kind,
                          ResourceAttributeKinds.COLLECTION)
        self.assert_equal(attrs[2].entity_name, 'children')
        self.assert_equal(attrs[2].value_type, IMyEntityChild)
        self.assert_equal(attrs[3].name, 'text')
        self.assert_equal(attrs[3].kind, ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attrs[3].entity_name, 'text')
        self.assert_equal(attrs[3].value_type, str)
        self.assert_equal(attrs[5].name, 'number')
        self.assert_equal(attrs[5].kind, ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attrs[5].entity_name, 'number')
        self.assert_equal(attrs[5].value_type, int)

    def test_inheritance(self):
        class MyEntityDerivedMember(MyEntityMember):
            text = terminal_attribute('text', int)
        attrs = get_resource_class_attributes(MyEntityDerivedMember)
        attr = attrs['text']
        self.assert_equal(attr.kind,
                          ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attr.entity_name, 'text')
        self.assert_equal(attr.value_type, int)


class DescriptorsTestCase(ResourceTestCase):
    test_app_cls = TestApp

    metadata = None
    _connection = None
    _transaction = None
    _request = None

    TEST_TEXT = 'TEST TEXT'
    UPDATED_TEXT = 'UPDATED TEXT'

    def _custom_configure(self):
        if DescriptorsTestCase.metadata is None:
            setup()
        # Set up outer transaction.
        self._connection = DescriptorsTestCase.metadata.bind.connect()
        self._transaction = self._connection.begin()
        Session.configure(bind=self._connection,
                          extension=None)
        ResourceTestCase._custom_configure(self)

    def tear_down(self):
        ResourceTestCase.tear_down(self)
        Session.remove()
        self._transaction.rollback()
        self._connection.close()

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
        member = MyEntityMember.create_from_entity(entity)
        self.assert_true(isinstance(member.children, Collection))
        coll = get_collection(IMyEntity)
        coll.add(member)
        i = 0
        n = 5
        while i < n:
            child_entity = MyEntityChild()
            child_member = MyEntityChildMember.create_from_entity(child_entity)
            member.children.add(child_member)
            i += 1
        self.assert_equal(len(member.children), n)

    def test_update_terminal(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self.__create_member()
            member.text = self.UPDATED_TEXT
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self.__create_member()
                self.assert_equal(context.text, MyEntity.DEFAULT_TEXT)
                context.update_from_data(data_el)
                self.assert_equal(context.text, self.UPDATED_TEXT)

    def test_update_terminal_in_parent(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self.__create_member()
            member.parent.text = self.UPDATED_TEXT
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self.__create_member()
                self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
                context.update_from_data(data_el)
                self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_update_terminal_in_child(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self.__create_member()
            member_child = iter(member.children).next()
            member_child.text = self.UPDATED_TEXT
            mb_slug = member_child.__name__
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT, STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self.__create_member()
                context_child = context.children[mb_slug]
                self.assert_equal(context_child.text, MyEntity.DEFAULT_TEXT)
                context.update_from_data(data_el)
                self.assert_equal(context_child.text, self.UPDATED_TEXT)

    def test_update_member(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self.__create_member()
            new_parent = MyEntityParent()
            new_parent.text = self.UPDATED_TEXT
            new_parent_member = \
                    MyEntityParentMember.create_from_entity(new_parent)
            member.parent = new_parent_member
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self.__create_member()
                self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
                context.update_from_data(data_el)
                self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_delete_child(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self.__create_member()
            member_child = iter(member.children).next()
            member.children.remove(member_child)
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self.__create_member()
                self.assert_equal(len(context.children), 1)
                context.update_from_data(data_el)
                self.assert_equal(len(context.children), 0)

    def test_delete_grandchild(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self.__create_member()
            member_child = iter(member.children).next()
            member_grandchild = iter(member_child.children).next()
            member_child.children.remove(member_grandchild)
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self.__create_member()
                self.assert_equal(len(iter(context.children).next().children),
                                  1)
                context.update_from_data(data_el)
                self.assert_equal(len(iter(context.children).next().children),
                                  0)

    def test_add_child(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self.__create_member()
            new_child = MyEntityChild()
            new_child_member = \
                    MyEntityChildMember.create_from_entity(new_child)
            member.children.add(new_child_member)
            self.assert_equal(len(member.children), 2)
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT,
                      ):
            with create_object(stage):
                context = self.__create_member()
                self.assert_equal(len(context.children), 1)
                context.update_from_data(data_el)
                self.assert_equal(len(context.children), 2)

    def test_filter_specification_visitor(self):
        coll = get_collection(IMyEntity)
        mb_cls = get_member_class(coll)
        member = self.__create_member()
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

    def _make_data_element_generator(self):
        reg = SimpleDataElementRegistry()
        # We configure the DataElementGenerator to dump all data explicitly.
        repr_config = RepresenterConfiguration()
        repr_config.set_option('mapping',
                               dict(parent=dict(write_as_link=False,
                                                ignore=False),
                                    children=dict(write_as_link=False,
                                                  ignore=False)))
        for cls in (MyEntityMember, MyEntityParentMember,
                    MyEntityChildMember, MyEntityGrandchildMember,
                    get_collection_class(MyEntityChildMember),
                    get_collection_class(MyEntityGrandchildMember)):
            de_cls = reg.create_data_element_class(cls, repr_config)
            reg.set_data_element_class(de_cls)
        gen = DataElementGenerator(reg)
        return gen

    def __create_member(self):
        my_entity = MyEntity()
        my_entity.id = 0
        member = MyEntityMember.create_from_entity(my_entity)
        my_entity_parent = MyEntityParent()
        my_entity_parent.id = 0
        member.parent = \
            MyEntityParentMember.create_from_entity(my_entity_parent)
        my_entity_child = MyEntityChild()
        my_entity_child.id = 0
        child_member = MyEntityChildMember.create_from_entity(my_entity_child)
        member.children.add(child_member)
        my_entity_grandchild = MyEntityGrandchild()
        my_entity_grandchild.id = 0
        child_member.children.add(
            MyEntityGrandchildMember.create_from_entity(my_entity_grandchild))
        coll = get_collection(IMyEntity)
        coll.add(member)
        return member
