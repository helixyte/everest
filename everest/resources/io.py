"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Input/Output operations on resources.

Created on Jan 27, 2012.
"""

from StringIO import StringIO
from everest.mime import CsvMime
from everest.mime import XmlMime
from everest.representers.utils import as_representer
from everest.resources.utils import get_member_class
from everest.resources.utils import new_stage_collection
from everest.resources.utils import provides_member_resource
from everest.utils import OrderedDict
from pygraph.algorithms.sorting import topological_sorting
from pygraph.classes.digraph import digraph
from urlparse import urlparse
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface  # pylint: disable=E0611,F0401
import os

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


def build_resource_dependency_graph(resource_classes,
                                    include_backreferences=False):
    """
    Builds a graph of dependencies among the given resource classes.

    The dependency graph is a directed graph with member resource classes as 
    nodes. An edge between two nodes represents a member or collection
    attribute.
    
    :param resource_classes: resource classes to determine interdependencies
      of.
    :type resource_classes: sequence of registered resources.
    :param bool include_backreferences: flag indicating if dependencies
      introduced by back-references (e.g., a child resource referencing its
      parent) should be included in the dependency graph.
    """
    def visit(mb_cls, grph, path, incl_backrefs):
        for attr_name in mb_cls.get_attribute_names():
            if mb_cls.is_terminal(attr_name):
                continue
            child_descr = getattr(mb_cls, attr_name)
            child_mb_cls = get_member_class(child_descr.entity_type)
            # We do not follow cyclic references back to a resource class
            # that is last in the path.
            if len(path) > 0 and child_mb_cls is path[-1] \
               and not incl_backrefs:
                continue
            if not grph.has_node(child_mb_cls):
                grph.add_node(child_mb_cls)
                path.append(mb_cls)
                visit(child_mb_cls, grph, path, incl_backrefs)
                path.pop()
            if not grph.has_edge((mb_cls, child_mb_cls)):
                grph.add_edge((mb_cls, child_mb_cls))
    dep_grph = digraph()
    for resource_class in resource_classes:
        mb_cls = get_member_class(resource_class)
        if not dep_grph.has_node(mb_cls):
            dep_grph.add_node(mb_cls)
            visit(mb_cls, dep_grph, [], include_backreferences)
    return dep_grph


def build_resource_graph(resource, dependency_graph=None):
    """
    Traverses the graph of resources that is reachable from the given 
    resource.
    
    If a resource dependency graph is given, links to other resources are 
    only followed if the dependency graph has an edge connecting the two 
    corresponding resource classes; otherwise, a default graph is built
    which ignores all direct cyclic resource references. 

    :resource: a :class:`thelma.resources.MemberResource` instance.
    :returns: a :class:`ResourceGraph` instance representing the graph of 
        resources reachable from the given resource.
    """
    def visit(rc, grph, dep_grph):
        mb_cls = type(rc)
        attr_map = mb_cls.get_attributes()
        for attr_name, attr in attr_map.iteritems():
            if mb_cls.is_terminal(attr_name):
                continue
            # Only follow the resource attribute if the dependency graph
            # has an edge here.
            child_mb_cls = get_member_class(attr.value_type)
            if not dep_grph.has_edge((mb_cls, child_mb_cls)):
                continue
            child_rc = getattr(rc, attr_name)
            if mb_cls.is_collection(attr_name):
                for child_mb in child_rc:
                    if not grph.has_node(child_mb): # Ignore cyclic references.
                        grph.add_node(child_mb)
                        grph.add_edge((rc, child_mb))
                        visit(child_mb, grph, dep_grph)
            else: # Member.
                if not grph.has_node(child_rc): # Ignore cyclic references.
                    grph.add_node(child_rc)
                    grph.add_edge((rc, child_rc))
                    visit(child_rc, grph, dep_grph)
    if  dependency_graph is None:
        dependency_graph = build_resource_dependency_graph(
                                            [get_member_class(resource)])
    graph = ResourceGraph()
    if provides_member_resource(resource):
        rcs = [resource]
    else:
        rcs = resource
    for rc in rcs:
        graph.add_node(rc)
        visit(rc, graph, dependency_graph)
    return graph


def find_connected_resources(resource, dependency_graph=None):
    """
    Collects all resources connected to the given resource and returns a 
    dictionary mapping member resource classes to new collections containing
    the members found.
    """
    # Build a resource_graph.
    resource_graph = \
                build_resource_graph(resource,
                                     dependency_graph=dependency_graph)
    # Build an ordered dictionary of collections.
    collections = OrderedDict()
    for mb in topological_sorting(resource_graph):
        mb_cls = get_member_class(mb)
        coll = collections.get(mb_cls)
        if coll is None:
            # Create new collection.
            coll = new_stage_collection(mb)
            collections[mb_cls] = coll
        coll.add(mb)
    return collections


def dump_resource_to_files(resource, content_type=None, directory=None):
    """
    Convenience function. See 
    :meth:`thelma.resources.io.ConnectedResourcesSerializer.to_files` for 
    details.
    """
    srl = ConnectedResourcesSerializer(content_type=content_type)
    srl.to_files(resource, directory=directory)


class ResourceGraph(digraph):
    """
    Specialized digraph for resource instances. 
    
    Nodes are resources, edges represent relationships between resources. 
    Since resources are wrapper objects generated on the fly, the presence 
    of a resource in the graph is determined by its underlying entity, using
    the entity class and its ID as a key.
    """
    def __init__(self):
        digraph.__init__(self)
        self.__entities = set()

    def add_node(self, node, attrs=None):
        digraph.add_node(self, node, attrs=attrs)
        key = self.__make_key(node)
        self.__entities.add(key)

    def del_node(self, node):
        digraph.del_node(self, node)
        key = self.__make_key(node)
        self.__entities.remove(key)

    def has_node(self, node):
        return self.__make_key(node) in self.__entities

    def __make_key(self, obj):
        ent = obj.get_entity()
        return (type(ent), ent.id)


class ConnectedResourcesSerializer(object):
    """
    Serializer for a graph of connected resources.
    """
    def __init__(self, content_type=None, dependency_graph=None):
        """
        :param content_type: MIME content type to use for representations
        :type content_type: object implementing 
            :class:`everest.interfaces.IMime`.
        :param dependency_graph: graph determining which resource connections
            to follow when the graph of connected resources for a given
            resource is built.
        """
        if content_type is None:
            content_type = CsvMime
        self.__content_type = content_type
        self.__dependency_graph = dependency_graph

    def to_strings(self, resource):
        """
        Dumps the all resources reachable from the given resource to a map of 
        string representations using the specified content_type (defaults
        to CSV).
        
        :returns: dictionary mapping resource member classes to string 
            representations
        """
        collections = \
            find_connected_resources(resource,
                                     dependency_graph=self.__dependency_graph)
        # Build a map of representations.
        rpr_map = OrderedDict()
        for (mb_cls, coll) in collections.iteritems():
            stream = StringIO('w')
            dump_resource(coll, stream, content_type=self.__content_type)
            rpr_map[mb_cls] = stream.getvalue()
        return rpr_map

    def to_files(self, resource, directory=None):
        """
        Dumps the given resource and all resources linked to it into a set of
        representation files in the given directory.
        """
        if directory is None:
            directory = os.getcwd()
        rc_map = self.to_strings(resource)
        for mb_cls, rpr_string in rc_map.iteritems():
            fn = '%s-collection.%s' % (mb_cls.relation.split('/')[-1],
                                       self.__content_type.file_extensions[0])
            strm = open(os.path.join(directory, fn), 'wb')
            with strm:
                strm.write(rpr_string)
