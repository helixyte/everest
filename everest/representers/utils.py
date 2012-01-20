"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Representer utilities.

Created on May 18, 2011.
"""

from StringIO import StringIO
from everest.mime import CsvMime
from everest.mime import XmlMime
from everest.representers.interfaces import IDataElementRegistry
from everest.representers.interfaces import IRepresenter
from everest.resources.attributes import ResourceAttributeKinds
from urlparse import urlparse
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


def data_element_tree_to_string(data_element):
    """
    Creates a string representation of the given data element tree.
    """
    def __dump(data_el, stream, offset):
        name = data_el.__class__.__name__
        stream.write("%s(" % name)
        offset = offset + len(name) + 1
        first_attr = True
        attrs = \
            data_el.mapper.get_mapped_attributes(data_el.mapped_class)
        for attr in attrs.values():
            if first_attr:
                first_attr = False
            else:
                stream.write(',\n' + ' ' * offset)
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                stream.write("%s=%s" % (attr.name,
                                        str(data_el.get_terminal(attr)))
                             )
            else:
                nested_el = data_el.get_nested(attr)
                if attr.kind == ResourceAttributeKinds.COLLECTION:
                    stream.write('%s=[' % attr.name)
                    first_member = True
                    for member_el in nested_el.get_members():
                        if first_member:
                            stream.write('\n' + ' ' * (offset + 2))
                            first_member = False
                        else:
                            stream.write(',\n' + ' ' * (offset + 2))
                        __dump(member_el, stream, offset + 2)
                    stream.write('\n' + ' ' * (offset + 2) + ']')
                else:
                    stream.write("%s=" % attr.name)
                    __dump(nested_el, stream, offset)
        stream.write(')')
    stream = StringIO()
    __dump(data_element, stream, 0)
    return stream.getvalue()


def load_from_url(resource, url, content_type_string=None):
    parsed = urlparse(url)
    if parsed.scheme == 'file': # pylint: disable=E1101
        # Assume a local path.
        rc = load_from_file(resource, parsed.path, # pylint: disable=E1101
                            content_type_string=content_type_string)
    else:
        raise ValueError('Unsupported URL scheme "%s".' % parsed.scheme) # pylint: disable=E1101
    return rc


def load_from_file(resource, filename, content_type_string=None):
    if content_type_string is None:
        #
        extensions = dict(csv=CsvMime,
                          xml=XmlMime,
                          )
        ext = filename.splitext()[1]
        try:
            content_type_string = extensions[ext].mime_string
        except KeyError:
            raise ValueError('Unknown extension for representation.')
    rpr = as_representer(resource, content_type_string)
    fp = open(filename, 'rU')
    with fp:
        rc = rpr.from_stream(fp)
    return rc


