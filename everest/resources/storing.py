"""
Input/Output operations on resources.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 27, 2012.
"""
from collections import OrderedDict
import os
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from pyramid.compat import NativeIO
from pyramid.compat import iteritems_
from pyramid.compat import text_type
from pyramid.compat import urlparse

from everest.compat import open_text
from everest.entities.utils import get_entity_class
from everest.mime import CsvMime
from everest.mime import MimeTypeRegistry
from everest.repositories.memory.cache import EntityCacheMap
from everest.representers.utils import as_representer
from everest.resources.attributes import get_resource_class_attribute_names
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.attributes import is_resource_class_collection_attribute
from everest.resources.attributes import is_resource_class_terminal_attribute
from everest.resources.staging import StagingAggregate
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import provides_member_resource
from pygraph.algorithms.sorting import topological_sorting # pylint: disable=E0611,F0401
from pygraph.classes.digraph import digraph # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['ConnectedResourcesSerializer',
           'ResourceGraph',
           'build_resource_dependency_graph',
           'build_resource_graph',
           'dump_resource',
           'dump_resource_to_files',
           'dump_resource_to_zipfile',
           'find_connected_resources',
           'get_collection_filename',
           'get_collection_name',
           'get_read_collection_path',
           'get_write_collection_path',
           'load_collection_from_file',
           'load_collection_from_stream',
           'load_collection_from_url',
           'load_into_collection_from_file',
           'load_into_collection_from_stream',
           'load_into_collection_from_url',
           'load_into_collections_from_zipfile',
           ]


def load_into_collection_from_stream(collection, stream, content_type):
    """
    Loads resources from the given resource data stream (of the specified MIME
    content type) into the given collection resource.
    """
    rpr = as_representer(collection, content_type)
    with stream:
        data_el = rpr.data_from_stream(stream)
    rpr.resource_from_data(data_el, resource=collection)


def load_collection_from_stream(resource, stream, content_type):
    """
    Creates a new collection for the registered resource and calls
    `load_into_collection_from_stream` with it.
    """
    coll = create_staging_collection(resource)
    load_into_collection_from_stream(coll, stream, content_type)
    return coll


def load_into_collection_from_file(collection, filename,
                                   content_type=None):
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
    load_into_collection_from_stream(collection, open(filename, 'rU'),
                                     content_type)


def load_collection_from_file(resource, filename, content_type=None):
    """
    Creates a new collection for the registered resource and calls
    `load_into_collection_from_file` with it.
    """
    coll = create_staging_collection(resource)
    load_into_collection_from_file(coll, filename,
                                   content_type=content_type)
    return coll


def load_into_collection_from_url(collection, url, content_type=None):
    """
    Loads resources from the representation contained in the given URL into
    the given collection resource.

    :returns: collection resource
    """
    parsed = urlparse.urlparse(url)
    scheme = parsed.scheme # pylint: disable=E1101
    if scheme == 'file':
        # Assume a local path.
        load_into_collection_from_file(collection,
                                       parsed.path, # pylint: disable=E1101
                                       content_type=content_type)
    else:
        raise ValueError('Unsupported URL scheme "%s".' % scheme)


def load_collection_from_url(resource, url, content_type=None):
    """
    Creates a new collection for the registered resource and calls
    `load_into_collection_from_url` with it.
    """
    coll = create_staging_collection(resource)
    load_into_collection_from_url(coll, url, content_type=content_type)
    return coll


class DecodingStream(object):
    """
    Helper class that iterates over a bytes stream yielding strings.
    """
    def __init__(self, stream, encoding='utf-8'):
        self.__stream = stream
        self.__encoding = encoding

    def __enter__(self):
        return self.__stream.__enter__()

    def __exit__(self, *args, **kw):
        self.__stream.__exit__(*args, **kw)

    def __iter__(self):
        for line in self.__stream:
            yield text_type(line, self.__encoding)


