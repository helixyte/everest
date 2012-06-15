"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 14, 2012.
"""
from everest.entities.base import Entity
from everest.querying.specifications import ConjunctionFilterSpecification
from everest.querying.specifications import ValueEqualToFilterSpecification
from everest.querying.utils import get_filter_specification_factory
from everest.resources.utils import get_root_collection
from everest.testing import ResourceTestCase
from everest.tests.testapp.entities import FooEntity
from everest.tests.testapp.interfaces import IFoo
from everest.tests.testapp.resources import FooCollection
from everest.tests.testapp.resources import FooMember
from everest.tests.testapp_db.testing import create_collection

__docformat__ = 'reStructuredText en'
__all__ = ['ResourcesFilteringTestCase',
           'ResourcesTestCase',
           ]


class ResourcesTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp'
    config_file_name = 'configure.zcml'

    def test_no_relation_raises_error(self):
        foo = FooEntity()
        self.assert_raises(ValueError, MemberWithoutRelation, foo)

    def test_wrong_entity_raises_error(self):
        ent = UnregisteredEntity()
        self.assert_raises(ValueError, FooMember, ent)

    def test_member_delete(self):
        coll = get_root_collection(IFoo)
        foo = FooEntity(id=0)
        mb = coll.create_member(foo)
        self.assert_true(mb in coll)
        mb.delete()
        self.assert_false(mb in coll)

    def test__getitem__with_invalid_key_raises_error(self):
        foo = FooEntity(id=0)
        mb = FooMember.create_from_entity(foo)
        self.assert_raises(KeyError, mb.__getitem__, 'x')

    def test_equal(self):
        foo0 = FooEntity(id=0)
        mb0 = FooMember.create_from_entity(foo0)
        foo1 = FooEntity(id=1)
        mb1 = FooMember.create_from_entity(foo1)
        self.assert_true(mb0 == mb0)
        self.assert_true(mb0 != mb1)

    def test_no_title_raises_error(self):
        with self.assert_raises(ValueError) as cm:
            CollectionWithoutTitle(None)
        exc_msg = 'Collection must have a title.'
        self.assert_equal(cm.exception.message, exc_msg)


class ResourcesFilteringTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_filter_nested(self):
        coll = create_collection()
        children = iter(coll).next().children
        spec_fac = get_filter_specification_factory()
        spec = spec_fac.create_equal_to('id', 1)
        children.filter = spec
        self.assert_true(isinstance(children.filter,
                                    ValueEqualToFilterSpecification))
        self.assert_equal(len(children), 0)

    def test_filter_not_nested(self):
        # The grand children are not nested, so the filter spec has to be
        # a ConjunctionFilterSpecification.
        coll = create_collection()
        grand_children = iter(iter(coll).next().children).next().children
        spec_fac = get_filter_specification_factory()
        spec = spec_fac.create_equal_to('id', 1)
        grand_children.filter = spec
        self.assert_equal(len(grand_children), 0)
        self.assert_true(isinstance(grand_children.filter,
                                    ConjunctionFilterSpecification))
        grand_children.filter = None
        self.assert_equal(len(grand_children), 1)
        self.assert_true(isinstance(grand_children.filter,
                                    ValueEqualToFilterSpecification))

    def test_filter_backref_only_raises_error(self):
        # We can not use resource attributes that do not have a corresponding
        # entity attribute (such as backref only collections) for filtering.
        coll = create_collection()
        children = iter(coll).next().children
        grandchildren = iter(children).next().children
        grandchild = iter(grandchildren).next()
        spec_fac = get_filter_specification_factory()
        spec = spec_fac.create_equal_to('backref_only_children', grandchild)
        with self.assert_raises(ValueError) as cm:
            children.filter = spec
        exc_msg = 'does not have a corresponding entity attribute.'
        self.assert_true(cm.exception.message.endswith(exc_msg))


class UnregisteredEntity(Entity):
    pass


class MemberWithoutRelation(FooMember):
    relation = None


class CollectionWithoutTitle(FooCollection):
    title = None
