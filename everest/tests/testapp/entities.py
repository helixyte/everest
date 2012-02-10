from everest.entities.base import Aggregate
from everest.entities.base import Entity


class FooEntity(Entity):
    def __init__(self, name=None, **kw):
        Entity.__init__(self, **kw)
        self.__name = name

    @property
    def slug(self):
        if self.__name is None:
            slug = str(self.id)
        else:
            slug = self.__name
        return slug


class BarEntity(Entity):
    pass


class FooEntityAggregate(Aggregate):
    pass


class BarEntityAggregate(Aggregate):
    pass
