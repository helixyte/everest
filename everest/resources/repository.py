"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The resource repository class.

Created on Jan 13, 2012.
"""

from everest.repository import Repository
from everest.resources.interfaces import ICollectionResource
from everest.resources.io import load_resource_from_url
from everest.resources.utils import get_collection_class
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401
from zope.interface import implementer # pylint: disable=E0611,F0401
from everest.interfaces import IRepository
from everest.resources.persisters import DummyPersister
from everest.entities.repository import EntityRepository
from everest.entities.aggregates import MemoryAggregateImpl

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


@implementer(IRepository)
def new_memory_repository():
    prst = DummyPersister(None)
    ent_repo = EntityRepository(prst)
    ent_repo.set_default_implementation(MemoryAggregateImpl)
    rc_repo = ResourceRepository(ent_repo)
    rc_repo.initialize()
    return rc_repo


