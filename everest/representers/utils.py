"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Representer utilities.

Created on May 18, 2011.
"""

from everest.representers.interfaces import IDataElementRegistry
from everest.representers.interfaces import IRepresenter
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401
from zope.component import getUtility as get_utility # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['as_representer',
           'get_data_element_registry',
           ]


def as_representer(resource, content_type_string):
    """
    Adapts the given resource and content type to a representer.

    :param resource: resource to adapt.
    :param str content_type_string: content (MIME) type to create a
        representer for.
    """
    return get_adapter(resource, IRepresenter, content_type_string)


def get_data_element_registry(content_type):
    """
    Returns the data element registry for the given content type (a Singleton).

    :Note: This only works after a representer for the given content type
        has been created.
    """
    return get_utility(IDataElementRegistry, content_type.mime_string)

#def dump_resource_graph(resource, content_type=None):
#    def visit(rc, content_type, depth, visited, collections, depths):
#        if rc in visited:
#            return
#        else:
#            visited.add(rc)
#        mb_cls = get_member_class(rc)
#        coll = collections.get(mb_cls)
#        if coll is None:
#            # Create new collection and store max depth with it.
#            coll = new_stage_collection(resource)
#            collections[mb_cls] = coll
#        max_depth = depths.get(mb_cls)
#        if max_depth is None or max_depth < depth:
#            # Store new max depth with existing collection.
#            depths[mb_cls] = depth
#        if provides_collection_resource(rc):
#            for mb in rc:
#                visit(mb, content_type, depth, visited, collections, depths)
#        else:
#            coll.add(rc)
#            for attr in get_resource_class_attributes(type(rc)):
#                if attr.kind == ResourceAttributeKinds.TERMINAL:
#                    continue
#                next_rc = getattr(rc, attr.name)
#                visit(next_rc, content_type, depth + 1, visited, collections,
#                      depths)
#    if content_type is None:
#        content_type = CsvMime
#    visited = set()
#    collections = {}
#    depths = {}
#    visit(resource, content_type, 1, visited, collections, depths)
#    buf = []
#    for mb_cls in [item[0] for item in sorted(depths.items(),
#                                              cmp=lambda x, y: cmp(y[1], x[1]))]:
#        coll = visited[mb_cls]
#        rpr = as_representer(coll, content_type.mime_string)
#        stream = StringIO('w')
#        buf.append(rpr.to_stream(stream))
#    return buf
