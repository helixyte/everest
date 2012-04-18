"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

MIME (content) types.

Created on Aug 17, 2011.
"""

from everest.interfaces import IAtomEntryMime
from everest.interfaces import IAtomFeedMime
from everest.interfaces import IAtomMime
from everest.interfaces import IAtomRequest
from everest.interfaces import IAtomServiceMime
from everest.interfaces import ICsvMime
from everest.interfaces import ICsvRequest
from everest.interfaces import IHtmlMime
from everest.interfaces import IHtmlRequest
from everest.interfaces import IJsonMime
from everest.interfaces import IJsonRequest
from everest.interfaces import ITextPlainMime
from everest.interfaces import IXlsMime
from everest.interfaces import IXlsRequest
from everest.interfaces import IXmlMime
from everest.interfaces import IXmlRequest
from everest.interfaces import IZipRequest
from everest.interfaces import IZipMime
from zope.interface import implements # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['JSON_MIME',
           'ATOM_MIME',
           'ATOM_FEED_MIME',
           'ATOM_ENTRY_MIME',
           'XML_MIME',
           'CSV_MIME',
           'ZIP_MIME',
           'MIME_REQUEST',
           'get_registered_mime_strings',
           'get_registered_mime_type_for_string',
           'get_registered_mime_types',
           ]


class MimeTypeRegistry(object):

    __mime_string_map = {}
    __file_extension_map = {}

    @classmethod
    def register(cls, mime_type):
        if mime_type.mime_string in cls.__mime_string_map:
            raise ValueError('Duplicate MIME string detected.')
        for ext in mime_type.file_extensions:
            if ext in cls.__file_extension_map:
                raise ValueError('Duplicate file extension detected.')
        cls.__mime_string_map[mime_type.mime_string] = mime_type
        for ext in mime_type.file_extensions:
            cls.__file_extension_map[ext] = mime_type

    @classmethod
    def get_strings(cls):
        return cls.__mime_string_map.keys()

    @classmethod
    def get_types(cls):
        return cls.__mime_string_map.values()

    @classmethod
    def get_type_for_string(cls, mime_string):
        return cls.__mime_string_map[mime_string]


register_mime_type = MimeTypeRegistry.register
get_registered_mime_strings = MimeTypeRegistry.get_strings
get_registered_mime_types = MimeTypeRegistry.get_types
get_registered_mime_type_for_string = MimeTypeRegistry.get_type_for_string


class JsonMime(object):
    implements(IJsonMime)
    mime_string = 'application/json'
    file_extensions = ['.json']

JSON_MIME = JsonMime.mime_string

register_mime_type(JsonMime)


class AtomMime(object):
    implements(IAtomMime)
    mime_string = 'application/atom+xml'
    file_extensions = ['.atom']

ATOM_MIME = AtomMime.mime_string

register_mime_type(AtomMime)


class AtomFeedMime(AtomMime):
    implements(IAtomFeedMime)
    mime_string = 'application/atom+xml;type=feed'

ATOM_FEED_MIME = AtomFeedMime.mime_string


class AtomEntryMime(AtomMime):
    implements(IAtomEntryMime)
    mime_string = 'application/atom+xml;type=entry'

ATOM_ENTRY_MIME = AtomFeedMime.mime_string


class AtomServiceMime(AtomMime):
    implements(IAtomServiceMime)
    mime_string = 'application/atomsvc+xml'

ATOM_SERVICE_MIME = AtomFeedMime.mime_string


class XmlMime(object):
    implements(IXmlMime)
    mime_string = 'application/xml'
    file_extensions = ['.xml']

XML_MIME = XmlMime.mime_string

register_mime_type(XmlMime)


class CsvMime(object):
    implements(ICsvMime)
    mime_string = 'application/csv'
    file_extensions = ['.csv']

CSV_MIME = CsvMime.mime_string

register_mime_type(CsvMime)


class HtmlMime(object):
    implements(IHtmlMime)
    mime_string = 'text/html'
    file_extensions = ['.html', '.htm']

HTML_MIME = HtmlMime.mime_string

register_mime_type(HtmlMime)


class TextPlainMime(object):
    implements(ITextPlainMime)
    mime_string = 'text/plain'
    file_extensions = ['.txt']

TEXT_PLAIN_MIME = TextPlainMime.mime_string

register_mime_type(TextPlainMime)


class XlsMime(object):
    implements(IXlsMime)
    mime_string = 'application/vnd.xls'
    file_extensions = ['.xls']

XLS_MIME = XlsMime.mime_string

register_mime_type(XlsMime)


class ZipMime(object):
    implements(IZipMime)
    mime_string = 'application/zip'
    file_extensions = ['.zip']

ZIP_MIME = ZipMime.mime_string

register_mime_type(ZipMime)


MIME_REQUEST = {JSON_MIME : IJsonRequest,
                ATOM_MIME : IAtomRequest,
                ATOM_FEED_MIME : IAtomRequest,
                ATOM_ENTRY_MIME : IAtomRequest,
                ATOM_SERVICE_MIME : IAtomRequest,
                XML_MIME : IXmlRequest,
                CSV_MIME : ICsvRequest,
                HTML_MIME : IHtmlRequest,
                XLS_MIME : IXlsRequest,
                ZIP_MIME : IZipRequest,
                }
