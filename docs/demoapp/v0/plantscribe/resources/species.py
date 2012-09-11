from everest.resources.base import Member
from everest.resources.descriptors import terminal_attribute
from everest.resources.descriptors import attribute_alias

class SpeciesMember(Member):
    relation = 'http://plantscribe.org/relations/species'
    title = attribute_alias('species_name')
    species_name = terminal_attribute(str, 'species_name')
    genus_name = terminal_attribute(str, 'genus_name')
    cultivar = terminal_attribute(str, 'cultivar')
    author = terminal_attribute(str, 'author')
