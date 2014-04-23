"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Adapted from the ZCML unit tests in BFG.

Created on Jun 17, 2011.
"""
from everest.configuration import Configurator
from everest.entities.interfaces import IEntity
from everest.repositories.interfaces import IRepositoryManager
from everest.mime import CsvMime
from everest.representers.base import Representer
from everest.representers.interfaces import IRepresenter
from everest.representers.utils import as_representer
from everest.resources.base import Collection
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IService
from everest.testing import Pep8CompliantTestCase
from everest.tests import simple_app as package
from everest.tests.simple_app.entities import FooEntity
from everest.tests.simple_app.interfaces import IBar
from everest.tests.simple_app.interfaces import IFoo
from everest.tests.simple_app.resources import FooCollection
from everest.tests.simple_app.resources import FooMember
from pyramid.testing import setUp as set_up_testing
from pyramid.testing import tearDown as tear_down_testing
from pyramid.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['DirectivesTestCase',
           ]


class DirectivesTestCase(Pep8CompliantTestCase):

    def set_up(self):
        set_up_testing()
        reg = self._registry = get_current_registry()
        self._config = Configurator(registry=reg, package=package)
        self._config.setup_registry()
        repo_mgr = self._config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize_all()

    def tear_down(self):
        tear_down_testing()

    def test_configure_with_simple_zcml(self):
        # Load the configuration.
        self._config.load_zcml('everest.tests.simple_app:configure_simple.zcml')
        reg = self._registry
        # Check adapters.
        ent = FooEntity()
        member = object.__new__(FooMember)
        coll_cls = reg.queryUtility(IFoo, name='collection-class')
        self.assert_is_not_none(coll_cls)
        self.assert_is_not_none(coll_cls.root_name)
        self.assert_is_not_none(coll_cls.title)
        coll = object.__new__(coll_cls)
        self.__check(reg, member, ent, coll)
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
        coll = object.__new__(FooCollection)
        # Make sure no adapters are in the registry.
        self.assert_is_none(reg.queryAdapter(coll, IMemberResource,
                                          name='member-class'))
        self.assert_is_none(reg.queryAdapter(member, ICollectionResource,
                                          name='collection-class'))
        self.assert_is_none(reg.queryAdapter(member, IEntity,
                                          name='entity-class'))
        self.assert_is_none(reg.queryAdapter(ent, IMemberResource))
        self.assert_is_none(reg.queryAdapter(coll, IRepresenter,
                                          name=CsvMime.mime_type_string))
        # Load the configuration.
        config = Configurator(registry=reg, package=package)
        config.load_zcml('everest.tests.simple_app:configure.zcml')
        self.__check(reg, member, ent, coll)
        rpr = as_representer(coll, CsvMime)
        self.assert_true(isinstance(rpr, Representer))

    def test_configure_with_custom_repo_zcml(self):
        repo_mgr = self._registry.queryUtility(IRepositoryManager)
        self.assert_is_none(repo_mgr.get('CUSTOM_MEMORY'))
        self.assert_is_none(repo_mgr.get('CUSTOM_FILESYSTEM'))
        self.assert_is_none(repo_mgr.get('CUSTOM_RDB'))
        self._config.load_zcml('everest.tests.simple_app:configure_repos.zcml')
        self.assert_is_not_none(repo_mgr.get('CUSTOM_MEMORY'))
        self.assert_is_not_none(repo_mgr.get('CUSTOM_FILESYSTEM'))
        self.assert_is_not_none(repo_mgr.get('CUSTOM_RDB'))

    def __check(self, reg, member, ent, coll):
        for idx, obj in enumerate((member, coll, ent)):
            self.assert_equal(reg.queryAdapter(obj, IMemberResource,
                                              name='member-class'),
                              type(member))
            self.assert_equal(reg.queryAdapter(obj, ICollectionResource,
                                              name='collection-class'),
                              type(coll))
            self.assert_equal(reg.queryAdapter(obj, IEntity,
                                              name='entity-class'),
                              type(ent))
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
        # Check instance adapters.
        self.assert_is_not_none(reg.queryAdapter(ent, IMemberResource))
