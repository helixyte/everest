"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 14, 2014.
"""
from itertools import chain
import os
from unittest import TestCase

from _pytest.python import getfixturemarker
from pyramid.compat import configparser
from pyramid.paster import setup_logging
from pyramid.registry import Registry
from pyramid.testing import DummyRequest
import pytest
import transaction

from everest.configuration import Configurator
from everest.ini import EverestIni
from everest.plugins import IPluginManager
from everest.querying.specifications import FilterSpecificationFactory
from everest.querying.specifications import OrderSpecificationFactory
from everest.repositories.constants import REPOSITORY_DOMAINS
from everest.repositories.interfaces import IRepositoryManager
from everest.repositories.rdb.session import ScopedSessionMaker as Session
from everest.representers.interfaces import IRepresenterRegistry
from everest.resources.interfaces import IService
from everest.testing import BaseTestCaseWithConfiguration
from everest.testing import EverestTestApp
from everest.testing import tear_down_registry
from paste.deploy import loadapp
from everest.repositories.rdb.utils import reset_metadata


__docformat__ = 'reStructuredText en'
__all__ = []


def pytest_addoption(parser):
    """
    py.test hook that adds the `--app-ini-file` option for configuring test
    runs with an `ini` file.

    Just like when configuring pyramid with an ini file, you can not only
    define WSGI application settings in your ini file, but also set up the
    logging system if you supply a "loggers" section.
    """
    parser.addoption("--app-ini-file", action="store", default=None,
                     help="everest application ini file.")
    parser.addoption("--app-name", action="store", default=None,
                     help="name of the everest application to run.")


def pytest_configure(config):
    """
    py.test hook that is called after all options have been collected and all
    plugins have been initialized.

    This sets up the logging system from the "loggers" section in your
    application ini file, if configured.
    """
    ini_file_path = config.getoption('--app-ini-file')
    if not ini_file_path is None:
        # FIXME: This is only needed if a test run uses old-style nose tests.
        EverestIni.ini_file_path = ini_file_path
        setup_logging(ini_file_path)
    app_name = config.getoption('--app-name')
    if not app_name is None:
        # FIXME: This is only needed if a test run uses old-style nose tests.
        BaseTestCaseWithConfiguration.ini_section_name = 'app:%s' % app_name


def pytest_collection_modifyitems(session, config, items): # pylint: disable=W0613
    """
    py.test hook called after all tests have been collected.

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


def pytest_pycollect_makemodule(path, parent):
    """
    py.test hook called when a new test module is generated.

    If your test module contains a class named "Fixtures" with
    :class:`Fixture` instances as (class) attributes, this will set up "lazy"
    fixtures to use within the test module.
    """
    mod = path.pyimport()
    fixtures = getattr(mod, 'Fixtures', None)
    if not fixtures is None:
        fixtures = [item for item in fixtures.__dict__.items()
                    if (callable(item[1])
                        and not item[0].startswith('_'))]
        for (fx_name, func) in fixtures:
            if getfixturemarker(func) is None:
                fxt = pytest.fixture(scope='function')(func)
            else:
                fxt = func
            setattr(mod, fx_name, fxt)
    return pytest.Module(path, parent)


