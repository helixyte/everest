from everest.entities.base import Entity

class Incidence(Entity):
    def __init__(self, species, site, quantity, **kw):
        Entity.__init__(self, **kw)
        self.species = species
        self.site = site
        self.quantity = quantity

    @property
    def slug(self):
        return None if self.species is None else self.species.slug
