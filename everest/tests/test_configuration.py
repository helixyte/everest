"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 18, 2012.
"""
from everest.configuration import Configurator
from everest.entities.aggregates import MemoryAggregate
from everest.interfaces import IRepositoryManager
from everest.interfaces import IResourceUrlConverter
from everest.mime import CsvMime
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationFactory
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.repository import REPOSITORIES
from everest.representers.csv import CsvResourceRepresenter
from everest.representers.interfaces import IRepresenterRegistry
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IService
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_repository
from everest.testing import Pep8CompliantTestCase
from everest.tests import testapp as package
from everest.tests.testapp.entities import FooEntity
from everest.tests.testapp.interfaces import IFoo
from everest.tests.testapp.resources import FooMember
from pyramid.testing import DummyRequest
from pyramid.testing import setUp as testing_set_up
from pyramid.testing import tearDown as testing_tear_down
from pyramid.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['ConfiguratorTestCase',
           ]

class ConfiguratorTestCase(Pep8CompliantTestCase):

    def set_up(self):
        testing_set_up()
        reg = self._registry = get_current_registry()
        self._config = Configurator(registry=reg, package=package)
        self._config.setup_registry()

    def tear_down(self):
        testing_tear_down()

    def test_registry_setup(self):
        reg = self._registry
        self.assert_is_not_none(reg.queryUtility(IRepositoryManager))
        self.assert_is_not_none(reg.queryUtility(IFilterSpecificationFactory))
        self.assert_is_not_none(reg.queryUtility(IOrderSpecificationFactory))
        self.assert_is_not_none(reg.queryUtility(IService))
        self.assert_is_not_none(reg.queryUtility(IFilterSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.CQL))
        self.assert_is_not_none(reg.queryUtility(IFilterSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.SQL))
        self.assert_is_not_none(reg.queryUtility(IFilterSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.EVAL))
        self.assert_is_not_none(reg.queryUtility(IOrderSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.CQL))
        self.assert_is_not_none(reg.queryUtility(IOrderSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.SQL))
        self.assert_is_not_none(reg.queryUtility(IOrderSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.EVAL))
        reg = self._registry
        req = DummyRequest()
        self.assert_is_not_none(reg.queryAdapter(req, IResourceUrlConverter))

    def test_add_resource(self):
        self.assert_raises(ValueError, self._config.add_resource,
                           NotAnInterface, FooMember, FooEntity, expose=False)
        self.assert_raises(ValueError, self._config.add_resource,
                           IFoo, NotAMember, FooEntity, expose=False)
        self.assert_raises(ValueError, self._config.add_resource,
                           IFoo, FooMember, NotAnEntity, expose=False)
        self.assert_raises(ValueError, self._config.add_resource,
                           IFoo, FooMember, FooEntity, expose=False,
                           collection=NotACollection)
        self.assert_raises(ValueError, self._config.add_resource,
                           IFoo, UnrelatedMember, FooEntity, expose=False)
        self.assert_raises(ValueError, self._config.add_resource,
                           IFoo, FooMember, FooEntity, expose=False,
                           repository='UNKNOWN')
        self.assert_raises(ValueError, self._config.add_resource,
                           IFoo, FooMember, FooEntity, expose=True)

    def test_add_resource_with_collection_title(self):
        title = 'myfoos'
        self._config.add_resource(IFoo, FooMember, FooEntity, expose=False,
                                  collection_title=title)
        self.assert_equal(get_collection_class(IFoo).title, title)

    def test_add_resource_with_root_name(self):
        root_name = 'myfoos'
        self._config.add_resource(IFoo, FooMember, FooEntity, expose=True,
                                  collection_root_name=root_name)
        self.assert_equal(get_collection_class(IFoo).root_name, root_name)

    def test_add_resource_with_orm_repo(self):
        self._config.add_resource(IFoo, FooMember, FooEntity, expose=False,
                                  repository=REPOSITORIES.ORM)
        reg = self._registry
        repo_mgr = reg.queryUtility(IRepositoryManager)
        self.assert_is_not_none(repo_mgr.get(REPOSITORIES.ORM))

    def test_have_memory_repo(self):
        reg = self._registry
        repo_mgr = reg.queryUtility(IRepositoryManager)
        self.assert_is_not_none(repo_mgr.get(REPOSITORIES.MEMORY))

    def test_add_resource_with_filesystem_repo(self):
        self._config.add_resource(IFoo, FooMember, FooEntity, expose=False,
                                  repository=REPOSITORIES.FILE_SYSTEM)
        reg = self._registry
        repo_mgr = reg.queryUtility(IRepositoryManager)
        self.assert_is_not_none(repo_mgr.get(REPOSITORIES.FILE_SYSTEM))

    def test_add_representer(self):
        self.assert_raises(ValueError, self._config.add_representer)
        self.assert_raises(ValueError, self._config.add_representer,
                           content_type=CsvMime,
                           representer_class=CsvResourceRepresenter)

    def test_add_representer_with_representer_class(self):
        self._config.add_representer(representer_class=MyRepresenterClass)
        rpr_reg = self._registry.queryUtility(IRepresenterRegistry)
        self.assert_true(rpr_reg.is_registered_representer_class(
                                                        MyRepresenterClass))

    def test_add_resource_representer(self):
        self.assert_raises(ValueError, self._config.add_resource_representer,
                           NotAMember, CsvMime)

    def test_custom_repository(self):
        class MyMemoryAggregate(MemoryAggregate):
            pass
        reg = self._registry
        config = Configurator(registry=reg)
        config.add_memory_repository('test',
                                     aggregate_class=MyMemoryAggregate)
        repo_mgr = config.get_registered_utility(IRepositoryManager)
        repo = repo_mgr.get('test')
        config.add_resource(IFoo, FooMember, FooEntity,
                            collection_root_name="foos",
                            repository='test')
        member = object.__new__(FooMember)
        coll_cls = reg.queryAdapter(member, ICollectionResource,
                                    name='collection-class')
        self.assert_raises(RuntimeError, repo.new, coll_cls)
        repo.initialize()
        repo = get_repository('test')
        coll = repo.new(coll_cls)
        agg = coll.get_aggregate()
        self.assert_true(isinstance(agg, MyMemoryAggregate))
        entity = FooEntity(id=1)
        agg.add(entity)
        self.assert_true(agg.count() == 1)
        self.assert_equal(list(agg.iterator())[0].id, entity.id)
        self.assert_equal(agg.get_by_id(1).id, entity.id)
        self.assert_equal(agg.get_by_slug('1').slug, entity.slug)
        agg.remove(entity)
        self.assert_true(agg.count() == 0)


class Dummy(object):
    pass


NotAMember = Dummy
NotACollection = Dummy
NotAnInterface = Dummy
NotAnEntity = Dummy


class UnrelatedMember(FooMember):
    relation = None


class MyRepresenterClass(CsvResourceRepresenter):
    pass
