"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 2, 2011.
"""

from ConfigParser import SafeConfigParser
from everest import db
from everest.configuration import Configurator
from everest.db import get_db_engine
from everest.db import is_db_engine_initialized
from everest.db import set_db_engine
from everest.entities.utils import get_persistent_aggregate
from everest.resources.interfaces import IService
from everest.resources.utils import get_collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_root_collection
from functools import update_wrapper
from nose.tools import make_decorator
from paste.deploy import loadapp # pylint: disable=E0611,F0401
from repoze.bfg.registry import Registry
from repoze.bfg.testing import DummyRequest
from sqlalchemy.engine import create_engine
from webtest import TestApp as _TestApp
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
import nose.plugins
import os
import sys
import time
import unittest

__docformat__ = 'reStructuredText en'
__all__ = ['BaseTestCase',
           'DbTestCase',
           'DummyContext',
           'DummyModule',
           'EverestTestApp',
           'EverestTestAppNosePlugin',
           'FunctionalTestCase',
           'ModelTestCase',
           'Pep8CompliantTestCase',
           'ResourceTestCase',
           'TestApp',
           'elapsed',
           'no_autoflush',
           ]


class EverestTestAppNosePlugin(nose.plugins.Plugin):
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
        super(EverestTestAppNosePlugin, self).configure(options, conf)
        opt_val = getattr(options, self.__dest_opt_name, None)
        if opt_val:
            self.enabled = True
            TestApp.app_ini_file_path = opt_val


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
        "Hook method for setting up the test fixture before exercising it."
        pass

    def tear_down(self):
        "Hook method for deconstructing the test fixture after testing it."
        pass

    def setUp(self):
        self.set_up()

    def tearDown(self):
        self.tear_down()


class TestApp(_TestApp):
    """
    Test web application.

    Extends the base class with facilities to access to a global application
    initialization file that can be configured through nose.
    """
    #: Name of the application to test. This specifies the section name to
    #: look for in the initialization file. Please set to your app's name in
    #: a derived class.
    app_name = None

    #: Name of the package to load the application from. Please set to your
    #: app's package in a derived class.
    package_name = None

    #: Application initialization file path. Set from the nose plugin
    #: :class:`EverestTestAppNosePlugin`.
    app_ini_file_path = None

    __ini_parser = None

    @classmethod
    def read_ini_file(cls):
        """
        Returns a parser for the application ini file that was configured
        through the :method:`set_app_ini_file_path` method.
        """
        if cls.__ini_parser is None:
            if cls.app_ini_file_path is None:
                raise ValueError('You need to configure an application '
                                 'initialization file path (e.g., through '
                                 'the EverestAppNosePlugin).')
            cls.__ini_parser = SafeConfigParser()
            cls.__ini_parser.read(cls.app_ini_file_path)
        return cls.__ini_parser


class EverestTestApp(TestApp):
    """
    Test app class for everest tests.
    """
    app_name = 'everest'
    package_name = 'everest'


class BaseTestCase(Pep8CompliantTestCase):
    """
    Base class for all everest unit test case classes.
    """

    #: The class of the test application (subclass of :class:`TestApp`).
    #: Override to make your test case load settings from custom sections
    #: of your application initialization file.
    test_app_cls = EverestTestApp

    def _test_attributes(self, test_object, attribute_map):
        """
        Utility method to test whether the test object attributes match the
        expected ones (given the dictionary).

        :param test_object: a test object
        :param attribute_map: a dictionary with key = attribute name
                and value = expected value for this attribute
        """
        for attr_name, wanted_value in attribute_map.iteritems():
            self.assert_equal(getattr(test_object, attr_name), wanted_value)


class DbTestCase(BaseTestCase):
    """
    Test class for database related operations such as query, insert, update,
    and delete.
    """
    _connection = None
    _transaction = None
    _session = None

    def set_up(self):
        # Initialize the engine, if necessary. Note that this should only
        # be done once per process.
        if not is_db_engine_initialized():
            db_string, db_echo = self._get_db_info_from_ini_file()
            engine = create_engine(db_string)
            engine.echo = db_echo
            set_db_engine(engine)
        else:
            engine = get_db_engine()
        # We set up an outer transaction that allows us to roll back all
        # changes (including commits) the unittest may want to make.
        self._connection = engine.connect()
        self._transaction = self._connection.begin()
        # Make sure we start with a clean session.
        db.Session.remove()
        # Throw out the Zope transaction manager.
        db.Session.configure(extension=None)
        # Create a new session for the tests.
        self._session = db.Session(bind=self._connection)

    def tear_down(self):
        # Roll back the outer transaction and close the connection.
        self._session.close()
        self._transaction.rollback()
        self._connection.close()
        # Remove the session we created.
        db.Session.remove()

    def _get_db_info_from_ini_file(self):
        # Extract DB initialization strings from the ini file.
        ini_parser = self.test_app_cls.read_ini_file()
        ini_marker = 'app:%s' % self.test_app_cls.app_name
        db_string = ini_parser.get(ini_marker, 'db_string')
        if ini_parser.has_option(ini_marker, 'db_echo'):
            db_echo = ini_parser.getboolean(ini_marker, 'db_echo')
        else:
            db_echo = False
        return db_string, db_echo

    def _test_model_attributes(self, model_class, attribute_map,
                               test_attributes=True):
        """
        Utility method which creates an object of the given class with the
        given attribute map, commits it to the backend, reloads it from the
        backend and then tests if the attributes compare equal.

        :param model_class: A model class inheriting from
                :class:`everest.entities.base.Entity`
        :param attribute_map: a dictionary with (key = attribute name,
                value = expected value of the attribute)
        """
        # Instantiate.
        model = model_class(**attribute_map) #pylint:disable=W0142
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        model_id = model.id
        # Assure a new object is loaded to test if storing worked.
        self._session.expunge(model)
        del model
        query = self._session.query(model_class)
        fetched_model = query.filter_by(id=model_id).one()
        if test_attributes:
            self._test_attributes(fetched_model, attribute_map)


class ModelTestCase(DbTestCase):
    """
    Test class for entity classes.
    """

    __autoflush_flag = None
    config = None
    autoflush_default = False

    def set_up(self):
        # Configure the sessionmaker to disable autoflush before we create our
        # session.
        self.__autoflush_flag = db.Session.autoflush #pylint:disable=E1101
        db.Session.configure(autoflush=self.autoflush_default)
        super(ModelTestCase, self).set_up()
        # Create a new testing registry.
        reg = Registry('testing')
        # Configure the registry.
        self.config = Configurator(registry=reg,
                                   package=self.test_app_cls.package_name)
        self.config.setup_registry()
        self.config.hook_zca()
        self._custom_configure()
        self.config.load_zcml('configure.zcml')

    def _custom_configure(self):
        self.config.begin()

    def tear_down(self):
        super(ModelTestCase, self).tear_down()
        db.Session.configure(autoflush=self.__autoflush_flag)
        self.config.unhook_zca()
        self.config.end()

    def _get_entity(self, icollection, key=None):
        agg = get_persistent_aggregate(icollection)
        if key is None:
            agg.slice(slice(0, 1))
            entity = list(agg.iterator())[0]
        else:
            entity = agg.get_by_slug(key)
        return entity

    def _create_entity(self, entity_cls, data):
        return entity_cls.create_from_data(data)


class ResourceTestCase(ModelTestCase):
    """
    Test class for resources classes.
    """

    autoflush_default = True
    _request = None

    def set_up(self):
        super(ResourceTestCase, self).set_up()
        # Set the request root.
        srvc = get_utility(IService)
        srvc.start()
        self._request.root = srvc

    def _custom_configure(self):
        # Build a dummy request.
        ini_parser = self.test_app_cls.read_ini_file()
        host = ini_parser.get('server:main', 'host')
        port = ini_parser.getint('server:main', 'port')
        base_url = 'http://%s:%d' % (host, port)
        app_url = base_url
        self._request = DummyRequest(application_url=app_url,
                                     host_url=base_url,
                                     path_url=app_url,
                                     url=app_url,
                                     registry=self.config.registry)
        self.config.begin(request=self._request)

    def _get_member(self, icollection, key=None):
        coll = get_root_collection(icollection)
        if key is None:
            coll = self._get_collection(icollection, slice(0, 1))
            member = list(iter(coll))[0]
        else:
            member = coll.get(key)
        return member

    def _get_collection(self, icollection, slice_key=None):
        if slice_key is None:
            slice_key = slice(0, 10)
        coll = get_root_collection(icollection)
        coll.slice = slice_key
        return coll

    def _create_member(self, member_cls, entity):
        member = member_cls.create_from_entity(entity)
        coll = get_collection(get_collection_class(member))
        coll.add(member)
        return member


class FunctionalTestCase(BaseTestCase):
    """
    A basic test class for client side actions.
    """

    config = None
    app = None

    def set_up(self):
        reg = Registry('testing')
        self.config = Configurator(registry=reg,
                                   package=self.test_app_cls.package_name)
        self.config.hook_zca()
        self.config.begin()
        wsgiapp = self._load_wsgiapp()
        self._custom_configure()
        self.app = TestApp(wsgiapp,
                           extra_environ=self._create_extra_environment())

    def tear_down(self):
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
        wsgiapp = loadapp('config:' + self.test_app_cls.app_ini_file_path,
                          name=self.test_app_cls.app_name)
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


def no_autoflush(scoped_session):
    """
    Decorator to disable autoflush on the session for the duration of a
    test call.

    Taken from
    http://www.sqlalchemy.org/trac/wiki/UsageRecipes/DisableAutoflush
    """
    def decorate(fn):
        def go(*args, **kw):
            session = scoped_session()
            autoflush = session.autoflush
            session.autoflush = False
            try:
                return fn(*args, **kw)
            finally:
                session.autoflush = autoflush
        return update_wrapper(go, fn)
    return decorate
