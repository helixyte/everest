from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

class Customer(Entity):
    def __init__(self, first_name, last_name, **kw):
        Entity.__init__(self, **kw)
        self.first_name = first_name
        self.last_name = last_name

    @property
    def slug(self):
        return slug_from_string("%s-%s" % (self.last_name, self.first_name))
