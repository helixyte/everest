"""
MIME (content) types.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

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
__all__ = ['ATOM_MIME',
           'ATOM_FEED_MIME',
           'ATOM_ENTRY_MIME',
           'MIME_REQUEST',
           'CSV_MIME',
           'HTML_MIME',
           'JSON_MIME',
           'TEXT_PLAIN_MIME',
           'XLS_MIME',
           'XML_MIME',
           'ZIP_MIME',
           'AtomMime',
           'CsvMime',
           'HtmlMime',
           'JsonMime',
           'TextPlainMime',
           'XlsMime',
           'XmlMime',
           'ZipMime',
           'get_registered_mime_strings',
           'get_registered_mime_type_for_extension',
           'get_registered_mime_type_for_name',
           'get_registered_mime_type_for_string',
           'get_registered_mime_types',
           'get_registered_representer_names',
           ]


class MimeTypeRegistry(object):

    __type_string_map = {}
    __rpr_name_map = {}
    __file_extension_map = BidirectionalLookup()

    @classmethod
    def register(cls, mime_type):
        if not [ifc for ifc in provided_by(mime_type)
                if issubclass(ifc, IMime)]:
            raise ValueError('MIME type to register must implement the '
                             'IMime interface.')
        if mime_type.mime_type_string in cls.__type_string_map:
            raise ValueError('Duplicate MIME string detected.')
        if mime_type.representer_name in cls.__rpr_name_map:
            raise ValueError('Duplicate MIME name detected.')
        if mime_type.file_extension in cls.__file_extension_map:
            raise ValueError('Duplicate file extension detected.')
        cls.__type_string_map[mime_type.mime_type_string] = mime_type
        cls.__rpr_name_map[mime_type.representer_name] = mime_type
        cls.__file_extension_map[mime_type.file_extension] = mime_type

    @classmethod
    def get_types(cls):
        return cls.__type_string_map.values()

    @classmethod
    def get_strings(cls):
        return cls.__type_string_map.keys()

    @classmethod
    def get_names(cls):
        return cls.__rpr_name_map.keys()

    @classmethod
    def get_type_for_string(cls, mime_type_string):
        return cls.__type_string_map[mime_type_string]

    @classmethod
    def get_type_for_name(cls, representer_name):
        return cls.__rpr_name_map[representer_name]

    @classmethod
    def get_type_for_extension(cls, file_extension):
        return cls.__file_extension_map[file_extension]


register_mime_type = MimeTypeRegistry.register
get_registered_mime_strings = MimeTypeRegistry.get_strings
get_registered_representer_names = MimeTypeRegistry.get_names
get_registered_mime_types = MimeTypeRegistry.get_types
get_registered_mime_type_for_string = MimeTypeRegistry.get_type_for_string
get_registered_mime_type_for_name = MimeTypeRegistry.get_type_for_name
get_registered_mime_type_for_extension = \
                                    MimeTypeRegistry.get_type_for_extension


class JsonMime(object):
    class_provides(IJsonMime)
    mime_type_string = 'application/json'
    representer_name = 'json'
    file_extension = '.json'

JSON_MIME = JsonMime.mime_type_string

register_mime_type(JsonMime)


class AtomMime(object):
    class_provides(IAtomMime)
    mime_type_string = 'application/atom+xml'
    representer_name = 'atom'
    file_extension = '.atom'

ATOM_MIME = AtomMime.mime_type_string

register_mime_type(AtomMime)


class AtomFeedMime(AtomMime):
    class_provides(IAtomFeedMime)
    mime_type_string = 'application/atom+xml;type=feed'

ATOM_FEED_MIME = AtomFeedMime.mime_type_string


class AtomEntryMime(AtomMime):
    class_provides(IAtomEntryMime)
    mime_type_string = 'application/atom+xml;type=entry'

ATOM_ENTRY_MIME = AtomFeedMime.mime_type_string


class AtomServiceMime(AtomMime):
    class_provides(IAtomServiceMime)
    mime_type_string = 'application/atomsvc+xml'

ATOM_SERVICE_MIME = AtomFeedMime.mime_type_string


class XmlMime(object):
    class_provides(IXmlMime)
    mime_type_string = 'application/xml'
    representer_name = 'xml'
    file_extension = '.xml'

XML_MIME = XmlMime.mime_type_string

register_mime_type(XmlMime)


class CsvMime(object):
    class_provides(ICsvMime)
    mime_type_string = 'application/csv'
    representer_name = 'csv'
    file_extension = '.csv'

CSV_MIME = CsvMime.mime_type_string

register_mime_type(CsvMime)


class HtmlMime(object):
    class_provides(IHtmlMime)
    mime_type_string = 'text/html'
    file_extension = '.html'

HTML_MIME = HtmlMime.mime_type_string


class TextPlainMime(object):
    class_provides(ITextPlainMime)
    mime_type_string = 'text/plain'
    file_extension = '.txt'

TEXT_PLAIN_MIME = TextPlainMime.mime_type_string


class XlsMime(object):
    class_provides(IXlsMime)
    mime_type_string = 'application/vnd.xls'
    file_extension = '.xls'

XLS_MIME = XlsMime.mime_type_string


class ZipMime(object):
    class_provides(IZipMime)
    mime_type_string = 'application/zip'
    file_extension = '.zip'

ZIP_MIME = ZipMime.mime_type_string


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
