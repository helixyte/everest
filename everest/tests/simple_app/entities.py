from everest.entities.base import Entity


class FooEntity(Entity):
    name = None
    def __init__(self, name=None, **kw):
        Entity.__init__(self, **kw)
        self.name = name

    @property
    def slug(self):
        if self.name is None:
            slug = str(self.id)
        else:
            slug = self.name
        return slug


class BarEntity(Entity):
    pass
