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
from everest.interfaces import IMime
from everest.interfaces import ITextPlainMime
from everest.interfaces import IXlsMime
from everest.interfaces import IXlsRequest
from everest.interfaces import IXmlMime
from everest.interfaces import IXmlRequest
from everest.interfaces import IZipMime
from everest.interfaces import IZipRequest
from everest.utils import BidirectionalLookup
from zope.interface import classProvides as class_provides # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

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
    __file_extension_map = BidirectionalLookup()

    @classmethod
    def register(cls, mime_type):
        if not [ifc for ifc in provided_by(mime_type)
                if issubclass(ifc, IMime)]:
            raise ValueError('MIME type to register must implement the '
                             'IMime interface.')
        if mime_type.mime_string in cls.__mime_string_map:
            raise ValueError('Duplicate MIME string detected.')
        if mime_type.file_extension in cls.__file_extension_map:
            raise ValueError('Duplicate file extension detected.')
        cls.__mime_string_map[mime_type.mime_string] = mime_type
        cls.__file_extension_map[mime_type.file_extension] = mime_type

    @classmethod
    def get_strings(cls):
        return cls.__mime_string_map.keys()

    @classmethod
    def get_types(cls):
        return cls.__mime_string_map.values()

    @classmethod
    def get_type_for_string(cls, mime_string):
        return cls.__mime_string_map[mime_string]

    @classmethod
    def get_type_for_extension(cls, file_extension):
        return cls.__file_extension_map[file_extension]


register_mime_type = MimeTypeRegistry.register
get_registered_mime_strings = MimeTypeRegistry.get_strings
get_registered_mime_types = MimeTypeRegistry.get_types
get_registered_mime_type_for_string = MimeTypeRegistry.get_type_for_string
get_registered_mime_type_for_extension = \
                                    MimeTypeRegistry.get_type_for_extension


class JsonMime(object):
    class_provides(IJsonMime)
    mime_string = 'application/json'
    file_extension = '.json'

JSON_MIME = JsonMime.mime_string

register_mime_type(JsonMime)


class AtomMime(object):
    class_provides(IAtomMime)
    mime_string = 'application/atom+xml'
    file_extension = '.atom'

ATOM_MIME = AtomMime.mime_string

register_mime_type(AtomMime)


class AtomFeedMime(AtomMime):
    class_provides(IAtomFeedMime)
    mime_string = 'application/atom+xml;type=feed'

ATOM_FEED_MIME = AtomFeedMime.mime_string


class AtomEntryMime(AtomMime):
    class_provides(IAtomEntryMime)
    mime_string = 'application/atom+xml;type=entry'

ATOM_ENTRY_MIME = AtomFeedMime.mime_string


class AtomServiceMime(AtomMime):
    class_provides(IAtomServiceMime)
    mime_string = 'application/atomsvc+xml'

ATOM_SERVICE_MIME = AtomFeedMime.mime_string


class XmlMime(object):
    class_provides(IXmlMime)
    mime_string = 'application/xml'
    file_extension = '.xml'

XML_MIME = XmlMime.mime_string

register_mime_type(XmlMime)


class CsvMime(object):
    class_provides(ICsvMime)
    mime_string = 'application/csv'
    file_extension = '.csv'

CSV_MIME = CsvMime.mime_string

register_mime_type(CsvMime)


class HtmlMime(object):
    class_provides(IHtmlMime)
    mime_string = 'text/html'
    file_extension = '.html'

HTML_MIME = HtmlMime.mime_string

register_mime_type(HtmlMime)


class TextPlainMime(object):
    class_provides(ITextPlainMime)
    mime_string = 'text/plain'
    file_extension = '.txt'

TEXT_PLAIN_MIME = TextPlainMime.mime_string

register_mime_type(TextPlainMime)


class XlsMime(object):
    class_provides(IXlsMime)
    mime_string = 'application/vnd.xls'
    file_extension = '.xls'

XLS_MIME = XlsMime.mime_string

register_mime_type(XlsMime)


class ZipMime(object):
    class_provides(IZipMime)
    mime_string = 'application/zip'
    file_extension = '.zip'

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
