from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import terminal_attribute
from plantscribe.interfaces import IProject
from everest.resources.descriptors import attribute_alias

class CustomerMember(Member):
    relation = 'http://plantscribe.org/relations/customer'
    title = attribute_alias('last_name')
    first_name = terminal_attribute(str, 'first_name')
    last_name = terminal_attribute(str, 'last_name')
    projects = collection_attribute(IProject, backref='customer')
