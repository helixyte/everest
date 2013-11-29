"""
Testing base classes and services.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 2, 2011.
"""
from ConfigParser import NoSectionError
from everest.configuration import Configurator
from everest.entities.utils import get_root_aggregate
from everest.ini import EverestIni
from everest.repositories.interfaces import IRepositoryManager
from everest.resources.interfaces import IService
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_root_collection
from nose.tools import make_decorator
from paste.deploy import loadapp # pylint: disable=E0611,F0401
from pyramid.registry import Registry
from pyramid.testing import DummyRequest
from webtest import TestApp
import sys
import time
import transaction
import unittest
from everest.constants import RequestMethods

__docformat__ = 'reStructuredText en'
__all__ = ['DummyContext',
           'DummyModule',
           'EntityTestCase',
           'FunctionalTestCase',
           'Pep8CompliantTestCase',
           'ResourceTestCase',
           'TestCaseWithConfiguration',
           'TestCaseWithIni',
           'elapsed',
           ]


class Pep8CompliantTestCase(unittest.TestCase):
    """
    Use this for simple unit tests with PEP8 compliant method names.
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


class TestCaseWithIni(Pep8CompliantTestCase):
    """
    Use this for unit tests that need access to settings specified in an
    .ini file.

    :ivar ini: The ini file parser. This will only be set up if the
        `ini_file_path` and `ini_section_name` class variables were set up
        sensibly.
    """
    # : The name of the package where the tests reside. May be overridden in
    # : derived classes.
    package_name = 'everest'
    # : The path to the application initialization (ini) file name. Override
    # : as needed in derived classes.
    ini_file_path = None
    # : The section name in the ini file to look for settings. Override as
    # : needed in derived classes.
    ini_section_name = None

    def set_up(self):
        self.ini = EverestIni(self.ini_file_path)

    def tear_down(self):
        super(TestCaseWithIni, self).tear_down()
        try:
            del self.ini
        except AttributeError:
            pass

    def _get_app_url(self):
        section = 'server:main'
        if self.ini.has_setting(section, 'host'):
            host = self.ini.get_setting(section, 'host')
        else:
            host = '0.0.0.0'
        if self.ini.has_setting(section, 'port'):
            port = int(self.ini.get_setting(section, 'port'))
        else:
            port = 6543
        return 'http://%s:%d' % (host, port)


class BaseTestCaseWithConfiguration(TestCaseWithIni):
    """
    Base class for test cases that access an initialized (but not configured)
    registry.

    :ivar config: The registry configurator. This is set in the set_up method.
    """
    # : The name of a ZCML configuration file to use.
    config_file_name = 'configure.zcml'

    def set_up(self):
        super(BaseTestCaseWithConfiguration, self).set_up()
        # Create and configure a new testing registry.
        reg = Registry('testing')
        self.config = Configurator(registry=reg,
                                   package=self.package_name)
        if not self.ini_section_name is None:
            settings = self.ini.get_settings(self.ini_section_name)
        else:
            try:
                settings = self.ini.get_settings('DEFAULT')
            except NoSectionError:
                settings = None
        self.config.setup_registry(settings=settings)

    def tear_down(self):
        super(BaseTestCaseWithConfiguration, self).tear_down()
        tear_down_registry(self.config.registry)
        try:
            del self.config
        except AttributeError:
            pass

    def _get_config_file_name(self):
        if self.ini.has_setting(self.ini_section_name, 'configure_zcml'):
            cfg_zcml = self.ini.get_setting(self.ini_section_name,
                                            'configure_zcml')
        else:
            cfg_zcml = self.config_file_name
        return cfg_zcml


class TestCaseWithConfiguration(BaseTestCaseWithConfiguration):
    """
    Use this for test cases that need access to an initialized (but not
    configured) registry.
    """
    def set_up(self):
        BaseTestCaseWithConfiguration.set_up(self)
        self.config.begin()

    def tear_down(self):
        self.config.end()
        BaseTestCaseWithConfiguration.tear_down(self)



class EntityTestCase(BaseTestCaseWithConfiguration):
    """
    Use this for test cases that need access to a configured registry.
    """
    def set_up(self):
        super(EntityTestCase, self).set_up()
        # Load config file.
        self.config.begin()
        self.config.load_zcml(self._get_config_file_name())
        # Set up repositories.
        repo_mgr = self.config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize_all()

    def tear_down(self):
        transaction.abort()
        self.config.end()
        super(EntityTestCase, self).tear_down()

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


class ResourceTestCase(BaseTestCaseWithConfiguration):
    """
    Use this for test cases that need access to a configured registry, a
    request object and a service object.
    """
    config_file_name = 'configure.zcml'

    def set_up(self):
        super(ResourceTestCase, self).set_up()
        # Build a dummy request.
        base_url = app_url = self._get_app_url()
        self._request = DummyRequest(application_url=app_url,
                                     host_url=base_url,
                                     path_url=app_url,
                                     url=app_url,
                                     registry=self.config.registry)
        # Load config file.
        self.config.begin(request=self._request)
        self.config.load_zcml(self._get_config_file_name())
        self._load_custom_zcml()
        # Put the service at the request root (needed for URL resolving).
        srvc = self.config.get_registered_utility(IService)
        self._request.root = srvc
        # Initialize all registered repositories.
        repo_mgr = self.config.get_registered_utility(IRepositoryManager)
        repo_mgr.initialize_all()
        # Start the service.
        srvc.start()

    def tear_down(self):
        transaction.abort()
        self.config.end()
        super(ResourceTestCase, self).tear_down()
        try:
            del self._request
        except AttributeError:
            pass

    def _load_custom_zcml(self):
        # This is meant as a hook for subclasses to slip in custom ZCML
        # after the Zope machinery has been set up but before the service
        # is started.
        pass

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
        coll = create_staging_collection(member_cls)
        return coll.create_member(entity)


class EverestTestApp(TestApp):
    """
    Testing WSGI application for everest.
    """
    def patch(self, url, params='', headers=None, extra_environ=None,
            status=None, upload_files=None, expect_errors=False,
            content_type=None):
        """
        Do a PATCH request. This uses the same machinery as the
        :method:`put` method.
        """
        return self._gen_request(RequestMethods.PATCH,
                                 url, params=params, headers=headers,
                                 extra_environ=extra_environ, status=status,
                                 upload_files=upload_files,
                                 expect_errors=expect_errors,
                                 content_type=content_type)


class FunctionalTestCase(TestCaseWithIni):
    """
    Use this for test cases that need access to a WSGI application.

    :ivar app: :class:`webtest.TestApp` instance wrapping our WSGI app to test.
    """
    # : The name of the application to test.
    app_name = None

    def set_up(self):
        super(FunctionalTestCase, self).set_up()
        # Create the WSGI application and set up a configurator.
        wsgiapp = self._load_wsgiapp()
        self.config = Configurator(registry=wsgiapp.registry,
                                   package=self.package_name)
        self.config.begin()
        self.app = \
            EverestTestApp(wsgiapp,
                           extra_environ=self._create_extra_environment())

    def tear_down(self):
        super(FunctionalTestCase, self).tear_down()
        transaction.abort()
        self.config.end()
        tear_down_registry(self.config.registry)
        try:
            del self.app
        except AttributeError:
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


def tear_down_registry(registry):
    """
    Explicit un-registration of registered adapters and utilities for testing
    puprposes.
    """
    for reg_adp in list(registry.registeredAdapters()):
        registry.unregisterAdapter(factory=reg_adp.factory,
                                   required=reg_adp.required,
                                   provided=reg_adp.provided,
                                   name=reg_adp.name)
    for reg_ut in list(registry.registeredUtilities()):
        registry.unregisterUtility(component=reg_ut.component,
                                   provided=reg_ut.provided,
                                   name=reg_ut.name)
