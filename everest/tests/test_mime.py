"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.interfaces import IMime
from everest.mime import XmlMime
from everest.mime import get_registered_mime_strings
from everest.mime import get_registered_mime_type_for_extension
from everest.mime import get_registered_mime_type_for_name
from everest.mime import get_registered_mime_type_for_string
from everest.mime import get_registered_mime_types
from everest.mime import get_registered_representer_names
from everest.mime import register_mime_type
from everest.testing import Pep8CompliantTestCase
from zope.interface import provider # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['MimeTestCase',
           ]


class MimeTestCase(Pep8CompliantTestCase):
    def test_registry(self):
        self.assert_raises(ValueError, register_mime_type,
                           MimeNotImplementingIMime)
        self.assert_raises(ValueError, register_mime_type,
                           MimeWithDuplicateTypeString)
        self.assert_raises(ValueError, register_mime_type,
                           MimeWithDuplicateNameString)
        self.assert_raises(ValueError, register_mime_type,
                           MimeWithDuplicateFileExtensionString)
        self.assert_true(XmlMime.mime_type_string
                                        in get_registered_mime_strings())
        self.assert_true(XmlMime.representer_name
                                        in get_registered_representer_names())
        self.assert_true(XmlMime in get_registered_mime_types())
        self.assert_true(
                get_registered_mime_type_for_string(XmlMime.mime_type_string)
                is XmlMime)
        self.assert_true(
                get_registered_mime_type_for_name(XmlMime.representer_name)
                is XmlMime)
        self.assert_equal(
                get_registered_mime_type_for_extension(XmlMime.file_extension),
                XmlMime)


class MimeNotImplementingIMime(object):
    pass


@provider(IMime)
class MimeWithDuplicateTypeString(object):
    mime_type_string = 'application/xml'
    representer_name = 'myxml'
    file_extension = 'xmlish'


@provider(IMime)
class MimeWithDuplicateNameString(object):
    mime_type_string = 'application/xmlish'
    representer_name = 'xml'
    file_extension = '.xmlish'


@provider(IMime)
class MimeWithDuplicateFileExtensionString(object):
    mime_type_string = 'application/xmlish'
    representer_name = 'myxml'
    file_extension = '.xml'