class _AppIni(object):
    __parsers = {}

    def __init__(self, ini_file_path=None, app_name=None, package_name=None,
                 config_file_name=None):
        self.__ini_file_path = ini_file_path
        self.__app_name = app_name
        self.__package_name = package_name
        self.__config_file_name = config_file_name
        self.__app_url = None
        self.__app_settings = None
        self.__default_settings = None
        self.__host = '0.0.0.0'
        self.__port = '6543'
        if not ini_file_path is None:
            self.__parser = self.__parsers.get(ini_file_path)
            if self.__parser is None:
                defaults = {'here':os.path.dirname(ini_file_path)}
                self.__parser = \
                    configparser.SafeConfigParser(defaults=defaults)
                self.__parsers[ini_file_path] = self.__parser
        else:
            self.__parser = None

    def load(self):
        if not self.__parser is None:
            self.__parse_ini()
        if self.__config_file_name is None:
            settings = self.__app_settings or self.__default_settings
            if not settings is None:
                self.__config_file_name = settings.get('configure_zcml',
                                                       'configure.zcml')
            else:
                self.__config_file_name = 'configure.zcml'
        if self.__package_name is None:
            self.__package_name = self.__app_name
        self.__app_url = 'http://%s:%s' % (self.__host, self.__port)

    def __parse_ini(self):
        self.__parser.read(self.__ini_file_path)
        if self.__app_name is None:
            # If the app name was not passed in, we try to determine it as
            # follows:
            #  * If the ini file contains only one app:<app name> section,
            #    use it;
            #  * Else, if the ini file contains a pipeline:main section, use
            #    the innermost app;
            #  * Else raise ValueError
            app_names = [sect.split(':')[-1]
                         for sect in self.__parser.sections()
                         if sect[:4] == 'app:']
            if len(app_names) == 1:
                self.__app_name = app_names[0]
            else:
                pp_sect_name = 'pipeline:main'
                if self.__parser.has_section(pp_sect_name):
                    pipeline_apps = \
                        self.__parser.get(pp_sect_name, 'pipeline').split()
                    self.__app_name = pipeline_apps[-1]
                else:
                    raise ValueError('Could not determine application name. '
                                     'You need to either define exactly one '
                                     'app:<app name> section or a '
                                     'pipeline:main section in your ini '
                                     'file.')
        srv_sect_name = 'server:main'
        if self.__parser.has_section(srv_sect_name):
            host_opt_name = 'host'
            if self.__parser.has_option(srv_sect_name, host_opt_name):
                self.__host = self.__parser.get(srv_sect_name, host_opt_name)
            port_opt_name = 'port'
            if self.__parser.has_option(srv_sect_name, port_opt_name):
                self.__port = self.__parser.get(srv_sect_name, port_opt_name)
        if not self.__app_name is None:
            app_sect_name = 'app:%s' % self.__app_name
            if self.__parser.has_section(app_sect_name):
                self.__app_settings = dict(self.__parser.items(app_sect_name))
        def_sect_name = 'DEFAULT'
        if self.__parser.has_section(def_sect_name):
            self.__default_settings = dict(self.__parser.items(def_sect_name))

    @property
    def ini_file_path(self):
        return self.__ini_file_path

    @property
    def app_name(self):
        return self.__app_name

    @property
    def package_name(self):
        return self.__package_name

    @property
    def config_file_name(self):
        return self.__config_file_name

    @property
    def app_url(self):
        return self.__app_url

    @property
    def app_settings(self):
        return self.__app_settings.copy()

    @property
    def default_settings(self):
        return self.__default_settings.copy()

    @property
    def settings(self):
        return self.__app_settings or self.__default_settings


class _IniFactory(object):
    __inis = {}

    @classmethod
    def get_cached(cls, ini_file_path, app_name, package_name,
                   config_file_name):
        key = (ini_file_path, app_name, package_name, config_file_name)
        cached_ini = cls.__inis.get(key)
        if cached_ini is None:
            cached_ini = _AppIni(ini_file_path=ini_file_path,
                                 app_name=app_name,
                                 package_name=package_name,
                                 config_file_name=config_file_name)
            cached_ini.load()
            cls.__inis[key] = cached_ini
        return cached_ini


class _ConfiguratorFactory(object):
    __configurators = {}

    @classmethod
    def get(cls, ini): # redefining ini pylint: disable=W0621
        return cls.__create(ini)

    @classmethod
    def get_cached(cls, ini): # redefining ini pylint: disable=W0621
        key = (ini.ini_file_path, ini.app_name,
               ini.package_name, ini.config_file_name)
        conf = _ConfiguratorFactory.__configurators.get(key)
        if conf is None:
            conf = cls.__create(ini)
            _ConfiguratorFactory.__configurators[key] = conf
        return conf

    @classmethod
    def __create(cls, ini):
        reg = Registry('testing')
        conf = Configurator(registry=reg, package=ini.package_name)
        conf.setup_registry(settings=ini.settings)
        if not ini.config_file_name is None and not ini.package_name is None:
            conf.begin()
            try:
                conf.load_zcml(ini.config_file_name)
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


