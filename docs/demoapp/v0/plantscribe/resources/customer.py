from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import terminal_attribute
from plantscribe.interfaces import IProject

class CustomerMember(Member):
    relation = 'http://plantscribe.org/relations/customer'
    first_name = terminal_attribute(str, 'first_name')
    last_name = terminal_attribute(str, 'last_name')
    projects = collection_attribute(IProject, backref='customer')
