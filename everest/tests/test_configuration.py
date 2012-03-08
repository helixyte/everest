"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 18, 2012.
"""

from everest.configuration import Configurator
from everest.interfaces import IRepositoryManager
from everest.interfaces import IResourceUrlConverter
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.interfaces import IFilterSpecificationBuilder
from everest.querying.interfaces import IFilterSpecificationDirector
from everest.querying.interfaces import IFilterSpecificationFactory
from everest.querying.interfaces import IFilterSpecificationVisitor
from everest.querying.interfaces import IOrderSpecificationBuilder
from everest.querying.interfaces import IOrderSpecificationDirector
from everest.querying.interfaces import IOrderSpecificationFactory
from everest.querying.interfaces import IOrderSpecificationVisitor
from everest.resources.interfaces import IService
from everest.testing import Pep8CompliantTestCase
from everest.tests import testapp as package
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
        self.assert_is_not_none(reg.queryUtility(IFilterSpecificationBuilder))
        self.assert_is_not_none(reg.queryUtility(IFilterSpecificationDirector))
        self.assert_is_not_none(reg.queryUtility(IFilterSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.CQL))
        self.assert_is_not_none(reg.queryUtility(IFilterSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.SQL))
        self.assert_is_not_none(reg.queryUtility(IFilterSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.EVAL))
        self.assert_is_not_none(reg.queryUtility(IOrderSpecificationBuilder))
        self.assert_is_not_none(reg.queryUtility(IOrderSpecificationDirector))
        self.assert_is_not_none(reg.queryUtility(IOrderSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.CQL))
        self.assert_is_not_none(reg.queryUtility(IOrderSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.SQL))
        self.assert_is_not_none(reg.queryUtility(IOrderSpecificationVisitor,
                                                 name=EXPRESSION_KINDS.EVAL))
        reg = self._registry
        req = DummyRequest()
        self.assert_is_not_none(reg.queryAdapter(req, IResourceUrlConverter))