class ResourceCreatorContextManager(object):
    """
    Context manager for setting up the everest framework for resource level
    operations.
    """
    def __init__(self, ini, config, repo_name=None):
        self.__ini = ini
        self.__config = config
        self.__repo_name = repo_name

    def __enter__(self):
        request = DummyRequest(application_url=self.__ini.app_url,
                               host_url=self.__ini.app_url,
                               path_url=self.__ini.app_url,
                               url=self.__ini.app_url,
                               registry=self.__config.registry)
        srvc = self.__config.get_registered_utility(IService)
        self.__config.begin(request=request)
        request.root = srvc
        repo_mgr = self.__config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize_all()
        if not self.__ini.app_name is None:
            plugin_mgr = self.__config.get_registered_utility(IPluginManager)
            plugin_mgr.load_all("%s.plugins" % self.__ini.app_name)
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


class AppCreatorContextManager(object):
    """
    Context manager for setting up the everest framework for application
    level (functional) operations.
    """
    def __init__(self, ini, config_file_name, extra_environ):
        wsgiapp = loadapp('config:' + ini.ini_file_path, name=ini.app_name)
        self.__app = EverestTestApp(wsgiapp, ini.package_name,
                                    extra_environ=extra_environ)
        self.__config_file_name = config_file_name

    def __enter__(self):
        self.__app.config.begin()
        if not self.__config_file_name is None:
            self.__app.config.load_zcml(self.__config_file_name)
        return self.__app

    def __exit__(self, ext_type, value, tb):
        transaction.abort()
        self.__app.config.end()
        tear_down_registry(self.__app.config.registry)


# pylint: disable=W0613

@pytest.fixture(scope='session')
def session_ini(request):
    """
    Session-scoped fixture for all tests that parse an `ini` file.

    The ini file name is pulled from the `--app-ini-file` command line
    option unless it is overridden by specifying an `ini_file_path` attribute
    in the class name space.
    """
    ini_file_path = request.config.getoption('--app-ini-file')
    app_name = request.config.getoption('--app-name')
    return _IniFactory.get_cached(ini_file_path, app_name, None, None)


@pytest.fixture(scope='class')
def class_ini(request):
    """
    Class-scoped fixture for all tests that parse an `ini` file.

    The ini file name is pulled from the `--app-ini-file` command line
    option unless it is overridden by specifying an `ini_file_path` attribute
    in the class name space.
    """
    ini_file_path = getattr(request.cls, 'ini_file_path', None)
    if ini_file_path is None:
        ini_file_path = request.config.getoption('--app-ini-file')
    app_name = getattr(request.cls, 'app_name', None)
    if app_name is None:
        app_name = request.config.getoption('--app-name')
    pkg_name = getattr(request.cls, 'package_name', None)
    config_file_name = getattr(request.cls, 'config_file_name', None)
    return _IniFactory.get_cached(ini_file_path, app_name, pkg_name,
                                  config_file_name)


@pytest.fixture(scope='session')
def session_configurator(session_ini): # redefining ini pylint: disable=W0621
    """
    Session-scoped fixture for all tests that set up a Pyramid configurator.

    @note: If you modify this configurator, all tests in the current session
        are affected.
    """
    return _ConfiguratorFactory.get(session_ini)


@pytest.fixture(scope='class')
def class_configurator(class_ini): # redefining ini pylint: disable=W0621
    """
    Class-scoped fixture for all tests that set up a Pyramid configurator.

    @note: If you modify this configurator, all tests in all classes using the
           same ini file + ini file section + package name combinatino are
           affected.
    """
    return _ConfiguratorFactory.get_cached(class_ini)


@pytest.fixture
def function_configurator(class_ini): # redefining ini pylint: disable=W0621
    """
    Function-scoped fixture for all tests that set up a Pyramid configurator.
    """
    return _ConfiguratorFactory.get(class_ini)


@pytest.fixture
def mapping_registry_factory(function_configurator): # redefining function_configurator pylint: disable=W0621
    rpr_reg = function_configurator.registry.queryUtility(IRepresenterRegistry)
    return rpr_reg.get_mapping_registry


@pytest.yield_fixture(scope='session')
def session_entity_repo(session_configurator): # redefining session_configurator pylint: disable=W0621
    """
    Session-scoped fixture for all tests that perform operations on entities.
    """
    with EntityCreatorContextManager(session_configurator) as repo:
        yield repo


@pytest.yield_fixture
def class_entity_repo(class_configurator): # redefining class_configurator pylint: disable=W0621
    """
    Fixture for all tests that perform operations on entities.
    """
    with EntityCreatorContextManager(class_configurator) as repo:
        yield repo


