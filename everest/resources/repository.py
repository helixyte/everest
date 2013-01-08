"""
Resource repository.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 13, 2012.
"""
from everest.datastores.filesystem import DataStore as FileSystemDataStore
from everest.datastores.memory import DataStore as MemoryDataStore
from everest.datastores.orm import DataStore as OrmDataStore
from everest.datastores.memory import Aggregate as MemoryAggregate
from everest.datastores.orm import Aggregate as OrmAggregate
from everest.entities.repository import EntityRepository
from everest.repository import REPOSITORY_DOMAINS
from everest.repository import REPOSITORY_TYPES
from everest.repository import Repository
from everest.resources.io import load_into_collection_from_url
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
        load_into_collection_from_url(coll, url,
                                      content_type=content_type,
                                      resolve_urls=resolve_urls)

    def register_resource(self, resource):
        self.__entity_repository.register_resource(resource)

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
    """
    The repository manager creates, initializes and holds resource 
    repositories by name.
    """
    __repo_id_gen = id_generator()

    def __init__(self):
        self.__repositories = {}
        self.__default_repo = None

    def get(self, name):
        return self.__repositories.get(name)

    def set(self, repo):
        name = repo.name
        if name in self.__repositories \
           and self.__repositories[name].is_initialized:
            raise ValueError('Can not replace repositories that have been '
                             'initialized.')
        self.__repositories[name] = repo

    def get_default(self):
        return self.__default_repo

    def new(self, repo_type, name=None, make_default=False,
            entity_store_class=None, aggregate_class=None,
            configuration=None):
        if name == REPOSITORY_DOMAINS.ROOT:
            # Unless explicitly configured differently, all root repositories
            # join the transaction.
            join_transaction = True
            autocommit = False
            name = repo_type
        else:
            join_transaction = False
            if name is None:
                name = "%s%d" % (repo_type, self.__repo_id_gen.next())
            # The system repository is special in that its entity store
            # should not join the transaction but still commit all changes.
            autocommit = name == REPOSITORY_DOMAINS.SYSTEM
        if repo_type == REPOSITORY_TYPES.MEMORY:
            if entity_store_class is None:
                entity_store_class = MemoryDataStore
            if aggregate_class is None:
                aggregate_class = MemoryAggregate
        elif repo_type == REPOSITORY_TYPES.ORM:
            if entity_store_class is None:
                entity_store_class = OrmDataStore
            if aggregate_class is None:
                aggregate_class = OrmAggregate
        elif repo_type == REPOSITORY_TYPES.FILE_SYSTEM:
            if entity_store_class is None:
                entity_store_class = FileSystemDataStore
            if aggregate_class is None:
                aggregate_class = MemoryAggregate
        else:
            raise ValueError('Unknown repository type.')
        ent_store = entity_store_class(name,
                                       join_transaction=join_transaction,
                                       autocommit=autocommit)
        ent_repo = EntityRepository(ent_store,
                                    aggregate_class=aggregate_class)
        rc_repo = ResourceRepository(ent_repo)
        if not configuration is None:
            rc_repo.configure(**configuration)
        if make_default:
            self.__default_repo = rc_repo
        return rc_repo

    def setup_system_repository(self, repository_type, reset_on_start):
        """
        Sets up the system repository with the given repository type.
        
        :param str repository: Repository type to use for the SYSTEM 
          repository.
        :param bool reset_on_start: Flag to indicate whether stored system
          resources should be discarded on startup.
        """
        # Set up the system entity repository (this does not join the
        # transaction and is in autocommit mode).
        cnf = dict(messaging_enable=True,
                   messaging_reset_on_start=reset_on_start)
        system_repo = self.new(repository_type,
                               name=REPOSITORY_DOMAINS.SYSTEM,
                               configuration=cnf)
        self.set(system_repo)

    def initialize_all(self):
        """
        Convenience method to initialize all repositories that have not been
        initialized yet.
        """
        for repo in self.__repositories.itervalues():
            if not repo.is_initialized:
                repo.initialize()

    def on_app_created(self, event):  # pylint: disable=W0613
        self.initialize_all()

