"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from everest.entities.utils import get_entity_class
from everest.resources.interfaces import IDataStore
from zope.interface import implements  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['DataStore',
           'SessionFactory',
           ]


class SessionFactory(object):
    """
    Base class for session factories.
    """
    def __init__(self, entity_store):
        self._entity_store = entity_store

    def __call__(self):
        raise NotImplementedError('Abstract method.')


class DataStore(object):
    """
    Base class for data stores.
    
    An data store is responsible for configuration and initialization of a
    storage backend for resource data. It also creates and holds a session
    factory which is used to create a (thread-local) session. The session
    alone provides access to the entities loaded from the data store. 
    """
    implements(IDataStore)

    _configurables = ['messaging_enable', 'messaging_reset_on_start']

    def __init__(self, name,
                 autoflush=False, join_transaction=False, autocommit=False):
        """
        Constructor.
        
        :param name: name for this entity store (propagated to repository).
        :param autoflush: indicates whether changes should be flushed
            automatically.
        :param join_transaction: indicates whether this store should 
            participate in the Zope transaction.
        :param autocommit: indicates whether changes should be committed
            automatically.
        """
        self.__name = name
        if join_transaction and autocommit:
            raise ValueError('The "join_transaction" flag and the '
                             '"autocommit" flag can not both be set.')
        # : Flag indicating that changes should be flushed immediately.
        self.autoflush = autoflush
        # : Flag indicating that the sessions using this entity store should
        # : join the Zope transaction.
        self.join_transaction = join_transaction
        # : Flag indicating that changes should be committed immediately.
        self.autocommit = autocommit
        self._config = {}
        self.__session_factory = None
        self.__is_initialized = False
        # : The set of resources (collection classes) managed by this entity
        # : store.
        self.__registered_resources = set()

    def configure(self, **config):
        for key, val in config.items():
            if not key in self._configurables:
                raise ValueError('Invalid configuration key "%s".' % key)
            self._config[key] = val

    def register_resource(self, resource):
        self.__registered_resources.add(resource)

    @property
    def registered_types(self):
        return [get_entity_class(rc) for rc in self.__registered_resources]

    def initialize(self):
        # Perform initialization specific to the derived class.
        self._initialize()
        #
        self.__is_initialized = True

    @property
    def session_factory(self):
        if self.__session_factory is None:
            # Create a session factory. The call to _initialize may depend on
            # the session factory being instantiated.
            self.__session_factory = self._make_session_factory()
        return self.__session_factory

    @property
    def name(self):
        return self.__name

    @property
    def configuration(self):
        """
        Returns a copy of the configuration for this entity store.
        """
        return self._config.copy()

    @property
    def is_initialized(self):
        return self.__is_initialized

    def _initialize(self):
        """
        Performs initialization of the entity store.
        """
        raise NotImplementedError('Abstract method.')

    def _make_session_factory(self):
        """
        Create the session factory for this entity store.
        """
        raise NotImplementedError('Abstract method.')
