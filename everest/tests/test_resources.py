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
from everest.tests.complete_app.testing import create_collection
from everest.tests.simple_app.entities import FooEntity
from everest.tests.simple_app.interfaces import IFoo
from everest.tests.simple_app.resources import FooCollection
from everest.tests.simple_app.resources import FooMember
from mock import patch

__docformat__ = 'reStructuredText en'
__all__ = ['ResourcesFilteringTestCase',
           'ResourcesTestCase',
           ]


class ResourcesTestCase(ResourceTestCase):
    package_name = 'everest.tests.simple_app'
    config_file_name = 'configure.zcml'

    def test_no_relation_raises_error(self):
        foo = FooEntity()
        self.assert_raises(ValueError, MemberWithoutRelation, foo)

    def test_wrong_entity_raises_error(self):
        ent = UnregisteredEntity()
        self.assert_raises(ValueError, FooMember, ent)

    def test_member_name(self):
        coll = get_root_collection(IFoo)
        foo = FooEntity(id=0)
        mb = coll.create_member(foo)
        self.assert_equal(mb.__name__, '0')
        mb.__name__ = 'foo'
        self.assert_equal(mb.__name__, 'foo')

    def test_member_delete(self):
        coll = get_root_collection(IFoo)
        foo = FooEntity(id=0)
        mb = coll.create_member(foo)
        self.assert_true(mb in coll)
        coll.remove(mb)
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
        self.assert_equal(str(cm.exception), exc_msg)

    def test_str(self):
        coll = get_root_collection(IFoo)
        coll_str = str(coll)
        self.assert_true(coll_str.startswith('<FooCollection'))


#class RelatedResourcesTestCase(ResourceTestCase):
#    package_name = 'everest.tests.complete_app'
#    config_file_name = 'configure_no_rdb.zcml'
#
#    def test_delete_related_member(self):
#        coll = create_collection()
#        mb = coll['0']
#        parent = mb.parent
#        parent.remove(mb)


class ResourcesFilteringTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_filter_nested(self):
        coll = create_collection()
        children = coll['1'].children
        spec_fac = get_filter_specification_factory()
        spec = spec_fac.create_equal_to('id', 0)
        children.filter = spec
        self.assert_true(isinstance(children.filter,
                                    ConjunctionFilterSpecification))
        self.assert_equal(len(children), 0)

    def test_filter_not_nested(self):
        # The grand children are not nested, so the filter spec has to be
        # a ConjunctionFilterSpecification.
        coll = create_collection()
        grand_children = coll['0'].children['0'].children
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
        children = next(iter(coll)).children
        grandchildren = next(iter(children)).children
        grandchild = next(iter(grandchildren))
        spec_fac = get_filter_specification_factory()
        spec = spec_fac.create_equal_to('children', grandchild)
        with patch('%s.resources.MyEntityChildMember.children.entity_attr'
                   % self.package_name, None):
            with self.assert_raises(ValueError) as cm:
                children.filter = spec
        exc_msg = 'does not have a corresponding entity attribute.'
        self.assert_true(str(cm.exception).endswith(exc_msg))


class UnregisteredEntity(Entity):
    pass


class MemberWithoutRelation(FooMember):
    relation = None


class CollectionWithoutTitle(FooCollection):
    title = None