@pytest.yield_fixture
def resource_repo(class_ini, class_configurator): # redefining ini, class_configurator pylint: disable=W0621
    """
    Fixture for all tests that perform operations on resources.
    """
    with ResourceCreatorContextManager(class_ini, class_configurator) as repo:
        yield repo


@pytest.yield_fixture
def system_resource_repo(class_ini, class_configurator): # redefining ini, class_configurator pylint: disable=W0621
    """
    Like `resource_repo`, but yields the system repository instead of the
    default repository.
    """
    with ResourceCreatorContextManager(class_ini, class_configurator,
                                       repo_name=REPOSITORY_DOMAINS.SYSTEM) \
         as repo:
        yield repo


@pytest.yield_fixture(scope='class')
def app_creator(request, class_ini): # redefining ini, class_configurator pylint: disable=W0621
    """
    Fixture for all tests that perform operations on applications.
    """
    config_file_name = getattr(request.cls, 'config_file_name', None)
    extra_environ = getattr(request.cls, 'extra_environ', {})
    with AppCreatorContextManager(class_ini, config_file_name, extra_environ) \
         as app:
        yield app


# FIXME: This should be made optional (requires rdb repository).
@pytest.fixture(scope='class')
def rdb(request):
    """
    Fixture for all tests that use the relational database backend.

    This fixture has class scope.
    """
    def tear_down():
        Session.remove()
        assert not Session.registry.has()
        reset_metadata()
    request.addfinalizer(tear_down)


@pytest.fixture
def filter_specification_factory():
    """
    Fixture creating a new
    :class:`everest.querying.specifications.FilterSpecificationFactory`
    instance.
    """
    return FilterSpecificationFactory()


@pytest.fixture
def order_specification_factory():
    """
    Fixture creating a new
    :class:`everest.querying.specifications.OrderSpecificationFactory`
    instance.
    """
    return OrderSpecificationFactory()


@pytest.fixture
def test_object_fac():
    """
    Test object factory fixture.
    """
    return TestObjectFactory

# pylint: enable=W0613


class TestObjectFactory(object):
    """
    Test object factory managing a set of default keyword and positional
    arguments which can be overridden at call time  for lazy object
    initialization.

    Only one instance is created for each unique combination of keyword and
    positional arguments (memoize pattern); use the `new` method to obtain
    a new instance for the same set of arguments.
    """
    def __init__(self, entity_generator_func, args=None, kw=None):
        """
        Constructor.

        :param entity_generator_func: Callable to use to create the test
          object.
        :param tuple args: Default positional arguments to use to create a
          new test object.
        :param dict kw: Default keyword arguments to use to create a
          new test object.
        """
        self.__entity_generator_func = entity_generator_func
        if args is None:
            args = ()
        self.__init_args = args
        if kw is None:
            kw = {}
        self.__init_kw = kw
        # Instance cache.
        self.__instances = {}

    def __call__(self, *args, **kw):
        """
        Returns a test object instance (possibly memoized from a previous
        call with the same arguments). The default positional and keyword
        arguments are overridden with the given parameters.

        :param tuple args: Dynamic positional arguments to use instead of
          the default ones.
        :param dict kw: Dynamic keyword arguments to use instead of
          the default ones.
        """
        _args = args + self.__init_args[len(args):]
        _kw = self.__init_kw.copy()
        _kw.update(kw)
        key = tuple(chain((id(arg) for arg in _args),
                          ((k, id(v)) for (k, v) in sorted(_kw.items()))))
        try:
            obj = self.__instances[key]
        except KeyError:
            obj = self.__entity_generator_func(*_args, **_kw)
            self.__instances[key] = obj
        return obj

    def new(self, *args, **kw):
        """
        Always returns a new instance for the given positional and keyword
        arguments.
        """
        _args = args + self.__init_args[len(args):]
        _kw = self.__init_kw.copy()
        _kw.update(kw)
        return self.__entity_generator_func(*_args, **_kw)

    @property
    def init_args(self):
        """
        Returns the default positional arguments for this factory.
        """
        return self.__init_args

    @property
    def init_kw(self):
        """
        Returns a copy of the default keyword arguments for this factory.
        """
        return self.__init_kw.copy()
