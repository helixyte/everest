"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 9, 2012.
"""

from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from plantscribe.interfaces import ICustomer
from plantscribe.interfaces import IIncidence
from plantscribe.interfaces import IProject
from plantscribe.interfaces import ISite
from plantscribe.interfaces import ISpecies

__docformat__ = 'reStructuredText en'
__all__ = ['CustomerMember',
           'IncidenceMember',
           'ProjectMember',
           'SiteMember',
           'SpeciesMember',
           ]


class CustomerMember(Member):
    relation = 'http://plantscribe.org/relations/customer'
    first_name = terminal_attribute('first_name', str)
    last_name = terminal_attribute('last_name', str)
    projects = collection_attribute('projects',
                                    IProject, backref_attr='customer')


class CustomerCollection(Collection):
    title = 'Customers.'
    root_name = 'customers'
    description = 'Collection of customers.'


class ProjectMember(Member):
    relation = 'http://plantscribe.org/relations/project'
    name = terminal_attribute('name', str)
    customer = member_attribute('customer', ICustomer)
    sites = collection_attribute('sites', ISite,
                                 backref_attr='project',
                                 is_nested=True)


class ProjectCollection(Collection):
    title = 'Projects.'
    root_name = 'projects'


class SpeciesMember(Member):
    relation = 'http://plantscribe.org/relations/species'
    species_name = terminal_attribute('species_name', str)
    genus_name = terminal_attribute('genus_name', str)
    cultivar = terminal_attribute('cultivar', str)
    author = terminal_attribute('author', str)


class SpeciesCollection(Collection):
    title = 'Species.'
    root_name = 'species'


class SiteMember(Member):
    relation = 'http://plantscribe.org/relations/site'
    name = terminal_attribute('name', str)
    incidences = collection_attribute('incidences', IIncidence,
                                      backref_attr='site',
                                      is_nested=True)
    project = member_attribute('project', IProject)


class SiteCollection(Collection):
    title = 'Sites.'


class IncidenceMember(Member):
    relation = 'http://plantscribe.org/relations/incidence'
    species = member_attribute('species', ISpecies)
    site = member_attribute('site', ISite)
    quantity = terminal_attribute('quantity', float)


class IncidenceCollection(Collection):
    title = 'Incidences.'
