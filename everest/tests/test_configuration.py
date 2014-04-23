"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 18, 2012.
"""
from pyramid.testing import DummyRequest
import pytest

from everest.configuration import Configurator
from everest.interfaces import IResourceUrlConverter
from everest.mime import CsvMime
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationFactory
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.repositories.constants import REPOSITORY_TYPES
from everest.repositories.interfaces import IRepositoryManager
from everest.repositories.memory import Aggregate
from everest.representers.csv import CsvResourceRepresenter
from everest.representers.interfaces import IRepresenterRegistry
from everest.resources.interfaces import IService
from everest.resources.utils import get_collection_class
from everest.tests.simple_app.entities import FooEntity
from everest.tests.simple_app.interfaces import IFoo
from everest.tests.simple_app.resources import FooMember


__docformat__ = 'reStructuredText en'
__all__ = ['TestConfigurator',
           ]


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


class TestConfigurator(object):
    def test_registry_setup(self, simple_config):
        reg = simple_config.registry
        assert not reg.queryUtility(IRepositoryManager) is None
        assert not reg.queryUtility(IFilterSpecificationFactory) is None
        assert not reg.queryUtility(IOrderSpecificationFactory) is None
        assert not reg.queryUtility(IService) is None
        assert not reg.queryUtility(IFilterSpecificationVisitor,
                                    name=EXPRESSION_KINDS.CQL) is None
        assert not reg.queryUtility(IFilterSpecificationVisitor,
                                    name=EXPRESSION_KINDS.SQL) is None
        assert not reg.queryUtility(IFilterSpecificationVisitor,
                                    name=EXPRESSION_KINDS.EVAL) is None
        assert not reg.queryUtility(IOrderSpecificationVisitor,
                                    name=EXPRESSION_KINDS.CQL) is None
        assert not reg.queryUtility(IOrderSpecificationVisitor,
                                    name=EXPRESSION_KINDS.SQL) is None
        assert not reg.queryUtility(IOrderSpecificationVisitor,
                                    name=EXPRESSION_KINDS.EVAL) is None
        req = DummyRequest()
        assert not reg.queryAdapter(req, IResourceUrlConverter) is None

    @pytest.mark.parametrize('args,options',
                             [((NotAnInterface, FooMember, FooEntity),
                               dict(expose=False)),
                              ((IFoo, NotAMember, FooEntity),
                               dict(expose=False)),
                              ((IFoo, FooMember, NotAnEntity),
                               dict(expose=False)),
                              ((IFoo, FooMember, FooEntity),
                               dict(expose=False, collection=NotACollection)),
                              ((IFoo, UnrelatedMember, FooEntity),
                               dict(expose=False)),
                              ((IFoo, FooMember, FooEntity),
                               dict(expose=False, repository='UNKNOWN')),
                              ((IFoo, FooMember, FooEntity),
                               dict(expose=True)),
                              ]
                             )
    def test_add_resource(self, simple_config, args, options):
        with pytest.raises(ValueError):
            simple_config.add_resource(*args, **options)

    @pytest.mark.parametrize('title', ['myfoos'])
    def test_add_resource_with_collection_title(self, simple_config, title):
        simple_config.add_resource(IFoo, FooMember, FooEntity, expose=False,
                                   collection_title=title)
        assert get_collection_class(IFoo).title == title

    @pytest.mark.parametrize('root_name', ['myfoos'])
    def test_add_resource_with_root_name(self, simple_config, root_name):
        simple_config.add_resource(IFoo, FooMember, FooEntity, expose=True,
                                   collection_root_name=root_name)
        assert get_collection_class(IFoo).root_name == root_name

    def test_add_resource_with_rdb_repo(self, simple_config):
        simple_config.add_resource(IFoo, FooMember, FooEntity, expose=False,
                                   repository=REPOSITORY_TYPES.RDB)
        reg = simple_config.registry
        repo_mgr = reg.queryUtility(IRepositoryManager)
        assert not repo_mgr.get(REPOSITORY_TYPES.RDB) is None

    def test_have_memory_repo(self, simple_config):
        reg = simple_config.registry
        repo_mgr = reg.queryUtility(IRepositoryManager)
        assert not repo_mgr.get(REPOSITORY_TYPES.MEMORY) is None

    def test_add_resource_with_filesystem_repo(self, simple_config):
        simple_config.add_resource(IFoo, FooMember, FooEntity, expose=False,
                                  repository=REPOSITORY_TYPES.FILE_SYSTEM)
        reg = simple_config.registry
        repo_mgr = reg.queryUtility(IRepositoryManager)
        assert not repo_mgr.get(REPOSITORY_TYPES.FILE_SYSTEM) is None

    def test_add_representer(self, simple_config):
        with pytest.raises(ValueError):
            simple_config.add_representer()
        with pytest.raises(ValueError):
            simple_config.add_representer(
                                    content_type=CsvMime,
                                    representer_class=CsvResourceRepresenter)

    def test_add_representer_with_representer_class(self, simple_config):
        simple_config.add_representer(representer_class=MyRepresenterClass)
        reg = simple_config.registry
        rpr_reg = reg.queryUtility(IRepresenterRegistry)
        assert rpr_reg.is_registered_representer_class(MyRepresenterClass)

    def test_add_resource_representer(self, simple_config):
        with pytest.raises(ValueError):
            simple_config.add_resource_representer(NotAMember, CsvMime)

    def test_custom_repository(self, simple_config):
        class MyMemoryAggregate(Aggregate):
            pass
        reg = simple_config.registry
        config = Configurator(registry=reg)
        config.add_memory_repository('test',
                                     aggregate_class=MyMemoryAggregate)
        repo_mgr = config.get_registered_utility(IRepositoryManager)
        repo = repo_mgr.get('test')
        config.add_resource(IFoo, FooMember, FooEntity,
                            collection_root_name="foos",
                            repository='test')
        with pytest.raises(RuntimeError):
            repo.get_collection(IFoo)
        with pytest.raises(RuntimeError):
            repo.get_aggregate(IFoo)
        repo.initialize()
        coll = repo.get_collection(IFoo)
        agg = coll.get_aggregate()
        assert isinstance(agg, MyMemoryAggregate)
        entity = FooEntity(id=1)
        agg.add(entity)
        assert agg.count() == 1
        assert list(agg.iterator())[0].id == entity.id
        assert agg.get_by_id(1).id == entity.id
        assert agg.get_by_slug('1').slug == entity.slug
        agg.remove(entity)
        assert agg.count() == 0
