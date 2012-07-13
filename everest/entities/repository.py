"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The entity repository class.

Created on Jan 11, 2012.
"""
from everest.entities.utils import get_entity_class
from everest.repository import Repository

__docformat__ = 'reStructuredText en'
__all__ = ['EntityRepository',
           ]


class EntityRepository(Repository):
    """
    The entity repository manages entity accessors (aggregates).
    
    In addition to creating and caching aggregates, the entity repository
    also provides facilities to interact with the aggregate implementation
    registry. This makes it possible to switch the implementation used for 
    freshly created aggregates at runtime.
    """
    def __init__(self, entity_store, aggregate_class):
        Repository.__init__(self)
        #: The class to use when creating new aggregates.
        self.aggregate_class = aggregate_class
        # The underlying entity store.
        self.__entity_store = entity_store

    def configure(self, **config):
        self.__entity_store.configure(**config)

    def _initialize(self):
        self.__entity_store.initialize()

    def _new(self, rc):
        entity_cls = get_entity_class(rc)
        session_factory = self.__entity_store.session_factory
        agg = self.aggregate_class.create(entity_cls, session_factory)
        return agg

    @property
    def is_initialized(self):
        return self.__entity_store.is_initialized

    @property
    def name(self):
        return self.__entity_store.name

    @property
    def configuration(self):
        return self.__entity_store.configuration

    def _make_key(self, rc):
        return get_entity_class(rc)
