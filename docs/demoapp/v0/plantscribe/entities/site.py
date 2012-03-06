from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

class Site(Entity):
    def __init__(self, name, project, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.project = project

    @property
    def slug(self):
        return slug_from_string(self.name)
