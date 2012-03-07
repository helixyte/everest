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
    first_name = terminal_attribute(str, 'first_name')
    last_name = terminal_attribute(str, 'last_name')
    projects = collection_attribute(IProject, backref='customer')


class ProjectMember(Member):
    relation = 'http://plantscribe.org/relations/project'
    name = terminal_attribute(str, 'name')
    customer = member_attribute(ICustomer, 'customer')
    sites = collection_attribute(ISite, backref='project', is_nested=True)


class SpeciesMember(Member):
    relation = 'http://plantscribe.org/relations/species'
    species_name = terminal_attribute(str, 'species_name')
    genus_name = terminal_attribute(str, 'genus_name')
    cultivar = terminal_attribute(str, 'cultivar')
    author = terminal_attribute(str, 'author')


class SpeciesCollection(Collection):
    title = 'Species.'
    root_name = 'species'


class SiteMember(Member):
    relation = 'http://plantscribe.org/relations/site'
    name = terminal_attribute(str, 'name')
    incidences = collection_attribute(IIncidence, backref='site',
                                      is_nested=True)
    project = member_attribute(IProject, 'project')


class IncidenceMember(Member):
    relation = 'http://plantscribe.org/relations/incidence'
    species = member_attribute(ISpecies, 'species')
    site = member_attribute(ISite, 'site')
    quantity = terminal_attribute(float, 'quantity')
