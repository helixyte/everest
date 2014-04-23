"""
Repository base classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 5, 2013.
"""
from everest.entities.utils import get_entity_class
from everest.repositories.interfaces import IRepository
from everest.resources.base import Collection
from everest.resources.utils import get_collection_class
from zope.interface import implementer # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['AutocommittingSessionMixin',
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
    #: Flag to indicate whether session operations need to update back
    #: references.
    IS_MANAGING_BACKREFERENCES = None

    def get_by_id(self, entity_class, id_key):
        """
        Retrieves the entity for the specified entity class and ID.

        :param entity_class: the type of the entity to retrieve.
        :param id_key: ID of the entity to retrieve.
        """
        raise NotImplementedError('Abstract method.')

    def get_by_slug(self, entity_class, slug):
        """
        Retrieves the entity for the specified entity class and slug.

        :param entity_class: the type of the entity to retrieve.
        :param slug: slug of the entity to retrieve.
        """
        raise NotImplementedError('Abstract method.')

    def add(self, entity_class, data):
        """
        Adds the given entity of the given entity class to the session.

        At the point an entity is added, it must not have an ID or a slug
        of another entity that is already in the session. However, both the ID
        and the slug may be ``None`` values.

        :param data: Any object that can be adapted to
          :class:`everest.interfaces.IDataTraversalProxyAdapter` or an
          iterable of such objects.
        """
        raise NotImplementedError('Abstract method.')

    def remove(self, entity_class, data):
        """
        Removes the specified of the given entity class from the session.

        :param data: Any object that can be adapted to
          :class:`everest.interfaces.IDataTraversalProxyAdapter` or an
          iterable of such objects.
        :raises ValueError: If the entity data does not provide an ID
            (unless it is marked NEW).
        """
        raise NotImplementedError('Abstract method.')

    def update(self, entity_class, data, target=None):
        """
        Updates an existing entity with the given entity data. If
        :param:`target_data` not given, the target entity will be determined
        through the ID supplied with the data.

        :param data: Any object that can be adapted to
          :class:`everest.interfaces.IDataTraversalProxyAdapter` or an
          iterable of such objects.
        :raises ValueError: If no target is given and the session does not
          contain an entity with the ID provided with the data.
        """
        raise NotImplementedError('Abstract method.')

    def query(self, entity_class):
        raise NotImplementedError('Abstract method.')

    def begin(self):
        raise NotImplementedError('Abstract method.')

    def commit(self):
        raise NotImplementedError('Abstract method.')

    def rollback(self):
        raise NotImplementedError('Abstract method.')

    def reset(self):
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

    def update(self, entity_class, data, target=None):
        self.begin()
        spr = super(AutocommittingSessionMixin, self)
        updated_entity = spr.update(entity_class, data, target=target)
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
        self.__is_initialized = False
        self.__cache = {}
        self.__agg_cls = aggregate_class
        self.__session_factory = None
        #: The set of resources (collection classes) managed by this
        #: repository.
        self.__registered_resources = set()

    def get_aggregate(self, resource):
        return self.get_collection(resource).get_aggregate()

    def get_collection(self, resource):
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
        for key, val in config.items():
            if not key in self._configurables:
                raise ValueError('Invalid configuration key "%s".' % key)
            self._config[key] = val

    @property
    def configuration(self):
        return self._config.copy()

    def initialize(self):
        self._initialize()
        self.__is_initialized = True

    @property
    def is_initialized(self):
        return self.__is_initialized

    def register_resource(self, resource):
        if not issubclass(resource, Collection):
            resource = get_collection_class(resource)
        self.__registered_resources.add(resource)

    @property
    def registered_resources(self):
        return iter(self.__registered_resources)

    def is_registered_resource(self, resource):
        return get_collection_class(resource) in self.__registered_resources

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

    def reset(self):
        if not self.__session_factory is None:
            self.__session_factory().reset()
        self.__cache.clear()
        self._reset()
        self.__is_initialized = False

    def _initialize(self):
        """
        Performs initialization of the repository.
        """
        raise NotImplementedError('Abstract method.')

    def _reset(self):
        """
        Performs reset of the repository.
        """
        raise NotImplementedError('Abstract method.')

    def _make_session_factory(self):
        """
        Create the session factory for this repository.
        """
        raise NotImplementedError('Abstract method.')
