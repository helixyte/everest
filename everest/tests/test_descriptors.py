"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2011.
"""

from everest.configuration import Configurator
from everest.db import Session
from everest.db import reset_db_engine
from everest.db import reset_metadata
from everest.db import set_db_engine
from everest.entities.aggregates import MemoryRelationAggregateImpl
from everest.entities.aggregates import MemoryRootAggregateImpl
from everest.entities.aggregates import OrmRelationAggregateImpl
from everest.entities.aggregates import OrmRootAggregateImpl
from everest.entities.aggregates import PersistentStagingContextManager
from everest.entities.aggregates import TransientStagingContextManager
from everest.entities.base import Entity
from everest.entities.interfaces import IRelationAggregateImplementation
from everest.entities.interfaces import IRootAggregateImplementation
from everest.interfaces import IResourceReferenceConverter
from everest.representers.attributes import ResourceAttributeKinds
from everest.representers.attributes import get_resource_class_attributes
from everest.representers.base import DataElementGenerator
from everest.representers.base import RepresenterConfiguration
from everest.representers.base import SimpleDataElementRegistry
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.resources.service import Service
from everest.resources.utils import get_collection
from everest.resources.utils import get_collection_class
from everest.specifications import specification_factory
from everest.staging import STAGING_CONTEXT_MANAGERS
from everest.testing import BaseTestCase
from everest.testing import Pep8CompliantTestCase
from everest.url import ResourceReferenceConverter
from repoze.bfg.interfaces import IRequest
from repoze.bfg.registry import Registry
from repoze.bfg.testing import DummyRequest
from repoze.bfg.testing import setUp as testing_set_up
from repoze.bfg.testing import tearDown as testing_tear_down
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from sqlalchemy.sql.expression import cast
from zope.component import createObject as create_object # pylint: disable=E0611,F0401
from zope.component.interfaces import IFactory # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

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


def create_metadata():
    metadata = MetaData()
    #
    # TABLES
    #
    my_entity_parent_tbl = \
        Table('my_entity_parent', metadata,
              Column('my_entity_parent_id', Integer, primary_key=True),
              Column('text', String),
              )
    # 1:1 MyEntity <=> MyEntityParent
    my_entity_tbl = \
        Table('my_entity', metadata,
              Column('my_entity_id', Integer, primary_key=True),
              Column('text', String),
              Column('number', Integer),
              Column('my_entity_parent_id', Integer,
                     ForeignKey(my_entity_parent_tbl.c.my_entity_parent_id),
                     nullable=False),
              )
    # 1:n MyEntity <-> MyEntityChild
    my_entity_child_tbl = \
        Table('my_entity_child', metadata,
              Column('text', String),
              Column('my_entity_child_id', Integer, primary_key=True),
              Column('my_entity_id', Integer,
                     ForeignKey(my_entity_tbl.c.my_entity_id),
                     nullable=False),
              )
    # n:m MyEntity child <-> MyEntityGrandchild
    my_entity_grandchild_tbl = \
        Table('my_entity_grandchild', metadata,
              Column('text', String),
              Column('my_entity_grandchild_id', Integer, primary_key=True),
              )
    my_entity_child_children_tbl = \
        Table('my_entity_child_children', metadata,
              Column('my_entity_child_id', Integer,
                     ForeignKey(my_entity_child_tbl.c.my_entity_child_id),
                     nullable=False),
              Column('my_entity_grandchild_id', Integer,
                     ForeignKey(
                        my_entity_grandchild_tbl.c.my_entity_grandchild_id),
                     nullable=False)
              )
    #
    # MAPPERS
    #
    def make_slug_hybrid_attr(ent_cls):
        return hybrid_property(ent_cls.slug.fget,
                               expr=lambda cls: cast(cls.id, String))

    mapper(MyEntityParent, my_entity_parent_tbl,
           properties=
            dict(id=synonym('my_entity_parent_id'),
                 child=relationship(MyEntity,
                                    uselist=False,
                                    back_populates='parent'),
                 )
           )
    MyEntityParent.slug = make_slug_hybrid_attr(MyEntityParent)
    mapper(MyEntity, my_entity_tbl,
           properties=
            dict(id=synonym('my_entity_id'),
                 parent=relationship(MyEntityParent,
                                     uselist=False,
                                     back_populates='child'),
                 children=relationship(MyEntityChild,
                                       back_populates='parent',
                                       cascade="all, delete-orphan"),
                 )
           )
    MyEntity.slug = make_slug_hybrid_attr(MyEntity)
    mapper(MyEntityChild, my_entity_child_tbl,
           properties=
            dict(id=synonym('my_entity_child_id'),
                 parent=relationship(MyEntity,
                                     uselist=False,
                                     back_populates='children',
                                     cascade='save-update'
                                     ),
                 children=
                    relationship(MyEntityGrandchild,
                                 secondary=my_entity_child_children_tbl,
                                 back_populates='parent'),
                 ),
           )
    MyEntityChild.slug = make_slug_hybrid_attr(MyEntityChild)
    mapper(MyEntityGrandchild, my_entity_grandchild_tbl,
           properties=
            dict(id=synonym('my_entity_grandchild_id'),
                 parent=relationship(MyEntityChild,
                                     uselist=False,
                                     secondary=my_entity_child_children_tbl,
                                     back_populates='children'),
                 ),
           )
    MyEntityGrandchild.slug = make_slug_hybrid_attr(MyEntityGrandchild)
    return metadata


# Marker interfaces.
# pylint: disable=W0232
class IMyEntityParent(Interface):
    pass


class IMyEntity(Interface):
    pass


class IMyEntityChild(Interface):
    pass


class IMyEntityGrandchild(Interface):
    pass
# pylint: enable=W0232


# Entity classes.
class _MyEntity(Entity):
    DEFAULT_TEXT = 'TEXT'

    def __init__(self, text=None, **kw):
        Entity.__init__(self, **kw)
        if text is None:
            text = self.DEFAULT_TEXT
        self.text = text


class MyEntityParent(_MyEntity):
    def __init__(self, child=None, **kw):
        _MyEntity.__init__(self, **kw)
        self.child = child


class MyEntity(_MyEntity):
    DEFAULT_NUMBER = 1
    def __init__(self, parent=None, children=None, number=None, **kw):
        _MyEntity.__init__(self, **kw)
        self.parent = parent
        if children is None:
            children = []
        self.children = children
        if number is None:
            number = self.DEFAULT_NUMBER
        self.number = number

    def __getitem__(self, name):
        if name == 'children':
            return self.children
        return super(MyEntity, self).__getitem__(name)


class MyEntityChild(_MyEntity):
    def __init__(self, parent=None, children=None, **kw):
        _MyEntity.__init__(self, **kw)
        self.parent = parent
        if children is None:
            children = []
        self.children = children

    def __getitem__(self, name):
        if name == 'children':
            return self.children
        return super(MyEntityChild, self).__getitem__(name)


class MyEntityGrandchild(_MyEntity):
    def __init__(self, parent=None, **kw):
        _MyEntity.__init__(self, **kw)
        self.parent = parent


# Resource classes.
class MyEntityParentMember(Member):
    relation = 'http://test.org/my-entity-parent'
    text = terminal_attribute('text', str)


class MyEntityMember(Member):
    relation = 'http://test.org/my-entity'
    parent = member_attribute('parent', IMyEntityParent)
    children = collection_attribute('children', IMyEntityChild, is_nested=True)
    text = terminal_attribute('text', str)
    number = terminal_attribute('number', int)


class MyEntityChildMember(Member):
    relation = 'http://test.org/my-entity-child'
    children = collection_attribute('children', IMyEntityGrandchild,
                                    is_nested=True)
    text = terminal_attribute('text', str)


class MyEntityGrandchildMember(Member):
    relation = 'http://test.org/my-entity-grandchild'
    text = terminal_attribute('text', str)


class AttributesTestCase(Pep8CompliantTestCase):
    def test_names(self):
        self.assert_equal(
                    get_resource_class_attributes(MyEntityMember).keys(),
                    ['id', 'parent', 'children', 'text', 'number'])

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
        self.assert_equal(attrs[4].name, 'number')
        self.assert_equal(attrs[4].kind, ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attrs[4].entity_name, 'number')
        self.assert_equal(attrs[4].value_type, int)

    def test_inheritance(self):
        class MyEntityDerivedMember(MyEntityMember):
            text = terminal_attribute('text', int)
        attrs = get_resource_class_attributes(MyEntityDerivedMember)
        attr = attrs['text']
        self.assert_equal(attr.kind,
                          ResourceAttributeKinds.TERMINAL)
        self.assert_equal(attr.entity_name, 'text')
        self.assert_equal(attr.value_type, int)


class DescriptorsTestCase(BaseTestCase):
    metadata = None
    _connection = None
    _transaction = None
    _request = None

    UPDATED_TEXT = 'UPDATED TEXT'

    def set_up(self):
        if DescriptorsTestCase.metadata is None:
            setup()
        # Set up outer transaction.
        self._connection = DescriptorsTestCase.metadata.bind.connect()
        self._transaction = self._connection.begin()
        Session.configure(bind=self._connection,
                          extension=None)
        # Set up registry and request.
        reg = Registry('testing')
        config = Configurator(reg)
        reg.registerUtility(# pylint: disable=E1101
                            specification_factory, IFactory, 'specifications')
        reg.registerUtility(# pylint: disable=E1101
                            OrmRootAggregateImpl,
                            IRootAggregateImplementation)
        reg.registerUtility(# pylint: disable=E1101
                            OrmRelationAggregateImpl,
                            IRelationAggregateImplementation)
        reg.registerUtility(# pylint: disable=E1101
                            OrmRootAggregateImpl,
                            IRootAggregateImplementation,
                            STAGING_CONTEXT_MANAGERS.PERSISTENT)
        reg.registerUtility(# pylint: disable=E1101
                            OrmRelationAggregateImpl,
                            IRelationAggregateImplementation,
                            STAGING_CONTEXT_MANAGERS.PERSISTENT)
        reg.registerUtility(# pylint: disable=E1101
                            MemoryRootAggregateImpl,
                            IRootAggregateImplementation,
                            STAGING_CONTEXT_MANAGERS.TRANSIENT)
        reg.registerUtility(# pylint: disable=E1101
                            MemoryRelationAggregateImpl,
                            IRelationAggregateImplementation,
                            STAGING_CONTEXT_MANAGERS.TRANSIENT)
        reg.registerUtility(# pylint: disable=E1101
                            PersistentStagingContextManager,
                            IFactory, STAGING_CONTEXT_MANAGERS.PERSISTENT)
        reg.registerUtility(# pylint: disable=E1101
                            TransientStagingContextManager,
                            IFactory, STAGING_CONTEXT_MANAGERS.TRANSIENT)
        reg.registerAdapter(# pylint: disable=E1101
                            ResourceReferenceConverter,
                            (IRequest,), IResourceReferenceConverter)
        config.add_resource(IMyEntityParent, MyEntityParentMember,
                            MyEntityParent,
                            collection_root_name='my-entity-parents')
        config.add_resource(IMyEntity, MyEntityMember, MyEntity,
                            collection_root_name='my-entities')
        config.add_resource(IMyEntityChild, MyEntityChildMember, MyEntityChild,
                            collection_root_name='my-entity-children')
        config.add_resource(IMyEntityGrandchild, MyEntityGrandchildMember,
                            MyEntityGrandchild,
                            collection_root_name='my-entity-grandchildren')
        self._request = DummyRequest(registry=reg,
                                     host_url="http://everest.org/",
                                     application_url="http://everest.org/")
        testing_set_up(registry=reg, request=self._request)
        # Set up the service.
        with create_object(STAGING_CONTEXT_MANAGERS.PERSISTENT):
            service = Service('service')
            service.add(IMyEntity)
            service.add(IMyEntityParent)
            self._request.root = service

    def tear_down(self):
        Session.remove()
        self._transaction.rollback()
        self._connection.close()
        testing_tear_down()

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
            member = self._create_member()
            member.text = self.UPDATED_TEXT
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self._create_member()
                self.assert_equal(context.text, MyEntity.DEFAULT_TEXT)
                context.update_from_data(data_el)
                self.assert_equal(context.text, self.UPDATED_TEXT)

    def test_update_terminal_in_parent(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self._create_member()
            member.parent.text = self.UPDATED_TEXT
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self._create_member()
                self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
                context.update_from_data(data_el)
                self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_update_terminal_in_child(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self._create_member()
            member_child = iter(member.children).next()
            member_child.text = self.UPDATED_TEXT
            mb_slug = member_child.__name__
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT, STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self._create_member()
                context_child = context.children[mb_slug]
                self.assert_equal(context_child.text, MyEntity.DEFAULT_TEXT)
                context.update_from_data(data_el)
                self.assert_equal(context_child.text, self.UPDATED_TEXT)

    def test_update_member(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self._create_member()
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
                context = self._create_member()
                self.assert_equal(context.parent.text, MyEntity.DEFAULT_TEXT)
                context.update_from_data(data_el)
                self.assert_equal(context.parent.text, self.UPDATED_TEXT)

    def test_delete_child(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self._create_member()
            member_child = iter(member.children).next()
            member.children.remove(member_child)
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self._create_member()
                self.assert_equal(len(context.children), 1)
                context.update_from_data(data_el)
                self.assert_equal(len(context.children), 0)

    def test_delete_grandchild(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self._create_member()
            member_child = iter(member.children).next()
            member_grandchild = iter(member_child.children).next()
            member_child.children.remove(member_grandchild)
            gen = self._make_data_element_generator()
            data_el = gen.run(member)
            del member
        for stage in (STAGING_CONTEXT_MANAGERS.TRANSIENT,
                      STAGING_CONTEXT_MANAGERS.PERSISTENT):
            with create_object(stage):
                context = self._create_member()
                self.assert_equal(len(iter(context.children).next().children),
                                  1)
                context.update_from_data(data_el)
                self.assert_equal(len(iter(context.children).next().children),
                                  0)

    def test_add_child(self):
        with create_object(STAGING_CONTEXT_MANAGERS.TRANSIENT):
            member = self._create_member()
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
                context = self._create_member()
                self.assert_equal(len(context.children), 1)
                context.update_from_data(data_el)
                self.assert_equal(len(context.children), 2)

#    def test_nested_access(self):
#        entity = MyEntity()
#        member = MyEntityMember.create_from_entity(entity)

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

    def _create_member(self):
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
