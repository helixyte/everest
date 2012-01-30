"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 27, 2012.
"""

from StringIO import StringIO
from abc import WeakSet
from everest.mime import CsvMime
from everest.mime import XmlMime
from everest.representers.utils import as_representer
from everest.resources.utils import get_member_class
from everest.resources.utils import new_stage_collection
from everest.utils import OrderedDict
from pygraph.algorithms.sorting import topological_sorting
from pygraph.classes.digraph import digraph
from urlparse import urlparse
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = []

def load_from_url(resource, url, content_type=None):
    parsed = urlparse(url)
    if parsed.scheme == 'file': # pylint: disable=E1101
        # Assume a local path.
        rc = load_from_file(resource, parsed.path, # pylint: disable=E1101
                            content_type=content_type)
    else:
        raise ValueError('Unsupported URL scheme "%s".' % parsed.scheme) # pylint: disable=E1101
    return rc


def load_from_file(resource, filename, content_type=None):
    if content_type is None:
        #
        extensions = dict(csv=CsvMime,
                          xml=XmlMime,
                          )
        ext = filename.split('.')[1]
        try:
            content_type = extensions[ext]
        except KeyError:
            raise ValueError('Unknown file extension "%s".' % ext)
    if IInterface in provided_by(resource):
        coll_cls = get_utility(resource, name='collection-class')
    else:
        coll_cls = resource
    rpr = as_representer(object.__new__(coll_cls),
                         content_type.mime_string)
    fp = open(filename, 'rU')
    with fp:
        rc = rpr.from_stream(fp)
    return rc


class ResourceGraph(digraph):
    """
    Specialized digraph for resources. 
    
    Nodes are resources, edges represent relationships between resources. 
    Since resources are wrapper objects generated on the fly, the presence 
    of a resource in the graph is determined by its underlying entity.
    """
    def __init__(self):
        digraph.__init__(self)
        self.__entities = WeakSet()

    def add_node(self, node, attrs=None):
        digraph.add_node(self, node, attrs=attrs)
        self.__entities.add(node.get_entity())

    def del_node(self, node):
        digraph.del_node(self, node)
        self.__entities.remove(node.get_entity())

    def has_node(self, node):
        return node.get_entity() in self.__entities


def build_resource_graph(resource):
    """
    Traverses the graph of resources that is reachable from the given resource,
    ignoring cyclic references.
    """
    def visit(rc, grph):
        # We ignore cyclic references.
        mb_cls = type(rc)
        for attr_name in mb_cls.get_attribute_names():
            if mb_cls.is_terminal(attr_name):
                continue
            child_rc = getattr(rc, attr_name)
            if mb_cls.is_collection(attr_name):
                for child_mb in child_rc:
                    if not grph.has_node(child_mb): # Ignore cyclic references.
                        grph.add_node(child_mb)
                        grph.add_edge((rc, child_mb))
                        visit(child_mb, grph)
            else: # Member.
                if not grph.has_node(child_rc): # Ignore cyclic references.
                    grph.add_node(child_rc)
                    grph.add_edge((rc, child_rc))
                    visit(child_rc, grph)
    graph = ResourceGraph()
    graph.add_node(resource)
    visit(resource, graph)
    return graph


def dump_resource(resource, content_type=None):
    """
    Dumps the visited resources in the specified content_type (defaults
    to CSV).
    """
    if content_type is None:
        content_type = CsvMime
    collections = OrderedDict()
    graph = build_resource_graph(resource)
    for mb in topological_sorting(graph):
        mb_cls = get_member_class(mb)
        coll = collections.get(mb_cls)
        if coll is None:
            # Create new collection and store max depth with it.
            coll = new_stage_collection(mb)
            collections[mb_cls] = coll
        coll.add(mb)
    repr_map = {}
    for (mb_cls, coll) in collections.iteritems():
        rpr = as_representer(coll, content_type.mime_string)
        stream = StringIO('w')
        rpr.to_stream(coll, stream)
        repr_map[mb_cls] = stream.getvalue()
    return repr_map

