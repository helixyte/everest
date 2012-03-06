from everest.entities.base import Entity

class Customer(Entity):
    def __init__(self, first_name, last_name, **kw):
        Entity.__init__(self, **kw)
        self.first_name = first_name
        self.last_name = last_name

    @property
    def slug(self):
        return "%s-%s" % (self.last_name.lower(), self.first_name.lower())
