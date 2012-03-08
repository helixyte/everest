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
        return "%s-%s-%s-%s" \
        % (slug_from_string(self.genus_name),
           slug_from_string(self.species_name),
           not self.cultivar is None and slug_from_string(self.cultivar) or '',
           not self.author is None and slug_from_string(self.author) or '')
