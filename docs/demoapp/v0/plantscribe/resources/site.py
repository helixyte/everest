from everest.resources.base import Member
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from plantscribe.interfaces import IIncidence
from plantscribe.interfaces import IProject

class SiteMember(Member):
    relation = 'http://plantscribe.org/relations/site'
    name = terminal_attribute(str, 'name')
    incidences = collection_attribute(IIncidence, backref='site',
                                      is_nested=True)
    project = member_attribute(IProject, 'project')
