"""
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
           ]


class JsonMime(object):
    implements(IJsonMime)
    mime_string = 'application/json'

JSON_MIME = JsonMime.mime_string

class AtomMime(object):
    implements(IAtomMime)
    mime_string = 'application/atom+xml'

ATOM_MIME = AtomMime.mime_string

class AtomFeedMime(object):
    implements(IAtomFeedMime)
    mime_string = 'application/atom+xml;type=feed'

ATOM_FEED_MIME = AtomFeedMime.mime_string

class AtomEntryMime(object):
    implements(IAtomEntryMime)
    mime_string = 'application/atom+xml;type=entry'

ATOM_ENTRY_MIME = AtomFeedMime.mime_string

class AtomServiceMime(object):
    implements(IAtomServiceMime)
    mime_string = 'application/atomsvc+xml'

ATOM_SERVICE_MIME = AtomFeedMime.mime_string

class XmlMime(object):
    implements(IXmlMime)
    mime_string = 'application/xml'

XML_MIME = XmlMime.mime_string

class CsvMime(object):
    implements(ICsvMime)
    mime_string = 'application/csv'

CSV_MIME = CsvMime.mime_string

class HtmlMime(object):
    implements(IHtmlMime)
    mime_string = 'text/html'

HTML_MIME = HtmlMime.mime_string

class TextPlainMime(object):
    implements(ITextPlainMime)
    mime_string = 'text/plain'

TEXT_PLAIN_MIME = TextPlainMime.mime_string

class XlsMime(object):
    implements(IXlsMime)
    mime_string = 'application/vnd.xls'

XLS_MIME = XlsMime.mime_string

class ZipMime(object):
    implements(IZipMime)
    mime_string = 'application/zip'

ZIP_MIME = ZipMime.mime_string

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
