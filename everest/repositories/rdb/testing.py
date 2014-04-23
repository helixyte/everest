"""
Testing utilities for the rdb backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 26, 2013.
"""
from functools import update_wrapper

from pyramid.compat import iteritems_
from pyramid.threadlocal import get_current_registry

from everest.repositories.constants import REPOSITORY_TYPES
from everest.repositories.interfaces import IRepositoryManager
from everest.repositories.rdb.session import ScopedSessionMaker as Session
from everest.repositories.rdb.utils import reset_metadata
from everest.repositories.utils import get_engine


__docformat__ = 'reStructuredText en'
__all__ = ['RdbContextManager',
           'RdbTestCaseMixin',
           'check_attributes',
           'persist',
           'with_rdb',
           ]


def check_attributes(test_object, attribute_map):
    """
    Utility function to test whether the test object attributes match the
    expected ones (given the dictionary).

    :param test_object: a test object
    :param attribute_map: a dictionary with key = attribute name
            and value = expected value for this attribute
    """
    for attr_name, exp_val in iteritems_(attribute_map):
        obj_val = getattr(test_object, attr_name)
        if obj_val != exp_val:
            raise AssertionError('Values for attribute %s differ!'
                                 % attr_name)


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
    entity = entity_class(**attribute_map)
    session.add(entity_class, entity)
    session.commit()
    session.refresh(entity)
    entity_id = entity.id
    # Assure a new object is loaded to test if persisting worked.
    session.expunge(entity)
    del entity
    query = session.query(entity_class)
    fetched_entity = query.filter_by(id=entity_id).one()
    if do_attribute_check:
        check_attributes(fetched_entity, attribute_map)


class RdbContextManager(object):
    """
    Context manager for RDB tests.

    Configures the entity repository to use the RDB implementation as
    a default, sets up an outer transaction before the test is run and rolls
    this transaction back after the test has finished.
    """
    def __init__(self, autoflush=True, engine_name=None):
        if engine_name is None:
            # Use the name of the default RDB repository for engine lookup.
            engine_name = REPOSITORY_TYPES.RDB
        self.__autoflush = autoflush
        self.__engine_name = engine_name
        self.__connection = None
        self.__transaction = None
        self.__session = None
        self.__repo = None
        self.__old_autoflush_flag = None
        self.__old_join_transaction_flag = None

    def __enter__(self):
        # We set up an outer transaction that allows us to roll back all
        # changes (including commits) the unittest may want to make.
        engine = get_engine(self.__engine_name)
        self.__connection = engine.connect()
        self.__transaction = self.__connection.begin()
        reg = get_current_registry()
        repo_mgr = reg.getUtility(IRepositoryManager)
        self.__repo = repo_mgr.get(self.__engine_name)
        # Configure the autoflush behavior of the session.
        if Session.registry.has():
            self.__old_autoflush_flag = Session.autoflush # pylint:disable=E1101
        else:
            self.__old_autoflush_flag = self.__autoflush
        Session.remove()
        Session.configure(autoflush=self.__autoflush)
        # Create a new session for the tests.
        Session.configure(bind=self.__connection)
        self.__old_join_transaction_flag = self.__repo.join_transaction
        self.__repo.join_transaction = False
        self.__session = self.__repo.session_factory()
        return self.__session

    def __exit__(self, ext_type, value, tb):
        # Roll back the outer transaction and close the connection.
        self.__session.close()
        self.__transaction.rollback()
        self.__connection.close()
        # Remove the session we created.
        Session.remove()
        # Restore flags.
        Session.configure(autoflush=self.__old_autoflush_flag,
                          bind=get_engine(self.__engine_name))
        self.__repo.join_transaction = self.__old_join_transaction_flag


def with_rdb(autoflush=True, init_callback=None):
    """
    Decorator for tests which uses a :class:`RdbContextManager` for the
    call to the decorated test function.
    """
    def decorate(func):
        def wrap(*args, **kw):
            with RdbContextManager(autoflush=autoflush,
                                   init_callback=init_callback):
                func(*args, **kw)
        return update_wrapper(wrap, func)
    return decorate


class RdbTestCaseMixin(object):
    def tear_down(self):
        super(RdbTestCaseMixin, self).tear_down()
        Session.remove()

#    @classmethod
#    def setup_class(cls):
#        base_cls = super(RdbTestCaseMixin, cls)
#        try:
#            base_cls.setup_class()
#        except AttributeError:
#            pass
#        Session.remove()
#        assert not Session.registry.has()
#        reset_metadata()
#        reset_engines()

    @classmethod
    def teardown_class(cls):
        base_cls = super(RdbTestCaseMixin, cls)
        try:
            base_cls.teardown_class()
        except AttributeError:
            pass
        Session.remove()
        assert not Session.registry.has()
        reset_metadata()


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
