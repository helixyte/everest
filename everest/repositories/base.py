"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from everest.entities.utils import get_entity_class
from everest.repositories.interfaces import IRepository
from everest.resources.utils import get_collection_class
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['AutocommittingSessionMixin',
           'Query',
           'Repository',
           'Session',
           'SessionFactory',
           ]


class SessionFactory(object):
    """
    Base class for session factories.
    """
    def __init__(self, repository):
        self._repository = repository

    def __call__(self):
        raise NotImplementedError('Abstract method.')


class Session(object):
    """
    Abstract base class for session objects.
    """
    def get_by_id(self, entity_class, id_key):
        raise NotImplementedError('Abstract method.')

    def add(self, entity_class, data):
        raise NotImplementedError('Abstract method.')

    def remove(self, entity_class, data):
        raise NotImplementedError('Abstract method.')

    def update(self, entity_class, data):
        raise NotImplementedError('Abstract method.')

    def query(self, entity_class):
        raise NotImplementedError('Abstract method.')


class AutocommittingSessionMixin(object):
    """
    Mixin classes for sessions that wrap every add, remove, and update
    operation into a transaction.
    """
    def add(self, entity_class, data):
        self.begin()
        super(AutocommittingSessionMixin, self).add(entity_class, data)
        self.commit()

    def remove(self, entity_class, data):
        self.begin()
        super(AutocommittingSessionMixin, self).remove(entity_class, data)
        self.commit()

    def update(self, entity_class, source_data, target_entity):
        self.begin()
        updated_entity = super(AutocommittingSessionMixin, self).update(
                                    entity_class, source_data, target_entity)
        self.commit()
        return updated_entity


@implementer(IRepository)
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

    #: A list of key names which can be used by :method:`configure`.
    _configurables = ['messaging_enable', 'messaging_reset_on_start']

    def __init__(self, name, aggregate_class,
                 join_transaction=False, autocommit=False):
        """
        Constructor.

        :param name: Name for this repository (propagated to repository).
        :param aggregate_class: The aggregate class to use when creating new
          aggregates in this repository.
        :param join_transaction: Indicates whether this repository should
          participate in the Zope transaction.
        :param autocommit: Indicates whether changes should be committed
          automatically.
        """
        self.__name = name
        if join_transaction and autocommit:
            raise ValueError('The "join_transaction" flag and the '
                             '"autocommit" flag can not both be set.')
        #: Flag indicating that the sessions using this repository should
        #: join the Zope transaction.
        self.join_transaction = join_transaction
        #: Flag indicating that changes should be committed immediately.
        self.autocommit = autocommit
        self._config = {}
        self.__is_initializing = False
        self.__is_initialized = False
        self.__cache = {}
        self.__agg_cls = aggregate_class
        self.__session_factory = None
        #: The set of resources (collection classes) managed by this
        #: repository.
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
            # Create a new root aggregate.
            root_agg = self.__agg_cls.create(ent_cls, self.session_factory,
                                             self)
            # Create a new root collection.
            coll_cls = get_collection_class(resource)
            root_coll = coll_cls.create_from_aggregate(root_agg)
            self.__cache[ent_cls] = root_coll
        return root_coll.clone()

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
    def is_initialized(self):
        return self.__is_initialized

    @property
    def name(self):
        return self.__name

    @property
    def configuration(self):
        """
        Returns a copy of the configuration for this repository.
        """
        return self._config.copy()

    def _initialize(self):
        """
        Performs initialization of the repository.
        """
        raise NotImplementedError('Abstract method.')

    def _make_session_factory(self):
        """
        Create the session factory for this repository.
        """
        raise NotImplementedError('Abstract method.')


class Query(object):
    """
    Abstract base class for queries.
    """

    def __iter__(self):
        """
        Returns an iterator over all entities in this query after applying
        filtering, ordering, and slicing settings.
        """
        raise NotImplementedError('Abstract method.')

    def count(self):
        """
        Returns the count of the entities in this query.

        :note: This does not take slicing into account.
        """
        raise NotImplementedError('Abstract method.')

    def all(self):
        """
        Returns a list of all entities in this query after applying
        filtering, ordering, and slicing settings.
        """
        raise NotImplementedError('Abstract method.')

    def one(self):
        """
        Returns exactly one result from this query.

        :raises NoResultsException: if no results were found.
        :raises MultipleResultsException: if more than one result was found.
        """
        raise NotImplementedError('Abstract method.')

    def filter(self, filter_expression):
        """
        Sets the filter expression for this query. Generative (returns a
        clone).

        :note: If the query already has a filter expression, the returned
            query will use the conjunction of both expressions.
        """
        raise NotImplementedError('Abstract method.')

    def filter_by(self, **kw):
        """
        Generates an equal-to filter expression and calls :method:`filter`
        with it.
        """
        raise NotImplementedError('Abstract method.')

    def order_by(self, order_expression):
        """
        Sets the order expression for this query. Generative (returns a
        clone).

        :note: If the query already has an order expression, the returned
            query will use the conjunction of both expressions.
        """
        raise NotImplementedError('Abstract method.')

    def slice(self, start, stop):
        """
        Sets the slice key for this query. Generative (returns a clone).
        """
        raise NotImplementedError('Abstract method.')