def load_into_collections_from_zipfile(collections, zipfile):
    """
    Loads resources contained in the given ZIP archive into each of the
    given collections.

    The ZIP file is expected to contain a list of file names obtained with
    the :func:`get_collection_filename` function, each pointing to a file
    of zipped collection resource data.

    :param collections: sequence of collection resources
    :param str zipfile: ZIP file name
    """
    with ZipFile(zipfile) as zipf:
        names = zipf.namelist()
        name_map = dict([(os.path.splitext(name)[0], index)
                         for (index, name) in enumerate(names)])
        for coll in collections:
            coll_name = get_collection_name(coll)
            index = name_map.get(coll_name)
            if index is None:
                continue
            coll_fn = names[index]
            ext = os.path.splitext(coll_fn)[1]
            try:
                content_type = \
                    MimeTypeRegistry.get_type_for_extension(ext)
            except KeyError:
                raise ValueError('Could not infer MIME type for file '
                                 'extension "%s".' % ext)
            # Strings are always written as UTF-8 encoded byte strings when
            # the zip file is created, so we have to wrap the iterator into
            # a decoding step.
            coll_data = DecodingStream(zipf.open(coll_fn, 'r'))
            load_into_collection_from_stream(coll,
                                             coll_data,
                                             content_type)


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
        for attr_name in get_resource_class_attribute_names(mb_cls):
            if is_resource_class_terminal_attribute(mb_cls, attr_name):
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

    :resource: a :class:`everest.resources.MemberResource` instance.
    :returns: a :class:`ResourceGraph` instance representing the graph of
        resources reachable from the given resource.
    """
    def visit(rc, grph, dep_grph):
        mb_cls = type(rc)
        attr_map = get_resource_class_attributes(mb_cls)
        for attr_name, attr in iteritems_(attr_map):
            if is_resource_class_terminal_attribute(mb_cls, attr_name):
                continue
            # Only follow the resource attribute if the dependency graph
            # has an edge here.
            child_mb_cls = get_member_class(attr.attr_type)
            if not dep_grph.has_edge((mb_cls, child_mb_cls)):
                continue
            child_rc = getattr(rc, attr_name)
            if is_resource_class_collection_attribute(mb_cls, attr_name):
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
    entity_map = OrderedDict()
    for mb in topological_sorting(resource_graph):
        mb_cls = get_member_class(mb)
        ents = entity_map.get(mb_cls)
        if ents is None:
            ents = []
            entity_map[mb_cls] = ents
        ents.append(mb.get_entity())
    return entity_map


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

    def __collect(self, resource):
        ent_cls = get_entity_class(resource)
        coll_cls = get_collection_class(resource)
        cache = EntityCacheMap()
        agg = StagingAggregate(ent_cls, cache)
        coll = coll_cls.create_from_aggregate(agg)
        coll.add(resource)
        return dict([(get_member_class(ent_cls),
                      coll.get_root_collection(ent_cls))
                     for ent_cls in cache.keys()])

    def to_strings(self, resource):
        """
        Dumps the all resources reachable from the given resource to a map of
        string representations using the specified content_type (defaults
        to CSV).

        :returns: dictionary mapping resource member classes to string
            representations
        """
        collections = self.__collect(resource)
        # Build a map of representations.
        rpr_map = OrderedDict()
        for (mb_cls, coll) in iteritems_(collections):
            strm = NativeIO('w')
            dump_resource(coll, strm, content_type=self.__content_type)
            rpr_map[mb_cls] = strm.getvalue()
        return rpr_map

    def to_files(self, resource, directory):
        """
        Dumps the given resource and all resources linked to it into a set of
        representation files in the given directory.
        """
        collections = self.__collect(resource)
        for (mb_cls, coll) in iteritems_(collections):
            fn = get_write_collection_path(mb_cls,
                                           self.__content_type,
                                           directory=directory)
            with open_text(os.path.join(directory, fn)) as strm:
                dump_resource(coll, strm, content_type=self.__content_type)

    def to_zipfile(self, resource, zipfile):
        """
        Dumps the given resource and all resources linked to it into the given
        ZIP file.
        """
        rpr_map = self.to_strings(resource)
        with ZipFile(zipfile, 'w') as zipf:
            for (mb_cls, rpr_string) in iteritems_(rpr_map):
                fn = get_collection_filename(mb_cls, self.__content_type)
                zipf.writestr(fn, rpr_string, compress_type=ZIP_DEFLATED)


def dump_resource_to_files(resource, content_type=None, directory=None):
    """
    Convenience function. See
    :meth:`everest.resources.io.ConnectedResourcesSerializer.to_files` for
    details.

    If no directory is given, the current working directory is used.
    The given context type defaults to CSV.
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
    :meth:`everest.resources.io.ConnectedResourcesSerializer.to_zipfile` for
    details.

    The given context type defaults to CSV.
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
