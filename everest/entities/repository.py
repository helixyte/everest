"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

The entity repository class.

Created on Jan 11, 2012.
"""

from everest.entities.base import Aggregate
from everest.entities.utils import get_aggregate_class
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
    def __init__(self, persister, default_aggregate_implementation_class):
        Repository.__init__(self)
        #
        self.__persister = persister
        #
        self.__default_agg_impl_cls = default_aggregate_implementation_class

    def new(self, rc):
        agg_cls = get_aggregate_class(rc)
        entity_cls = get_entity_class(rc)
        if issubclass(agg_cls, Aggregate):
            # Normal case - we have an Aggregate wrapper class. Use the 
            # default aggregate implementation for this repository.
            impl_cls = self.__default_agg_impl_cls
            impl = impl_cls.create(entity_cls,
                                   self.__persister.session_factory())
            agg = agg_cls.create(impl)
        else:
            # Special case - customized AggregateImpl class; use directly.
            agg = agg_cls.create(entity_cls,
                                 self.__persister.session_factory())
        return agg

    def configure(self, **config):
        self.__persister.configure(**config)

    def initialize(self):
        self.__persister.initialize()

    @property
    def is_initialized(self):
        return self.__persister.is_initialized

    def _make_key(self, rc):
        return get_aggregate_class(rc)
