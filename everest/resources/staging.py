"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 27, 2013.
"""
from everest.constants import RELATION_OPERATIONS
from everest.entities.base import Aggregate
from everest.entities.base import RelationshipAggregate
from everest.entities.traversal import AruVisitor
from everest.entities.utils import get_entity_class
from everest.querying.base import EXPRESSION_KINDS
from everest.repositories.memory.cache import EntityCacheMap
from everest.resources.utils import get_collection_class
from everest.traversers import SourceTargetDataTreeTraverser

__docformat__ = 'reStructuredText en'
__all__ = ['StagingAggregate',
           'create_staging_collection',
           ]


class StagingAggregate(Aggregate):
    """
    Staging aggregate.

    A staging aggregate is used to build up a new set of entities of the same
    type e.g. from a representation. It does not have a session and therefore
    has no way to persist the changes that are made to the entities it holds.
    """

    def __init__(self, entity_class, cache=None):
        Aggregate.__init__(self)
        self.entity_class = entity_class
        if cache is None:
            cache = EntityCacheMap()
        self.__cache = cache
        self.__visitor = AruVisitor(entity_class, self.__cache.add,
                                    self.__cache.remove, self.__cache.update)

    def get_by_id(self, id_key):
        return self.__cache[self.entity_class].get_by_id(id_key)

    def get_by_slug(self, slug):
        return self.__cache[self.entity_class].get_by_slug(slug)

    def add(self, entity):
        trv = SourceTargetDataTreeTraverser.make_traverser(
                                                entity,
                                                RELATION_OPERATIONS.ADD,
                                                accessor=self)
        trv.run(self.__visitor)

    def remove(self, entity):
        trv = SourceTargetDataTreeTraverser.make_traverser(
                                                entity,
                                                RELATION_OPERATIONS.REMOVE,
                                                accessor=self)
        trv.run(self.__visitor)

    def update(self, entity):
        trv = SourceTargetDataTreeTraverser.make_traverser(
                                                entity,
                                                RELATION_OPERATIONS.UPDATE,
                                                accessor=self)
        trv.run(self.__visitor)
        return self.__visitor.root

    def query(self):
        return self.__cache.query(self.entity_class)

    @property
    def expression_kind(self):
        return EXPRESSION_KINDS.EVAL

    def get_root_aggregate(self, rc):
        ent_cls = get_entity_class(rc)
        return StagingAggregate(ent_cls, cache=self.__cache)

    def make_relationship_aggregate(self, relationship):
        return RelationshipAggregate(self, relationship)


def create_staging_collection(resource):
    """
    Helper function to create a staging collection for the given registered
    resource.

    :param resource: registered resource
    :type resource: class implementing or instance providing or subclass of
        a registered resource interface.
    """
    ent_cls = get_entity_class(resource)
    coll_cls = get_collection_class(resource)
    agg = StagingAggregate(ent_cls)
    return coll_cls.create_from_aggregate(agg)
