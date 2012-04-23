from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

class Species(Entity):
    def __init__(self, species_name, genus_name,
                 cultivar=None, author=None, **kw):
        Entity.__init__(self, **kw)
        self.species_name = species_name
        self.genus_name = genus_name
        self.cultivar = cultivar
        self.author = author

    @property
    def slug(self):
        return slug_from_string(
                    "%s-%s-%s-%s"
                    % (self.genus_name, self.species_name,
                       '' if self.cultivar is None else self.cultivar,
                       '' if self.author is None else self.author))
