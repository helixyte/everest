"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 2, 2011.
"""

from ConfigParser import SafeConfigParser
from everest import db
from everest.configuration import Configurator
from everest.db import Session
from everest.db import get_engine
from everest.entities.utils import get_root_aggregate
from everest.repository import REPOSITORIES
from everest.resources.interfaces import IService
from everest.resources.utils import get_root_collection
from everest.resources.utils import get_stage_collection
from functools import update_wrapper
from nose.tools import make_decorator
from paste.deploy import loadapp # pylint: disable=E0611,F0401
from repoze.bfg.registry import Registry
from repoze.bfg.testing import DummyRequest
from webtest import TestApp
import nose.plugins
import os
import sys
import time
import transaction
import unittest
from everest.interfaces import IRepositoryManager

__docformat__ = 'reStructuredText en'
__all__ = ['BaseTestCase',
           'DummyContext',
           'DummyModule',
           'EntityTestCase',
           'EverestIni',
           'EverestNosePlugin',
           'FunctionalTestCase',
           'OrmContextManager',
           'Pep8CompliantTestCase',
           'ResourceTestCase',
           'check_attributes',
           'elapsed',
           'no_autoflush',
           'persist',
           'with_orm',
           ]


class EverestNosePlugin(nose.plugins.Plugin):
    """
    Nose plugin extension.

    Provides a nose option that configures a test application configuration
    file.
    """

    def __init__(self, *args, **kw):
        nose.plugins.Plugin.__init__(self, *args, **kw)
        self.__opt_name = 'app-ini-file'
        self.__dest_opt_name = self.__opt_name.replace('-', '_')

    def options(self, parser, env=None):
        """Add command-line options for this plugin."""
        if env is None:
            env = os.environ
        env_opt_name = 'NOSE_%s' % self.__dest_opt_name.upper()
        parser.add_option("--%s" % self.__opt_name,
                          dest=self.__dest_opt_name,
                          type="string",
                          default=env.get(env_opt_name),
                          help=".ini file providing the environment for the "
                               "test web application.")

    def configure(self, options, conf):
        """Configure the plugin"""
        super(EverestNosePlugin, self).configure(options, conf)
        opt_val = getattr(options, self.__dest_opt_name, None)
        if opt_val:
            self.enabled = True
            EverestIni.ini_file_path = opt_val


class Pep8CompliantTestCase(unittest.TestCase):
    """
    Base class for tests with PEP8 compliant method names.
    """

    assert_true = unittest.TestCase.assertTrue

    assert_false = unittest.TestCase.assertFalse

    assert_equal = unittest.TestCase.assertEqual

    assert_equals = unittest.TestCase.assertEquals

    assert_not_equal = unittest.TestCase.assertNotEqual

    assert_almost_equal = unittest.TestCase.assertAlmostEqual

    assert_not_almost_equal = unittest.TestCase.assertNotAlmostEqual

    assert_is_none = unittest.TestCase.assertIsNone

    assert_is_not_none = unittest.TestCase.assertIsNotNone

    assert_raises = unittest.TestCase.assertRaises

    def set_up(self):
        pass

    def tear_down(self):
        pass

    def setUp(self):
        self.set_up()

    def tearDown(self):
        self.tear_down()


class EverestIni(object):
    """
    Helper class providing access to settings parsed from an ini file.
    
    By default, the ini file configured through the :class:`EverestNosePlugin`
    is used.
    """
    #: Path to the global ini file. Set through the nose plugin.
    ini_file_path = None

    __ini_parser = None

    def __init__(self, ini_file_path=None):
        if ini_file_path is None:
            self.__ini_parser = self.__check_ini_file()
        else:
            self.__ini_parser = self.__make_parser()
            self.__ini_parser.read(ini_file_path)
            self.ini_file_path = ini_file_path

    def get_settings(self, section):
        """
        Returns a dictionary containing the settings for the given ini file
        section.
        
        :param str section: ini file section.
        """
        return dict(self.__ini_parser.items(section))

    def get_setting(self, section, key):
        """
        Returns the specified setting from the given ini file section.
        
        :param str section: ini file section.
        :param str key: key to look up in the section.
        """
        return self.__ini_parser.get(section, key)

    @classmethod
    def __check_ini_file(cls):
        if cls.ini_file_path is None:
            raise ValueError('You need to set an application '
                             'initialization file path (e.g., through '
                             'the EverestAppNosePlugin).')
        if cls.__ini_parser is None:
            cls.__ini_parser = cls.__make_parser()
            cls.__ini_parser.read(cls.ini_file_path)
        return cls.__ini_parser

    @classmethod
    def __make_parser(cls):
        return SafeConfigParser(defaults={'here': os.getcwd()})


class BaseTestCase(Pep8CompliantTestCase):
    """
    Base class for all everest unit test case classes.
    """
    #: The registry configurator. This is set in the set_up method.
    config = None
    #: The name of the package where the tests reside. May be overridden in
    #: derived classes.
    package_name = 'everest'
    #: The path to the application initialization (ini) file name. Override
    #: as needed in derived classes.
    ini_file_path = None
    #: The section name in the ini file to look for settings. Override as 
    #: needed in derived classes.
    ini_section_name = 'everest'
    #: The ini file parser. This will only be set up if the ini_file_path 
    #: and ini_section_name variables were set up sensibly.
    ini = None

    def set_up(self):
        # Create and configure a new testing registry.
        reg = Registry('testing')
        self.ini = EverestIni(self.ini_file_path)
        settings = self.ini.get_settings(self.ini_section_name)
        self.config = Configurator(registry=reg,
                                   package=self.package_name)
        self.config.setup_registry(settings=settings)


class EntityTestCase(BaseTestCase):
    """
    Test class for entity classes.
    """

    def set_up(self):
        super(EntityTestCase, self).set_up()
        # Load config file.
        self.config.hook_zca()
        self.config.begin()
        self.config.load_zcml('configure.zcml')
        # Set up repositories.
        repo_mgr = self.config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize()

    def tear_down(self):
        transaction.abort()
        self.config.unhook_zca()
        self.config.end()

    def _get_entity(self, icollection, key=None):
        agg = get_root_aggregate(icollection)
        if key is None:
            agg.slice = slice(0, 1)
            entity = list(agg.iterator())[0]
        else:
            entity = agg.get_by_slug(key)
        return entity

    def _create_entity(self, entity_cls, data):
        return entity_cls.create_from_data(data)


class ResourceTestCase(BaseTestCase):
    """
    Test class for resource classes.
    """
    _request = None

    def set_up(self):
        super(ResourceTestCase, self).set_up()
        # Build a dummy request.
        host = self.ini.get_setting('server:main', 'host')
        port = int(self.ini.get_setting('server:main', 'port'))
        base_url = app_url = 'http://%s:%d' % (host, port)
        self._request = DummyRequest(application_url=app_url,
                                     host_url=base_url,
                                     path_url=app_url,
                                     url=app_url,
                                     registry=self.config.registry)
        # Load config file.
        self.config.hook_zca()
        self.config.begin(request=self._request)
        self.config.load_zcml('configure.zcml')
        # Put the service at the request root (needed for URL resolving).
        srvc = self.config.get_registered_utility(IService)
        self._request.root = srvc
        # Start the service.
        srvc.start()

    def tear_down(self):
        transaction.abort()
        self.config.unhook_zca()
        self.config.end()

    def _get_member(self, icollection, key=None):
        if key is None:
            coll = self._get_collection(icollection, slice(0, 1))
            member = list(iter(coll))[0]
        else:
            coll = get_root_collection(icollection)
            member = coll.get(key)
        return member

    def _get_collection(self, icollection, slice_key=None):
        if slice_key is None:
            slice_key = slice(0, 10)
        coll = get_root_collection(icollection)
        coll.slice = slice_key
        return coll

    def _create_member(self, member_cls, entity):
        coll = get_stage_collection(member_cls)
        return coll.create_member(entity)


class FunctionalTestCase(BaseTestCase):
    """
    A basic test class for client side actions.
    """
    app = None
    app_name = None

    def set_up(self):
        # Create and configure a new testing registry.
        reg = Registry('testing')
        self.ini = EverestIni(self.ini_file_path)
        self.config = Configurator(registry=reg,
                                   package=self.package_name)
        self.config.hook_zca()
        self.config.begin()
        wsgiapp = self._load_wsgiapp()
        self._custom_configure()
        # Set up repositories.
        repo_mgr = self.config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize()
        self.app = TestApp(wsgiapp,
                           extra_environ=self._create_extra_environment())

    def tear_down(self):
        transaction.abort()
        self.config.unhook_zca()
        self.config.end()

    def _custom_configure(self):
        """
        Called from :method:`set_up` after the configurator has been set up
        and hooked with the ZCA site manager, but before the WSGI app is
        loaded.

        This default implementation does nothing and is meant to be overridden.
        """
        pass

    def _load_wsgiapp(self):
        wsgiapp = loadapp('config:' + self.ini.ini_file_path,
                          name=self.app_name)
        return wsgiapp

    def _create_extra_environment(self):
        return {}


class DummyModule(object):
    """
    Dummy module for testing.
    """

    __path__ = "foo"
    __name__ = "dummy"
    __file__ = ''


class DummyContext:
    """
    Dummy context for testing.
    """

    def __init__(self, resolved=DummyModule):
        self.actions = []
        self.info = None
        self.resolved = resolved
        self.package = None

    def action(self, discriminator, callable=None, # pylint: disable=W0622
               args=None, kw=None, order=0): # pylint: disable=W0613
        if args is None:
            args = ()
        if kw is None:
            kw = {}
        self.actions.append(
            {'discriminator':discriminator,
             'callable':callable,
             'args':args,
             'kw':kw}
            )

    def path(self, path):
        return path

    def resolve(self, dottedname): # dottedname not used pylint: disable=W0613
        return self.resolved


def elapsed(func):
    """
    Useful decorator to print out the elapsed time for a unit test.
    """
    def call_elapsed(*args, **kwargs):
        start_time = time.time()
        func(*args, **kwargs)
        sys.__stdout__.write('Time elapsed: %s'
                             % (time.time() - start_time,))
    return make_decorator(func)(call_elapsed)


def no_autoflush(scoped_session=None):
    """
    Decorator to disable autoflush on the session for the duration of a
    test call. Uses the scoped session from the :mod:`everest.db` module
    as default.

    Adapted from
    http://www.sqlalchemy.org/trac/wiki/UsageRecipes/DisableAutoflush
    """
    if scoped_session is None:
        scoped_session = Session
    def decorate(fn):
        def wrap(*args, **kw):
            session = scoped_session()
            autoflush = session.autoflush
            session.autoflush = False
            try:
                return fn(*args, **kw)
            finally:
                session.autoflush = autoflush
        return update_wrapper(wrap, fn)
    return decorate


class OrmContextManager(object):
    """
    Context manager for ORM tests.
    
    Configures the entity repository to use the ORM implementation as
    a default, sets up an outer transaction before the test is run and rolls
    this transaction back after the test has finished.
    """
    def __init__(self, autoflush=True, engine_name=None):
        self.__autoflush = autoflush
        if engine_name is None:
            # Use the name of the default ORM repository for engine lookup.
            engine_name = REPOSITORIES.ORM
        self.__engine_name = engine_name
        self.__connection = None
        self.__transaction = None
        self.__session = None
        self.__old_autoflush_flag = None

    def __enter__(self):
        # We set up an outer transaction that allows us to roll back all
        # changes (including commits) the unittest may want to make.
        engine = get_engine(self.__engine_name)
        self.__connection = engine.connect()
        self.__transaction = self.__connection.begin()
        # Configure the autoflush behavior of the session.
        self.__old_autoflush_flag = db.Session.autoflush #pylint:disable=E1101
        db.Session.configure(autoflush=self.__autoflush)
        # Make sure we start with a clean session.
        db.Session.remove()
        # Throw out the Zope transaction manager for testing.
        db.Session.configure(extension=None)
        # Create a new session for the tests.
        self.__session = db.Session(bind=self.__connection)
        return self.__session

    def __exit__(self, ext_type, value, tb):
        # Roll back the outer transaction and close the connection.
        self.__session.close()
        self.__transaction.rollback()
        self.__connection.close()
        # Remove the session we created.
        db.Session.remove()
        # Restore autoflush flag.
        db.Session.configure(autoflush=self.__old_autoflush_flag)


def with_orm(autoflush=True, init_callback=None):
    """
    Decorator for ORM tests which uses a :class:`OrmContextManager` for the
    call to the decorated test function.
    """
    def decorate(func):
        def wrap(*args, **kw):
            with OrmContextManager(autoflush=autoflush,
                                   init_callback=init_callback):
                func(*args, **kw)
        return update_wrapper(wrap, func)
    return decorate


def check_attributes(test_object, attribute_map):
    """
    Utility function to test whether the test object attributes match the
    expected ones (given the dictionary).

    :param test_object: a test object
    :param attribute_map: a dictionary with key = attribute name
            and value = expected value for this attribute
    """
    for attr_name, exp_val in attribute_map.iteritems():
        assert getattr(test_object, attr_name) == exp_val


def persist(session, entity_class, attribute_map,
            do_attribute_check=True):
    """
    Utility function which creates an object of the given class with the
    given attribute map, commits it to the backend, reloads it from the
    backend and then tests if the attributes compare equal.

    :param entity_class: class inheriting from
      :class:`everest.entities.base.Entity`
    :param attribute_map: a dictionary containint attribute names as keys
      and expected attribute values as values. The attribute map must
      contain all mandatory attributes required for instantiation.
    """
    # Instantiate.
    entity = entity_class(**attribute_map) #pylint:disable=W0142
    session.add(entity)
    session.commit()
    session.refresh(entity)
    entity_id = entity.id
    # Assure a new object is loaded to test if storing worked.
    session.expunge(entity)
    del entity
    query = session.query(entity_class)
    fetched_entity = query.filter_by(id=entity_id).one()
    if do_attribute_check:
        check_attributes(fetched_entity, attribute_map)
