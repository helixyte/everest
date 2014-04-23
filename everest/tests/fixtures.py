"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 14, 2014.
"""
from unittest import TestCase

from pyramid.compat import configparser
from pyramid.paster import setup_logging
from pyramid.registry import Registry
from pyramid.testing import DummyRequest
from pytest import fixture # pylint: disable=E0611
from pytest import yield_fixture # pylint: disable=E0611
import transaction

from everest.configuration import Configurator
from everest.ini import EverestIni
from everest.querying.specifications import FilterSpecificationFactory
from everest.repositories.constants import REPOSITORY_DOMAINS
from everest.repositories.interfaces import IRepositoryManager
from everest.repositories.rdb.session import ScopedSessionMaker as Session
from everest.representers.interfaces import IRepresenterRegistry
from everest.resources.interfaces import IService
from everest.testing import EverestTestApp
from everest.testing import tear_down_registry
from everest.tests.complete_app import fixtures
from paste.deploy import loadapp
from everest.querying.specifications import OrderSpecificationFactory


__docformat__ = 'reStructuredText en'
__all__ = ['app_creator',
           'configurator',
           'entity_repo',
           'ini',
           'resource_repo',
           ]


# FIXME: Is there no better way to make this available?
collection = fixtures.collection
member = fixtures.member
representer = fixtures.representer
member_representer = fixtures.member_representer
mapping = fixtures.mapping
member_mapping = fixtures.member_mapping


def pytest_addoption(parser):
    """
    This adds the `--app-ini-file` option for configuring test runs with an
    `ini` file.

    Just like when configuring pyramid with an ini file, you can not only
    define WSGI application settings in your ini file, but also set up the
    logging system if you supply a "loggers" section.
    """
    parser.addoption("--app-ini-file", action="store", default=None,
                     help="everest application ini file.")


def pytest_configure(config):
    """
    Called by pytest after all options have been collected and all plugins
    have been initialized.

    This sets up the logging system from the "loggers" section in your
    application ini file, if configured.
    """
    app_ini_file = config.getoption('--app-ini-file')
    if not app_ini_file is None:
        setup_logging(app_ini_file)


def pytest_collection_modifyitems(session, config, items): # pylint: disable=W0613
    """
    Called by pytest after all tests have been collected.

    For compatibility with the existing test suite, we remove all tests that
    were collected from abstract base test classes or from classes that have
    a `__test__` attribute set to `False` (nose feature).
    """
    removed = 0
    for idx, item in enumerate(items[:]):
        cls = item.parent.cls
        if not cls is None and issubclass(cls, TestCase) \
           and (cls.__name__.startswith('_')
                or getattr(cls, '__test__', None) is False):
            items.pop(idx - removed)
            removed += 1


@fixture(scope='session')
def ini(request):
    """
    Fixture for all tests that parse an `ini` file.

    The ini file name is pulled from the `--app-ini-file` command line
    option.
    """
    app_ini_file = request.config.getoption('--app-ini-file')
    return EverestIni(app_ini_file)


class _ConfiguratorFactory(object):
    __registries = {}

    @classmethod
    def get(cls, request, ini): # redefining ini pylint: disable=W0621
        package_name, zcml_file_name, settings = cls.__get_args(request, ini)
        return cls.__make_new(package_name, zcml_file_name, settings)

    @classmethod
    def get_cached(cls, request, ini): # redefining ini pylint: disable=W0621
        package_name, zcml_file_name, settings = cls.__get_args(request, ini)
        key = (package_name, zcml_file_name,
               _ConfiguratorFactory.__make_settings_key(settings))
        conf = _ConfiguratorFactory.__registries.get(key)
        if conf is None:
            conf = cls.__make_new(package_name, zcml_file_name, settings)
            _ConfiguratorFactory.__registries[key] = conf
        return conf

    @classmethod
    def __get_args(cls, request, ini): # redefining ini pylint: disable=W0621
        ini_section_name = getattr(request.cls, 'ini_section_name', None)
        pkg_name = getattr(request.cls, 'package_name', None)
        if not pkg_name is None:
            def_cfg_zcml = getattr(request.cls, 'config_file_name',
                                   'configure.zcml')
        else:
            def_cfg_zcml = None
        if not ini_section_name is None:
            settings = ini.get_settings(ini_section_name)
        else:
            try:
                settings = ini.get_settings('DEFAULT')
            except configparser.NoSectionError:
                settings = None
        if not settings is None:
            cfg_zcml = settings.get('configure_zcml', def_cfg_zcml)
        else:
            cfg_zcml = def_cfg_zcml
        return pkg_name, cfg_zcml, settings

    @classmethod
    def __make_new(cls, package_name, zcml_file_name, settings):
        reg = Registry('testing')
        conf = Configurator(registry=reg, package=package_name)
        conf.setup_registry(settings=settings)
        if not package_name is None:
            conf.begin()
            try:
                conf.load_zcml(zcml_file_name)
            finally:
                conf.end()
        return conf

    @classmethod
    def __make_settings_key(cls, settings):
        if settings is None:
            key = None
        else:
            key = tuple([item for item in sorted(settings.items())])
        return key


@fixture(scope='class')
def configurator(request, ini): # redefining ini pylint: disable=W0621
    """
    Fixture for all tests that set up a Pyramid configurator.
    """
    return _ConfiguratorFactory.get_cached(request, ini)


@fixture
def new_configurator(request, ini): # redefining ini pylint: disable=W0621
    """
    Fixture for all tests that set up a Pyramid configurator and modify it.
    """
    return _ConfiguratorFactory.get(request, ini)


@fixture
def mapping_registry_factory(new_configurator): # redefining new_configurator pylint: disable=W0621
    rpr_reg = new_configurator.registry.queryUtility(IRepresenterRegistry)
    return rpr_reg.get_mapping_registry


class EntityCreatorContextManager(object):
    """
    Context manager for setting up the everest framework for entity level
    operations.
    """
    def __init__(self, config):
        self.__config = config

    def __enter__(self):
        repo_mgr = self.__config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize_all()
        self.__config.begin()
        return repo_mgr.get_default()

    def __exit__(self, ext_type, value, tb):
        transaction.abort()
        repo_mgr = self.__config.get_registered_utility(IRepositoryManager)
        repo_mgr.reset_all()
        self.__config.end()


@yield_fixture
def entity_repo(configurator): # redefining configurator pylint: disable=W0621
    """
    Fixture for all tests that perform operations on entities.
    """
    with EntityCreatorContextManager(configurator) as repo:
        yield repo


class ResourceCreatorContextManager(object):
    """
    Context manager for setting up the everest framework for resource level
    operations.
    """
    def __init__(self, config, app_url, repo_name=None):
        self.__config = config
        self.__app_url = app_url
        self.__repo_name = repo_name

    def __enter__(self):
        request = DummyRequest(application_url=self.__app_url,
                               host_url=self.__app_url,
                               path_url=self.__app_url,
                               url=self.__app_url,
                               registry=self.__config.registry)
        srvc = self.__config.get_registered_utility(IService)
        self.__config.begin(request=request)
        request.root = srvc
        repo_mgr = self.__config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize_all()
        srvc.start()
        if self.__repo_name is None:
            repo = repo_mgr.get_default()
        else:
            repo = repo_mgr.get(self.__repo_name)
        return repo

    def __exit__(self, ext_type, value, tb):
        transaction.abort()
        srvc = self.__config.get_registered_utility(IService)
        srvc.stop()
        repo_mgr = self.__config.get_registered_utility(IRepositoryManager)
        repo_mgr.reset_all()
        self.__config.end()


@yield_fixture
def resource_repo(ini, configurator): # redefining ini, configurator pylint: disable=W0621
    """
    Fixture for all tests that perform operations on resources.
    """
    app_url = ini.get_app_url()
    with ResourceCreatorContextManager(configurator, app_url) as repo:
        yield repo


@yield_fixture
def system_resource_repo(ini, configurator): # redefining ini, configurator pylint: disable=W0621
    """
    Like `resource_repo`, but yields the system repository instead of the
    default repository.
    """
    app_url = ini.get_app_url()
    with ResourceCreatorContextManager(configurator, app_url,
                                       repo_name=REPOSITORY_DOMAINS.SYSTEM) \
         as repo:
        yield repo


@yield_fixture(scope='class')
def app_creator(request, ini): # redefining ini pylint: disable=W0621
    """
    Fixture for all tests that perform operations on applications.
    """
    app_name = getattr(request.cls, 'app_name', None)
    pkg_name = getattr(request.cls, 'package_name', 'everest')
    extra_environ = getattr(request.cls, 'extra_environ', {})
    with AppCreatorContextManager(ini.ini_file_path, app_name, pkg_name,
                                  extra_environ) as app:
        yield app


class AppCreatorContextManager(object):
    """
    Context manager for setting up the everest framework for application
    level (functional) operations.
    """
    def __init__(self, ini_file_path, app_name, pkg_name, extra_environ):
        wsgiapp = loadapp('config:' + ini_file_path, name=app_name)
        self.__app = EverestTestApp(wsgiapp, extra_environ=extra_environ)
        self.__config = Configurator(registry=wsgiapp.registry,
                                     package=pkg_name)

    def __enter__(self):
        self.__config.begin()
        return self.__app

    def __exit__(self, ext_type, value, tb):
        transaction.abort()
        self.__config.end()
        tear_down_registry(self.__config.registry)


# FIXME: This should be made optional (requires rdb repository).
@fixture(scope='class')
def rdb(request):
    """
    Fixture for all tests that use the relational database backend.

    This fixture has class scope.
    """
    def tear_down():
        Session.remove()
    request.addfinalizer(tear_down)


@fixture
def filter_specification_factory():
    return FilterSpecificationFactory()


@fixture
def order_specification_factory():
    return OrderSpecificationFactory()
