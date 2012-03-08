from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

class Project(Entity):
    def __init__(self, name, customer, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.customer = customer

    @property
    def slug(self):
        return slug_from_string(self.name)
