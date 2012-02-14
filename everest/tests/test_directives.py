"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Adapted from the ZCML unit tests in BFG.

Created on Jun 17, 2011.
"""

from everest.configuration import Configurator
from everest.entities.aggregates import MemoryAggregateImpl
from everest.entities.interfaces import IAggregate
from everest.entities.interfaces import IEntity
from everest.entities.utils import get_root_aggregate
from everest.mime import CsvMime
from everest.representers.interfaces import IRepresenter
from everest.resources.base import Collection
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IService
from everest.testing import Pep8CompliantTestCase
from everest.tests import testapp as package
from everest.tests.testapp.entities import FooEntity
from everest.tests.testapp.entities import FooEntityAggregate
from everest.tests.testapp.interfaces import IBar
from everest.tests.testapp.interfaces import IFoo
from everest.tests.testapp.resources import FooCollection
from everest.tests.testapp.resources import FooMember
from repoze.bfg.testing import setUp as testing_set_up
from repoze.bfg.testing import tearDown as testing_tear_down
from repoze.bfg.threadlocal import get_current_registry
from everest.interfaces import IRepositoryManager

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

    def test_configure_with_simple_zcml(self):
        # Load the configuration.
        self._config.load_zcml('everest.tests.testapp:configure_simple.zcml')
        reg = self._registry
        # Check adapters.
        ent = FooEntity()
        member = object.__new__(FooMember)
        coll_cls = reg.queryUtility(IFoo, name='collection-class')
        self.assert_is_not_none(coll_cls)
        self.assert_is_not_none(coll_cls.root_name)
        self.assert_is_not_none(coll_cls.title)
        coll = object.__new__(coll_cls)
        agg_cls = reg.queryAdapter(coll, IAggregate,
                                   name='aggregate-class')
        self.assert_is_not_none(agg_cls)
        agg = object.__new__(agg_cls)
        self.__check(reg, member, ent, coll, agg)
        # Check service.
        srvc = reg.queryUtility(IService)
        self.assert_is_not_none(srvc)
        srvc.start()
        self.assert_true(isinstance(srvc.get('foos'), Collection))
        self.assert_is_none(srvc.get(coll_cls))
        self.assert_is_none(srvc.get(IBar))

    def test_configure_with_full_zcml(self):
        reg = self._registry
        # Check adapters.
        ent = FooEntity()
        member = object.__new__(FooMember)
        agg = object.__new__(FooEntityAggregate)
        coll = object.__new__(FooCollection)
        # Make sure no adapters are in the registry.
        self.assert_is_none(reg.queryAdapter(coll, IMemberResource,
                                          name='member-class'))
        self.assert_is_none(reg.queryAdapter(member, ICollectionResource,
                                          name='collection-class'))
        self.assert_is_none(reg.queryAdapter(member, IEntity,
                                          name='entity-class'))
        self.assert_is_none(reg.queryAdapter(coll, IAggregate,
                                          name='aggregate-class'))
        self.assert_is_none(reg.queryAdapter(ent, IMemberResource))
        self.assert_is_none(reg.queryAdapter(agg, ICollectionResource))
        self.assert_is_none(reg.queryAdapter(coll, IRepresenter,
                                          name=CsvMime.mime_string))
        # Load the configuration.
        config = Configurator(registry=reg, package=package)
        config.load_zcml('everest.tests.testapp:configure.zcml')
        self.__check(reg, member, ent, coll, agg)
        self.assert_is_not_none(reg.queryAdapter(coll, IRepresenter,
                                                 name=CsvMime.mime_string))

    def test_custom_memory_aggregate_class(self):
        class MyMemoryAggregate(MemoryAggregateImpl):
            pass
        reg = self._registry
        # Load the configuration.
        config = Configurator(registry=reg)
        config.add_resource(IFoo, FooMember, FooEntity,
                            collection_root_name="foos",
                            aggregate=MyMemoryAggregate)
        repo_mgr = config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize()
        member = object.__new__(FooMember)
        coll_cls = reg.queryAdapter(member, ICollectionResource,
                                    name='collection-class')
        coll = object.__new__(coll_cls)
        agg = get_root_aggregate(coll)
        self.assert_true(isinstance(agg, MyMemoryAggregate))
        entity = FooEntity(id=1)
        agg.add(entity)
        self.assert_true(agg.count() == 1)
        self.assert_true(list(agg.iterator())[0] is entity)
        self.assert_true(agg.get_by_id(1) is entity)
        self.assert_true(agg.get_by_slug('1') is entity)
        agg.remove(entity)
        self.assert_true(agg.count() == 0)

    def __check(self, reg, member, ent, coll, agg):
        for idx, obj in enumerate((member, coll, ent, agg)):
            self.assert_equal(reg.queryAdapter(obj, IMemberResource,
                                              name='member-class'),
                              type(member))
            self.assert_equal(reg.queryAdapter(obj, ICollectionResource,
                                              name='collection-class'),
                              type(coll))
            self.assert_equal(reg.queryAdapter(obj, IEntity,
                                              name='entity-class'),
                              type(ent))
            self.assert_equal(reg.queryAdapter(obj, IAggregate,
                                              name='aggregate-class'),
                              type(agg))
            if idx < 2: # lookup with class only for member/collection.
                self.assert_equal(reg.queryAdapter(type(obj), IMemberResource,
                                                  name='member-class'),
                                  type(member))
                self.assert_equal(reg.queryAdapter(type(obj),
                                                   ICollectionResource,
                                                  name='collection-class'),
                                  type(coll))
                self.assert_equal(reg.queryAdapter(type(obj), IEntity,
                                                   name='entity-class'),
                                  type(ent))
                self.assert_equal(reg.queryAdapter(type(obj), IAggregate,
                                                   name='aggregate-class'),
                                  type(agg))
        # Check instance adapters.
        self.assert_is_not_none(reg.queryAdapter(ent, IMemberResource))
        self.assert_is_not_none(reg.queryAdapter(agg, ICollectionResource))
