"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Input/Output operations on resources.

Created on Jan 27, 2012.
"""
from StringIO import StringIO
from everest.mime import CsvMime
from everest.mime import MimeTypeRegistry
from everest.representers.utils import as_representer
from everest.resources.utils import get_member_class
from everest.resources.utils import new_stage_collection
from everest.resources.utils import provides_member_resource
from collections import OrderedDict
from pygraph.algorithms.sorting import topological_sorting # pylint: disable=E0611,F0401
from pygraph.classes.digraph import digraph # pylint: disable=E0611,F0401
from urlparse import urlparse
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile
import os

__docformat__ = 'reStructuredText en'
__all__ = ['build_resource_dependency_graph',
           'build_resource_graph',
           'dump_resource',
           'dump_resource_graph',
           'dump_resource_to_files',
           'dump_resource_to_zipfile',
           'find_connected_resources',
           'load_collection_from_file',
           'load_collection_from_url',
           ]


def load_collection_from_url(collection, url,
                             content_type=None, resolve_urls=True):
    """
    Loads a collection resource of the given registered resource type from a 
    representation contained in the given URL.
    
    :returns: collection resource
    """
    parsed = urlparse(url)
    if parsed.scheme == 'file': # pylint: disable=E1101
        # Assume a local path.
        load_collection_from_file(collection, parsed.path, # pylint: disable=E1101
                                  content_type=content_type,
                                  resolve_urls=resolve_urls)
    else:
        raise ValueError('Unsupported URL scheme "%s".' % parsed.scheme) # pylint: disable=E1101


def load_collection_from_file(collection, filename,
                              content_type=None, resolve_urls=True):
    """
    Loads resources from the specified file into the given collection
    resource.
    
    If no content type is provided, an attempt is made to look up the 
    extension of the given filename in the MIME content type registry.
    """
    if content_type is None:
        ext = os.path.splitext(filename)[1]
        try:
            content_type = MimeTypeRegistry.get_type_for_extension(ext)
        except KeyError:
            raise ValueError('Could not infer MIME type for file extension '
                             '"%s".' % ext)
    load_collection_from_stream(collection, open(filename, 'rU'),
                                content_type, resolve_urls=resolve_urls)


def load_collection_from_stream(collection, stream, content_type,
                                resolve_urls=True):
    """
    Loads resources from the given stream into the given collection resource.
    """
    rpr = as_representer(collection, content_type)
    with stream:
        data_el = rpr.data_from_stream(stream)
    mem_coll = rpr.resource_from_data(data_el, resolve_urls=resolve_urls)
    for mb in mem_coll:
        collection.add(mb)


def load_collections_from_zipfile(collections, zipfile, resolve_urls=True):
    """
    Loads resources contained in the given ZIP archive into each of the
    given collections. 
    
    The ZIP file is expected to contain a list of file names obtained with
    the :func:`get_collection_filename` function, each pointing to a file
    of zipped collection resource data.
    
    :param collections: sequence of collection resources
    :param str zipfile: ZIP file name
    :param bool resolve_urls: Flag indicating if URLs should be resolved 
      during loading.
    """
    with ZipFile(zipfile) as zipf:
        names = zipf.namelist()
        name_map = dict([(os.path.splitext(name)[0], index)
                         for (index, name) in enumerate(names)])
        for collection in collections:
            coll_name = get_collection_name(collection)
            index = name_map.get(coll_name)
            if index is None:
                continue
            coll_fn = names[index]
            ext = os.path.splitext(coll_fn)[1]
            try:
                content_type = MimeTypeRegistry.get_type_for_extension(ext)
            except KeyError:
                raise ValueError('Could not infer MIME type for file '
                                 'extension "%s".' % ext)
            load_collection_from_stream(collection, zipf.open(coll_fn, 'r'),
                                        content_type,
                                        resolve_urls=resolve_urls)


def dump_resource(resource, stream, content_type=None):
    """
    Dumps the given resource to the given stream using the specified MIME
    content type (defaults to CSV).
    """
    if content_type is None:
        content_type = CsvMime
    rpr = as_representer(resource, content_type)
    rpr.to_stream(resource, stream)


def build_resource_dependency_graph(resource_classes,
                                    include_backrefs=False):
    """
    Builds a graph of dependencies among the given resource classes.

    The dependency graph is a directed graph with member resource classes as 
    nodes. An edge between two nodes represents a member or collection
    attribute.
    
    :param resource_classes: resource classes to determine interdependencies
      of.
    :type resource_classes: sequence of registered resources.
    :param bool include_backrefs: flag indicating if dependencies
      introduced by back-references (e.g., a child resource referencing its
      parent) should be included in the dependency graph.
    """
    def visit(mb_cls, grph, path, incl_backrefs):
        for attr_name in mb_cls.get_attribute_names():
            if mb_cls.is_terminal(attr_name):
                continue
            child_descr = getattr(mb_cls, attr_name)
            child_mb_cls = get_member_class(child_descr.attr_type)
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
            visit(mb_cls, dep_grph, [], include_backrefs)
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

#    def del_node(self, node):
#        digraph.del_node(self, node)
#        key = self.__make_key(node)
#        self.__entities.remove(key)

    def has_node(self, node):
        return self.__make_key(node) in self.__entities

    def __make_key(self, obj):
        ent = obj.get_entity()
        return (type(ent), ent.id)


class ConnectedResourcesSerializer(object):
    """
    Serializer for a graph of connected resources.
    """
    def __init__(self, content_type, dependency_graph=None):
        """
        :param content_type: MIME content type to use for representations
        :type content_type: object implementing 
            :class:`everest.interfaces.IMime`.
        :param dependency_graph: graph determining which resource connections
            to follow when the graph of connected resources for a given
            resource is built.
        """
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
            strm = StringIO('w')
            dump_resource(coll, strm, content_type=self.__content_type)
            rpr_map[mb_cls] = strm.getvalue()
        return rpr_map

    def to_files(self, resource, directory):
        """
        Dumps the given resource and all resources linked to it into a set of
        representation files in the given directory.
        """
        collections = \
            find_connected_resources(resource,
                                     dependency_graph=self.__dependency_graph)
        for (mb_cls, coll) in collections.iteritems():
            fn = get_write_collection_path(mb_cls,
                                           self.__content_type,
                                           directory=directory)
            with open(os.path.join(directory, fn), 'wb') as strm:
                dump_resource(coll, strm, content_type=self.__content_type)

    def to_zipfile(self, resource, zipfile):
        """
        Dumps the given resource and all resources linked to it into the given
        ZIP file.
        """
        rpr_map = self.to_strings(resource)
        with ZipFile(zipfile, 'w') as zipf:
            for (mb_cls, rpr_string) in rpr_map.iteritems():
                fn = get_collection_filename(mb_cls, self.__content_type)
                zipf.writestr(fn, rpr_string, compress_type=ZIP_DEFLATED)


def dump_resource_to_files(resource, content_type=None, directory=None):
    """
    Convenience function. See 
    :meth:`thelma.resources.io.ConnectedResourcesSerializer.to_files` for 
    details.
    
    If no directory is given, the current working directory is used. 
    The :param:`content_type` defaults to CSV.
    """
    if directory is None:
        directory = os.getcwd() # pragma: no cover
    if content_type is None:
        content_type = CsvMime
    srl = ConnectedResourcesSerializer(content_type)
    srl.to_files(resource, directory=directory)


def dump_resource_to_zipfile(resource, zipfile, content_type=None):
    """
    Convenience function. See 
    :meth:`thelma.resources.io.ConnectedResourcesSerializer.to_zipfile` for 
    details.
    
    The :param:`content_type` defaults to CSV.
    """
    if content_type is None:
        content_type = CsvMime
    srl = ConnectedResourcesSerializer(content_type)
    srl.to_zipfile(resource, zipfile)


def get_collection_name(rc_class):
    coll_cls = get_member_class(rc_class)
    collection_name = coll_cls.relation.split('/')[-1]
    return "%s-collection" % collection_name


def get_collection_filename(rc_class, content_type=None):
    if content_type is None:
        content_type = CsvMime
    return "%s%s" % (get_collection_name(rc_class),
                     content_type.file_extension)


def get_write_collection_path(collection_class, content_type, directory=None):
    if directory is None:
        directory = os.getcwd() # pragma: no cover
    coll_fn = get_collection_filename(collection_class, content_type)
    return os.path.join(directory, coll_fn)


def get_read_collection_path(collection_class, content_type, directory=None):
    if directory is None:
        directory = os.getcwd() # pragma: no cover
    coll_fn = get_collection_filename(collection_class, content_type)
    fn = os.path.join(directory, coll_fn)
    if os.path.isfile(fn):
        result = fn
    else:
        result = None
    return result
