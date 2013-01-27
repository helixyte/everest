"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from everest.entities.utils import get_entity_class
from everest.repositories.interfaces import IRepository
from everest.resources.io import load_into_collection_from_url
from everest.resources.utils import get_collection_class
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['Repository',
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


class Repository(object):
    """
    Base class for repositories.

    A repository has the following responsibilities:
     * Configure and initialize a storage backend for resource data; 
     * Create and cache aggregate and collection accessors for registered 
       resources;
     * Create and hold a session factory which is used to create a 
       (thread-local) session. The session is used by the accessors to 
       load entities and resources from the repository. 
    """
    implements(IRepository)

    #: A list of key names which can be used by :method:`configure`.
    _configurables = ['messaging_enable', 'messaging_reset_on_start']

    def __init__(self, name, aggregate_class,
                 autoflush=False, join_transaction=False, autocommit=False):
        """
        Constructor.
        
        :param name: Name for this entity store (propagated to repository).
        :param aggregate_class: The aggregate class to use when creating new
          aggregates in this repository.
        :param autoflush: Indicates whether changes should be flushed
          automatically.
        :param join_transaction: Indicates whether this store should 
          participate in the Zope transaction.
        :param autocommit: Indicates whether changes should be committed
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
        self.__is_initializing = False
        self.__is_initialized = False
        self.__cache = {}
        self.__agg_cls = aggregate_class
        self.__session_factory = None
        # : The set of resources (collection classes) managed by this entity
        # : store.
        self.__registered_resources = set()

    def get_aggregate(self, resource):
        """
        Get a clone of the root aggregate for the given registered resource.
        
        :param resource: Registered resource.
        :raises RuntimeError: If the repository has not been initialized yet.
        """
        return self.get_collection(resource).get_aggregate()

    def get_collection(self, resource):
        """
        Get a clone of the root collection for the given registered resource.

        :param resource: Registered resource.
        :raises RuntimeError: If the repository has not been initialized yet.
        """
        if not self.__is_initialized:
            raise RuntimeError('Repository needs to be initialized.')
        ent_cls = get_entity_class(resource)
        root_coll = self.__cache.get(ent_cls)
        if root_coll is None:
            coll_cls = get_collection_class(resource)
            agg = self.__agg_cls.create(ent_cls, self.session_factory)
            root_coll = coll_cls.create_from_aggregate(agg)
            self.__cache[ent_cls] = root_coll
        clone = root_coll.clone()
        clone.__repository__ = self
        return clone

    def set_collection_parent(self, resource, parent):
        """
        Sets the parent of the specified root collection to the given
        object (typically a service object).
        
        :param resource: Registered resource.
        :raises ValueError: If no root collection has been created for the
          given registered resource.
        """
        ent_cls = get_entity_class(resource)
        root_coll = self.__cache.get(ent_cls)
        if root_coll is None:
            raise ValueError('No root collection available for resource.')
        root_coll.__parent__ = parent

    def load_representation(self, resource, url,
                            content_type=None, resolve_urls=True):
        """
        Load the representation of the specified registered resource from the
        given URL. The new resource is loaded into the resource's root 
        collection.
        
        :param resource: Registered resource.
        :param url: URL to load.
        :param content_type: MIME content type of the representation
        :param resolve_urls: If `true`, links to other resources encountered
          during loading the representation will be resolved.
        :raises RuntimeError: If the repository has not been initialized yet.
        """
        coll = self.get_collection(resource)
        load_into_collection_from_url(coll, url,
                                      content_type=content_type,
                                      resolve_urls=resolve_urls)

    def configure(self, **config):
        """
        Apply the given configuration key:value map to the configuration of 
        this repository.
        
        :raises ValueError: If the configuration map contains keys which are
          not declared in the `_configurables` class variable. 
        """
        for key, val in config.items():
            if not key in self._configurables:
                raise ValueError('Invalid configuration key "%s".' % key)
            self._config[key] = val

    def initialize(self):
        """
        Initializes this repository.
        """
        self.__is_initializing = True
        self._initialize()
        self.__is_initializing = False
        self.__is_initialized = True

    @property
    def session_factory(self):
        if self.__session_factory is None:
            # Create a session factory. The call to _initialize may depend on
            # the session factory being instantiated.
            self.__session_factory = self._make_session_factory()
        return self.__session_factory

    def register_resource(self, resource):
        self.__registered_resources.add(resource)

    @property
    def registered_types(self):
        return [get_entity_class(rc) for rc in self.__registered_resources]

    @property
    def is_initialized(self):
        return self.__is_initialized

    @property
    def name(self):
        return self.__name

    @property
    def configuration(self):
        """
        Returns a copy of the configuration for this entity store.
        """
        return self._config.copy()

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
