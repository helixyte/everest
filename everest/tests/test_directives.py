"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Adapted from the ZCML unit tests in BFG.

Created on Jun 17, 2011.
"""

from everest.configuration import Configurator
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.testing import Pep8CompliantTestCase
from everest.tests import testapp as package
from everest.tests.testapp.interfaces import IFoo
from everest.tests.testapp.models import FooEntity
from everest.tests.testapp.models import FooEntityAggregate
from everest.tests.testapp.resources import FooCollection
from everest.tests.testapp.resources import FooMember
from repoze.bfg.testing import setUp as testing_set_up
from repoze.bfg.testing import tearDown as testing_tear_down
from repoze.bfg.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['DirectivesTestCase',
           ]


class DirectivesTestCase(Pep8CompliantTestCase):

    def set_up(self):
        testing_set_up()

    def tear_down(self):
        testing_tear_down()

    def test_configure_with_simple_zcml(self):
        reg = get_current_registry()
        # Load the configuration.
        config = Configurator(reg, package=package)
        config.load_zcml('everest.tests.testapp:configure_simple.zcml')
        #
        ent = FooEntity()
        member = object.__new__(FooMember)
        coll_cls = reg.queryUtility(IFoo, 'collection-class')
        self.assert_true(not coll_cls.root_name is None)
        self.assert_true(not coll_cls.title is None)
        self.assert_true(not coll_cls is None)
        coll = object.__new__(coll_cls)
        agg_cls = reg.queryAdapter(coll, IAggregate)
        self.assert_true(not agg_cls is None)
        agg = object.__new__(agg_cls)
        self.__check(reg, member, ent, coll, agg)

    def test_configure_with_full_zcml(self):
        ent = FooEntity()
        member = object.__new__(FooMember)
        agg = object.__new__(FooEntityAggregate)
        coll = object.__new__(FooCollection)
        reg = get_current_registry()
        # Make sure no adapters are in the registry.
        self.assert_true(reg.queryAdapter(member, ICollectionResource,
                                          'member-class') is None)
        self.assert_true(reg.queryAdapter(coll, IMemberResource,
                                          'collection-class') is None)
        self.assert_true(reg.queryAdapter(member, IEntity) is None)
        self.assert_true(reg.queryAdapter(coll, IAggregate) is None)
        self.assert_true(reg.queryAdapter(ent, IMemberResource) is None)
        self.assert_true(reg.queryAdapter(agg, ICollectionResource) is None)
        # Load the configuration.
        config = Configurator(reg, package=package)
        config.load_zcml('everest.tests.testapp:configure.zcml')
        self.__check(reg, member, ent, coll, agg)

    def __check(self, reg, member, ent, coll, agg):
        # Check if adapters were registered correctly.
        self.assert_true(reg.queryAdapter(coll, IMemberResource,
                                          'member-class')
                         is FooMember)
        self.assert_true(reg.queryAdapter(member, ICollectionResource,
                                          'collection-class')
                         is type(coll))
        self.assert_true(reg.queryAdapter(member, IEntity) is FooEntity)
        self.assert_true(reg.queryAdapter(coll, IAggregate)
                         is type(agg))
        self.assert_true(isinstance(reg.queryAdapter(ent, IMemberResource),
                                    FooMember))
        self.assert_true(isinstance(reg.queryAdapter(agg, ICollectionResource),
                                    type(coll)))
        # Check class lookup for member and collection adapters as well.
        self.assert_true(reg.queryAdapter(type(coll), IMemberResource,
                                          'member-class')
                         is FooMember)
        self.assert_true(reg.queryAdapter(FooMember, ICollectionResource,
                                          'collection-class')
                         is type(coll))
        self.assert_true(reg.queryAdapter(FooMember, IEntity)
                         is FooEntity)
        self.assert_true(reg.queryAdapter(type(coll), IAggregate)
                         is type(agg))
        # Check utilities for interface -> class translation.
        self.assert_true(reg.queryUtility(IFoo, 'member-class')
                         is FooMember)
        self.assert_true(reg.queryUtility(IFoo, 'collection-class')
                         is type(coll))
