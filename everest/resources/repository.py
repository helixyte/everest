"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The resource repository class.

Created on Jan 13, 2012.
"""
from everest.entities.aggregates import MemoryAggregate
from everest.entities.aggregates import OrmAggregate
from everest.entities.repository import EntityRepository
from everest.orm import map_system_entities
from everest.repository import REPOSITORIES
from everest.repository import Repository
from everest.resources.entitystores import CachingEntityStore
from everest.resources.entitystores import FileSystemEntityStore
from everest.resources.entitystores import OrmEntityStore
from everest.resources.io import load_collection_from_url
from everest.resources.utils import get_collection_class
from everest.utils import id_generator

__docformat__ = 'reStructuredText en'
__all__ = ['RepositoryManager',
           'ResourceRepository',
           ]


class ResourceRepository(Repository):
    """
    The resource repository manages resource accessors (collections).
    """
    def __init__(self, entity_repository):
        Repository.__init__(self)
        self.__managed_collections = set()
        self.__entity_repository = entity_repository

    def clear(self, rc):
        Repository.clear(self, rc)
        self.__entity_repository.clear(rc)

    def clear_all(self):
        Repository.clear_all(self)
        self.__entity_repository.clear_all()

    def load_representation(self, rc, url,
                            content_type=None, resolve_urls=True):
        coll = self.get(rc)
        load_collection_from_url(coll, url,
                                 content_type=content_type,
                                 resolve_urls=resolve_urls)

    def manage(self, collection_class):
        self.__managed_collections.add(collection_class)

    @property
    def managed_collections(self):
        return self.__managed_collections.copy()

    def configure(self, **config):
        self.__entity_repository.configure(**config)

    def _initialize(self):
        self.__entity_repository.initialize()

    def _new(self, rc):
        agg = self.__entity_repository.new(rc)
        coll_cls = get_collection_class(rc)
        return coll_cls.create_from_aggregate(agg)

    @property
    def is_initialized(self):
        return self.__entity_repository.is_initialized

    @property
    def name(self):
        return self.__entity_repository.name

    @property
    def configuration(self):
        return self.__entity_repository.configuration

    def _make_key(self, rc):
        return get_collection_class(rc)


class RepositoryManager(object):
    __repo_id_gen = id_generator()

    def __init__(self):
        self.__repositories = {}
        self.__default_repo = None
        self.__messaging_repo = None
        self.__messaging_reset_on_start = None

    def get(self, name):
        return self.__repositories.get(name)

    def set(self, repo, make_default=False):
        name = repo.name
        if name in self.__repositories \
           and self.__repositories[name].is_initialized:
            raise ValueError('Can not replace repositories that have been '
                             'initialized.')
        self.__repositories[name] = repo
        if make_default:
            self.__default_repo = repo

    def get_default(self):
        return self.__default_repo

    def new(self, repo_type, name=None,
            entity_store_class=None, aggregate_class=None):
        if name == repo_type:
            # This is a root repository.
            is_root_repository = True
        else:
            is_root_repository = False
            if name is None:
                name = "%s%d" % (repo_type, self.__repo_id_gen.next())
        if repo_type == REPOSITORIES.MEMORY:
            if entity_store_class is None:
                entity_store_class = CachingEntityStore
            if aggregate_class is None:
                aggregate_class = MemoryAggregate
        elif repo_type == REPOSITORIES.ORM:
            if entity_store_class is None:
                entity_store_class = OrmEntityStore
            if aggregate_class is None:
                aggregate_class = OrmAggregate
        elif repo_type == REPOSITORIES.FILE_SYSTEM:
            if entity_store_class is None:
                entity_store_class = FileSystemEntityStore
            if aggregate_class is None:
                aggregate_class = MemoryAggregate
        else:
            raise ValueError('Unknown repository type.')
        ent_store = entity_store_class(name,
                                       join_transaction=is_root_repository)
        ent_repo = EntityRepository(ent_store, aggregate_class=aggregate_class)
        return ResourceRepository(ent_repo)

    def setup_messaging(self, repository, reset_on_start):
        """
        Sets up messaging for the given repository.
        
        :param str repository: Name of the repository to use to store user
          messages. 
        :param bool reset_on_start: Flag to indicate whether stored user 
          messsages should be discarded on startup.
        """
        self.__messaging_repo = repository
        self.__messaging_reset_on_start = reset_on_start

    def initialize_all(self):
        """
        Convenience method to initialize all repositories that have not been
        initialized yet.
        """
        for repo in self.__repositories.itervalues():
            if not repo.is_initialized:
                # If this repo is the one configured for messaging, initialize
                # the message resource.
                if repo.name == self.__messaging_repo:
                    self.__initialize_messaging()
                repo.initialize()

    def __initialize_messaging(self):
        if self.__messaging_repo == REPOSITORIES.ORM:
            # Wrap the metadata callback to also call the mapping function
            # for system entities.
            repo = self.get(self.__messaging_repo)
            md_fac = repo.configuration['metadata_factory']
            def wrapper(engine,
                        reset_on_start=self.__messaging_reset_on_start):
                metadata = md_fac(engine)
                map_system_entities(engine, reset_on_start)
                return metadata
            repo.configure(metadata_factory=wrapper)
