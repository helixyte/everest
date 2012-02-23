"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Input/Output operations on resources.

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
from pygraph.algorithms.searching import depth_first_search

__docformat__ = 'reStructuredText en'
__all__ = ['dump_resource',
           'dump_resource_graph',
           'load_resource_from_file',
           'load_resource_from_url',
           ]


def load_resource_from_url(resource, url,
                           content_type=None, resolve_urls=True):
    """
    Loads a collection resource of the given registered resource type from a 
    representation contained in the given URL.
    
    :returns: collection resource
    """
    parsed = urlparse(url)
    if parsed.scheme == 'file': # pylint: disable=E1101
        # Assume a local path.
        rc = load_resource_from_file(resource, parsed.path, # pylint: disable=E1101
                                     content_type=content_type,
                                     resolve_urls=resolve_urls)
    else:
        raise ValueError('Unsupported URL scheme "%s".' % parsed.scheme) # pylint: disable=E1101
    return rc


def load_resource_from_file(resource, filename,
                            content_type=None, resolve_urls=True):
    """
    Loads a collection resource of the given registered resource type from a 
    representation contained in the given file name.
    
    :returns: collection resource
    """
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
        data_el = rpr.data_from_stream(fp)
    rc = rpr.resource_from_data(data_el, resolve_urls=resolve_urls)
    return rc


def dump_resource(resource, stream, content_type=None):
    """
    Dumps the given resource to the given stream using the specified MIME
    content type (defaults to CSV). If no stream is provided, a 
    :class:`StringIO` stream is returned.
    """
    if content_type is None:
        content_type = CsvMime
    rpr = as_representer(resource, content_type.mime_string)
    rpr.to_stream(resource, stream)


class ResourceGraph(digraph):
    """
    Specialized digraph for resource instances. 
    
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

    :resource: a :class:`thelma.resources.MemberResource` instance.
    :returns: a :class:`ResourceGraph` instance representing the graph of 
      resources reachable from the given resource.
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


def build_resource_dependency_graph(resource_classes):
    def visit(mb_cls, grph):
        for attr_name in mb_cls.get_attribute_names():
            if mb_cls.is_terminal(attr_name):
                continue
            child_descr = getattr(mb_cls, attr_name)
            child_mb_cls = get_member_class(child_descr.entity_type)
            if not grph.has_node(child_mb_cls):
                grph.add_node(child_mb_cls)
                visit(child_mb_cls, grph)
            if not grph.has_edge((mb_cls, child_mb_cls)):
                grph.add_edge((mb_cls, child_mb_cls))
    graph = digraph()
    for resource_class in resource_classes:
        mb_cls = get_member_class(resource_class)
        if not graph.has_node(mb_cls):
            graph.add_node(mb_cls)
            visit(mb_cls, graph)
    return graph


def dump_resource_graph(resource, content_type=None):
    """
    Dumps the all resources reachable from the given resource to a map of 
    string representations using the specified content_type (defaults
    to CSV).
    
    :returns: dictionary mapping resource member classes to string 
      representations
    """
    collections = OrderedDict()
    graph = build_resource_graph(resource)
    for mb in topological_sorting(graph):
        mb_cls = get_member_class(mb)
        coll = collections.get(mb_cls)
        if coll is None:
            # Create new collection.
            coll = new_stage_collection(mb)
            collections[mb_cls] = coll
        coll.add(mb)
    repr_map = {}
    for (mb_cls, coll) in collections.iteritems():
        stream = StringIO('w')
        dump_resource(coll, stream, content_type=content_type)
        repr_map[mb_cls] = stream.getvalue()
    return repr_map


def load_order(resource_classes):
    """
    Returns the given resource classes in an order that permits loading
    them from representations.
    
    Currently, this is implemented with a depth-first traversal of a
    directed resource dependency graph built from the given resource
    classes.
    
    :note: Cyclic resource dependencies are not handled very well.
    """
    grph = build_resource_dependency_graph(resource_classes)
    post_order = depth_first_search(grph)[2]
    return post_order
