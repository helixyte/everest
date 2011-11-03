"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 2, 2011.
"""

from ConfigParser import SafeConfigParser
from everest import db
from everest.configuration import Configurator
from everest.db import get_db_engine
from everest.db import initialize_db
from everest.db import is_db_engine_initialized
from everest.entities.utils import get_persistent_aggregate
from everest.resources.utils import get_collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_root_collection
from everest.root import RootBuilder
from functools import update_wrapper
from lxml import etree
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

__docformat__ = 'reStructuredText en'
__all__ = ['EverestNosePlugin',
           'BaseTestCase',
           'DbTestCase',
           'FunctionalTestCase',
           'ModelTestCase',
           'Pep8CompliantTestCase',
           'ResourceTestCase',
           ]


REMOTE_USER = 'it'


def create_extra_environ():
    return dict(REMOTE_USER=REMOTE_USER)


class EverestAppNosePlugin(nose.plugins.Plugin):
    """
    Nose plugin extension.

    For use with nose to allow a project to be configured before nose
    proceeds to scan the project for doc tests and unit tests. This
    prevents modules from being loaded without a configured everest
    application environment.

    Based on the Pylons plugin for Nose.
    """
    name = None

    def __init__(self, *args, **kw):
        if self.__class__ is EverestAppNosePlugin:
            raise NotImplementedError('Please create a custom nose plugin '
                                      'for your app that derives from '
                                      'EverestAppNosePlugin and has a '
                                      '"name" class attribute.')
        self.conf = None
        self.ini_file = None
        self.enable_opt = '%s_config' % self.name
        nose.plugins.Plugin.__init__(self, *args, **kw)

    def add_options(self, parser, env=None):
        """Add command-line options for this plugin"""
        if env is None:
            env = os.environ
        env_opt = 'NOSE_WITH_%s' % self.name.upper()
        env_opt.replace('-', '_')
        parser.add_option("--with-%s" % self.name,
                          dest=self.enable_opt, type="string",
                          default="",
                          help=".ini file to setup the everest application's "
                               "environment.")

    def configure(self, options, conf):
        """Configure the plugin"""
        self.conf = conf
        if hasattr(options, self.enable_opt):
            self.enabled = bool(getattr(options, self.enable_opt))
            self.ini_file = getattr(options, self.enable_opt)

    def begin(self):
        """Called before any tests are collected or run

        Loads the application, and in turn its configuration.
        """
        path = os.getcwd()
        # Store app name and path to the config file in our testing base class.
        BaseTestCase.app_name = self.name
        BaseTestCase.ini_file_path = os.path.join(path, self.ini_file)


class Pep8CompliantTestCase(unittest.TestCase):
    """
    Base class for tests with PEP8 compliant method names.
    """

    assert_true = unittest.TestCase.assertTrue

    assert_false = unittest.TestCase.assertFalse

    assert_equal = unittest.TestCase.assertEqual

    assert_not_equal = unittest.TestCase.assertNotEqual

    assert_equals = unittest.TestCase.assertEquals

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


class BaseTestCase(Pep8CompliantTestCase):
    """
    Base class for all everest unit test case classes.
    """
    app_name = None      # Set by nose plugin
    ini_file_path = None # Set by nose plugin

    __ini_parser = None

    def _read_ini_file(self):
        if self.__ini_parser is None:
            self.__ini_parser = SafeConfigParser()
            self.__ini_parser.read(self.ini_file_path)
        return self.__ini_parser

    def _test_attributes(self, test_object, attribute_map):
        """
        Utility method to test whether the test object attributes match the
        expected ones (given the dictionary).

        :param test_object: and Entity subclass object
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
        do_initialize = not is_db_engine_initialized()
        if do_initialize:
            # Extract DB initialization strings from the ini file.
            ini_parser = self._read_ini_file()
            db_string = ini_parser.get('app:%s' % self.app_name, 'db_string')
            db_echo = ini_parser.getboolean('app:%s' % self.app_name, 'db_echo')
            engine = initialize_db(db_string, db_echo)
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
        DbTestCase.set_up(self)
        # Create a new testing registry.
        reg = Registry('testing')
        # Configure the registry.
        self.config = Configurator(registry=reg, package=self.app_name)
        self.config.hook_zca()
        self._custom_configure()
        self.config.load_zcml('configure.zcml')

    def _custom_configure(self):
        self.config.begin()

    def tear_down(self):
        DbTestCase.tear_down(self)
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
        ModelTestCase.set_up(self)
        #
        root_builder = RootBuilder()
        self._request.root = root_builder(self._request.environ)

    def _custom_configure(self):
        # Build a dummy request.
        ini_parser = self._read_ini_file()
        host = ini_parser.get('server:main', 'host')
        port = ini_parser.getint('server:main', 'port')
        base_url = 'http://%s:%d' % (host, port)
        app_url = base_url
        self._request = DummyRequest(application_url=app_url,
                                     host_url=base_url,
                                     path_url=app_url,
                                     url=app_url,
                                     registry=self.config.registry,
                                     environ=create_extra_environ())
        # Configure authentication.
        self.config.testing_securitypolicy("it")
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

    NAMESPACES = {
        'atom': 'http://www.w3.org/2005/Atom',
        'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
        'app': 'http://www.w3.org/2007/app',
    }

    find_elements = etree.XPath('*[local-name() = $name]',
                                namespaces=NAMESPACES)
    find_entry_contents = etree.XPath('/atom:feed/atom:entry/atom:content',
                                      namespaces=NAMESPACES)
    count_entries = etree.XPath('count(/atom:feed/atom:entry)',
                                namespaces=NAMESPACES)

    config = None
    app = None

    def set_up(self):
        db.Session.remove()
        reg = Registry('testing')
        self.config = Configurator(registry=reg, package=self.app_name)
        self.config.testing_securitypolicy("it")
        self.config.hook_zca()
        self.config.begin()
        wsgiapp = self._load_wsgiapp()
        self.app = TestApp(wsgiapp,
                           extra_environ=create_extra_environ())

    def tear_down(self):
        transaction.abort()
        db.Session.remove()
        self.config.unhook_zca()
        self.config.end()

    def _load_wsgiapp(self):
        wsgiapp = loadapp('config:' + self.ini_file_path,
                          name=self.app_name)
        return wsgiapp

    def _parse_body(self, body):
        if isinstance(body, unicode):
            body = body.encode('utf-8')
        return etree.XML(body)


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
