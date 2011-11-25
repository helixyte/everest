"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Adapted from the ZCML unit tests in BFG.

Created on Jun 17, 2011.
"""

from everest.configuration import Configurator
from everest.entities.aggregates import MemoryRootAggregateImpl
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.entities.interfaces import IRelationAggregateImplementation
from everest.entities.interfaces import IRootAggregateImplementation
from everest.entities.utils import get_aggregate
from everest.filtering import IFilterSpecificationBuilder
from everest.filtering import IFilterSpecificationDirector
from everest.interfaces import IResourceUrlConverter
from everest.mime import CsvMime
from everest.ordering import IOrderSpecificationBuilder
from everest.ordering import IOrderSpecificationDirector
from everest.representers.interfaces import IRepresenter
from everest.resources.base import Collection
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IService
from everest.specifications import IFilterSpecificationFactory
from everest.specifications import IOrderSpecificationFactory
from everest.testing import Pep8CompliantTestCase
from everest.tests import testapp as package
from everest.tests.testapp.entities import FooEntity
from everest.tests.testapp.entities import FooEntityAggregate
from everest.tests.testapp.interfaces import IBar
from everest.tests.testapp.interfaces import IFoo
from everest.tests.testapp.resources import FooCollection
from everest.tests.testapp.resources import FooMember
from everest.visitors import ICqlFilterSpecificationVisitor
from everest.visitors import ICqlOrderSpecificationVisitor
from everest.visitors import IQueryFilterSpecificationVisitor
from repoze.bfg.testing import DummyRequest
from repoze.bfg.testing import setUp as testing_set_up
from repoze.bfg.testing import tearDown as testing_tear_down
from repoze.bfg.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['DirectivesTestCase',
           ]


class DirectivesTestCase(Pep8CompliantTestCase):
    _config = None
    _registry = None

    def set_up(self):
        testing_set_up()
        reg = self._registry = get_current_registry()
        self._config = Configurator(registry=reg, package=package)
        self._config.setup_registry()

    def tear_down(self):
        testing_tear_down()

    def test_registry_setup(self):
        reg = self._registry
        self.assert_false(reg.queryUtility(IService) is None)
        self.assert_false(reg.queryUtility(IFilterSpecificationFactory)
                          is None)
        self.assert_false(reg.queryUtility(IFilterSpecificationBuilder)
                          is None)
        self.assert_false(reg.queryUtility(IFilterSpecificationDirector)
                          is None)
        self.assert_false(reg.queryUtility(ICqlFilterSpecificationVisitor)
                          is None)
        self.assert_false(reg.queryUtility(IQueryFilterSpecificationVisitor)
                          is None)
        self.assert_false(reg.queryUtility(IOrderSpecificationFactory)
                          is None)
        self.assert_false(reg.queryUtility(IOrderSpecificationBuilder)
                          is None)
        self.assert_false(reg.queryUtility(IOrderSpecificationDirector)
                          is None)
        self.assert_false(reg.queryUtility(ICqlOrderSpecificationVisitor)
                          is None)
        self.assert_false(reg.queryUtility(IRootAggregateImplementation)
                          is None)
        self.assert_false(reg.queryUtility(IRelationAggregateImplementation)
                          is None)
        req = DummyRequest()
        self.assert_false(reg.queryAdapter(req, IResourceUrlConverter) is None)

    def test_configure_with_simple_zcml(self):
        # Load the configuration.
        self._config.load_zcml('everest.tests.testapp:configure_simple.zcml')
        reg = self._registry
        # Check adapters.
        ent = FooEntity()
        member = object.__new__(FooMember)
        coll_cls = reg.queryUtility(IFoo, 'collection-class')
        self.assert_true(not coll_cls is None)
        self.assert_true(not coll_cls.root_name is None)
        self.assert_true(not coll_cls.title is None)
        coll = object.__new__(coll_cls)
        agg_cls = reg.queryAdapter(coll, IAggregate)
        self.assert_true(not agg_cls is None)
        agg = object.__new__(agg_cls)
        self.__check(reg, member, ent, coll, agg)
        # Check service.
        srvc = reg.queryUtility(IService)
        self.assert_true(not srvc is None)
        srvc.start()
        self.assert_true(isinstance(srvc.get('foos'), Collection))
        self.assert_true(isinstance(srvc.get(coll_cls), Collection))
        self.assert_true(srvc.get(IBar) is None)

    def test_configure_with_full_zcml(self):
        reg = self._registry
        # Check adapters.
        ent = FooEntity()
        member = object.__new__(FooMember)
        agg = object.__new__(FooEntityAggregate)
        coll = object.__new__(FooCollection)
        # Make sure no adapters are in the registry.
        self.assert_true(reg.queryAdapter(member, ICollectionResource,
                                          'member-class') is None)
        self.assert_true(reg.queryAdapter(coll, IMemberResource,
                                          'collection-class') is None)
        self.assert_true(reg.queryAdapter(member, IEntity) is None)
        self.assert_true(reg.queryAdapter(coll, IAggregate) is None)
        self.assert_true(reg.queryAdapter(ent, IMemberResource) is None)
        self.assert_true(reg.queryAdapter(agg, ICollectionResource) is None)
        self.assert_true(
                reg.queryAdapter(coll, IRepresenter, CsvMime.mime_string)
                is None)
        # Load the configuration.
        config = Configurator(registry=reg, package=package)
        config.load_zcml('everest.tests.testapp:configure.zcml')
        self.__check(reg, member, ent, coll, agg)
        self.assert_false(
                reg.queryAdapter(coll, IRepresenter, CsvMime.mime_string)
                is None)

    def test_custom_memory_aggregate_class(self):
        class MyMemoryAggregate(MemoryRootAggregateImpl):
            pass
        reg = self._registry
        # Load the configuration.
        config = Configurator(registry=reg)
        config.add_resource(IFoo, FooMember, FooEntity,
                            collection_root_name="foos",
                            aggregate=MyMemoryAggregate)
        member = object.__new__(FooMember)
        coll_cls = reg.queryAdapter(member, ICollectionResource,
                                    'collection-class')
        coll = object.__new__(coll_cls)
        agg = get_aggregate(coll)
        self.assert_true(isinstance(agg, MyMemoryAggregate))
        entity = object.__new__(FooEntity)
        entity.id = 1
        agg.add(entity)
        self.assert_true(agg.count() == 1)
        self.assert_true(list(agg.iterator())[0] is entity)
        self.assert_true(agg.get_by_id(1) is entity)
        self.assert_true(agg.get_by_slug('1') is entity)
        agg.remove(entity)
        self.assert_true(agg.count() == 0)

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
