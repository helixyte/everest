from everest.entities.base import Aggregate
from everest.entities.base import Entity


class FooEntity(Entity):

    def __init__(self, **kw):
        Entity.__init__(self, **kw)
        self.atomic = 123
        self.entity = BarEntity()
        self.entity_collection = [BarEntity() for dummy in range(5)]

    @property
    def slug(self):
        return "%s%s" % (self.__class__.__name__, self.id)


class BarEntity(Entity):

    @property
    def slug(self):
        return "%s%s" % (self.__class__.__name__, self.id)


class FooEntityAggregate(Aggregate):
    pass


class BarEntityAggregate(Aggregate):
    pass
