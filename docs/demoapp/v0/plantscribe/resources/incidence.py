from everest.resources.base import Member
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from plantscribe.interfaces import ISite
from plantscribe.interfaces import ISpecies

class IncidenceMember(Member):
    relation = 'http://plantscribe.org/relations/incidence'
    species = member_attribute(ISpecies, 'species')
    site = member_attribute(ISite, 'site')
    quantity = terminal_attribute(float, 'quantity')
