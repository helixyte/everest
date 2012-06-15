"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.interfaces import IMime
from everest.mime import XmlMime
from everest.mime import get_registered_mime_strings
from everest.mime import get_registered_mime_type_for_extension
from everest.mime import get_registered_mime_type_for_string
from everest.mime import get_registered_mime_types
from everest.mime import register_mime_type
from everest.testing import Pep8CompliantTestCase
from zope.interface import classProvides as class_provides # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['MimeTestCase',
           ]


class MimeTestCase(Pep8CompliantTestCase):
    def test_registry(self):
        self.assert_raises(ValueError, register_mime_type,
                           MimeNotImplementingIMime)
        self.assert_raises(ValueError, register_mime_type,
                           MimeWithDuplicateMimeString)
        self.assert_raises(ValueError, register_mime_type,
                           MimeWithDuplicateFileExtensionString)
        self.assert_true(XmlMime.mime_string in get_registered_mime_strings())
        self.assert_true(XmlMime in get_registered_mime_types())
        self.assert_true(
                    get_registered_mime_type_for_string(XmlMime.mime_string)
                    is XmlMime)
        self.assert_equal(
                get_registered_mime_type_for_extension(XmlMime.file_extension),
                XmlMime)


class MimeNotImplementingIMime(object):
    pass


class MimeWithDuplicateMimeString(object):
    class_provides(IMime)
    mime_string = 'application/xml'
    file_extension = 'xmlish'


class MimeWithDuplicateFileExtensionString(object):
    class_provides(IMime)
    mime_string = 'application/xmlish'
    file_extension = '.xml'
