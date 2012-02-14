"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The resource repository class.

Created on Jan 13, 2012.
"""

from everest.entities.aggregates import MemoryAggregateImpl
from everest.entities.aggregates import OrmAggregateImpl
from everest.entities.repository import EntityRepository
from everest.repository import REPOSITORIES
from everest.repository import Repository
from everest.resources.interfaces import ICollectionResource
from everest.resources.io import load_resource_from_url
from everest.resources.persisters import DummyPersister
from everest.resources.persisters import FileSystemPersister
from everest.resources.persisters import OrmPersister
from everest.resources.utils import get_collection_class
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceRepository',
           ]


class ResourceRepository(Repository):
    """
    The resource repository manages resource accessors (collections).
    """
    def __init__(self, entity_repository):
        Repository.__init__(self)
        self.__managed_collections = set()
        self.__entity_repository = entity_repository

    def new(self, rc):
        agg = self.__entity_repository.new(rc)
        return get_adapter(agg, ICollectionResource)

    def clear(self, rc):
        Repository.clear(self, rc)
        self.__entity_repository.clear(rc)

    def clear_all(self):
        Repository.clear_all(self)
        self.__entity_repository.clear_all()

    def load_representation(self, rc, url, content_type=None):
        loaded_coll = load_resource_from_url(rc, url,
                                             content_type=content_type)
        coll = self.get(rc)
        for loaded_mb in loaded_coll:
            coll.add(loaded_mb)

    def get_entity_repository(self):
        return self.__entity_repository

    def manage(self, collection_class):
        self.__managed_collections.add(collection_class)

    @property
    def managed_collections(self):
        return self.__managed_collections.copy()

    def configure(self, **config):
        self.__entity_repository.configure(**config)

    def initialize(self):
        self.__entity_repository.initialize()

    @property
    def is_initialized(self):
        return self.__entity_repository.is_initialized

    def _make_key(self, rc):
        return get_collection_class(rc)


class RepositoryManager(object):
    def __init__(self):
        self.__repositories = {}
        self.__default_repo = None

    def get(self, name):
        return self.__repositories.get(name)

    def set(self, name, repo, make_default=False):
        if name in self.__repositories \
           and self.__repositories[name].is_initialized:
            raise ValueError('Can not replace repositories that have been '
                             'initialized.')
        self.__repositories[name] = repo
        if make_default:
            self.__default_repo = repo

    def get_default(self):
        return self.__default_repo

    def initialize(self):
        for repo in self.__repositories.itervalues():
            repo.initialize()

    def new(self, repo_type,
            name=None, persister_class=None,
            default_aggregate_implementation_class=None):
        if name is None:
            # This is a builtin repository.
            name = repo_type
        if repo_type == REPOSITORIES.MEMORY:
            if persister_class is None:
                persister_class = DummyPersister
            if default_aggregate_implementation_class is None:
                default_aggregate_implementation_class = MemoryAggregateImpl
        elif repo_type == REPOSITORIES.ORM:
            if persister_class is None:
                persister_class = OrmPersister
            if default_aggregate_implementation_class is None:
                default_aggregate_implementation_class = OrmAggregateImpl
        elif repo_type == REPOSITORIES.FILE_SYSTEM:
            if persister_class is None:
                persister_class = FileSystemPersister
            if default_aggregate_implementation_class is None:
                default_aggregate_implementation_class = MemoryAggregateImpl
        else:
            raise ValueError('Unknown repository type.')
        prst = persister_class(name)
        ent_repo = EntityRepository(prst,
                                    default_aggregate_implementation_class=
                                        default_aggregate_implementation_class)
        return ResourceRepository(ent_repo)

    def __check_name(self, name):
        if name in self.__repositories:
            raise ValueError('Duplicate repository name.')

