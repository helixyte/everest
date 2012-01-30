"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 6, 2012.
"""

from everest.entities.base import Entity
from everest.entities.utils import slug_from_string

__docformat__ = 'reStructuredText en'
__all__ = ['Customer',
           'Incidence',
           'Project',
           'Site',
           'Species',
           ]


class Customer(Entity):
    def __init__(self, first_name, last_name, **kw):
        Entity.__init__(self, **kw)
        self.first_name = first_name
        self.last_name = last_name

    @property
    def slug(self):
        return "%s-%s" % (self.last_name.lower(), self.first_name.lower())


class Project(Entity):
    def __init__(self, name, customer, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.customer = customer

    @property
    def slug(self):
        return slug_from_string(self.name)


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


class Site(Entity):
    def __init__(self, name, project, **kw):
        Entity.__init__(self, **kw)
        self.name = name
        self.project = project

    @property
    def slug(self):
        return slug_from_string(self.name)


class Incidence(Entity):
    def __init__(self, species, site, quantity, **kw):
        Entity.__init__(self, **kw)
        self.species = species
        self.site = site
        self.quantity = quantity

    @property
    def slug(self):
        return self.species.slug
