from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from plantscribe.interfaces import ICustomer
from plantscribe.interfaces import ISite
from everest.resources.descriptors import attribute_alias

class ProjectMember(Member):
    relation = 'http://plantscribe.org/relations/project'
    title = attribute_alias('name')
    name = terminal_attribute(str, 'name')
    customer = member_attribute(ICustomer, 'customer')
    sites = collection_attribute(ISite, backref='project', is_nested=True)
