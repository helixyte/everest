"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.schema import Bool # pylint: disable=E0611,F0401
from zope.schema import List # pylint: disable=E0611,F0401
from zope.schema import Text # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['IAtomMime',
           'IAtomEntryMime',
           'IAtomFeedMime',
           'IAtomRequest',
           'IAtomServiceMime',
           'ICsvMime',
           'ICsvRequest',
           'IHtmlRequest',
           'IHtmlMime',
           'IJsonMime',
           'IJsonRequest',
           'IXmlMime',
           'IXmlRequest',
           'IXlsMime',
           'IXlsRequest',
           'IZipMime'
           ]

# no self, no __init__, no args  pylint: disable=E0213,W0232,E0211

class IJsonRequest(Interface):
    """Marker interface for a JSON request."""


class IAtomRequest(Interface):
    """Marker interface for an ATOM request."""


class IXmlRequest(Interface):
    """Marker interface for an XML request."""


class ICsvRequest(Interface):
    """Marker interface for an request."""


class IHtmlRequest(Interface):
    """Marker interface for a HTML request."""


class IXlsRequest(Interface):
    """Marker interface for an Excel request."""


class IZipRequest(Interface):
    """Marker interface for an Zip compressed request."""


class IMime(Interface):
    """Base Interface for all MIME content types."""
    mime_string = Text(title=u'MIME string for this MIME content type.')
    file_extensions = List(title=u'Known file extensions for this MIME '
                                  'content type.')

class IJsonMime(IMime):
    """Interface for JSON mime type."""


class IAtomMime(IMime):
    """Interface for ATOM mime type."""


class IXmlMime(IMime):
    """Interface for XML mime type."""


class ICsvMime(IMime):
    """Interface for CSV mime type."""


class IXlsMime(IMime):
    """Interface for Excel mime type."""


class IZipMime(IMime):
    """Interface for Zip compressed mime type."""


class IHtmlMime(IMime):
    """Interface for HTML mime type."""


class ITextPlainMime(IMime):
    """Interface for Plain Text mime type."""


class IAtomFeedMime(Interface):
    """Marker interface for ATOM feed mime type."""


class IAtomEntryMime(Interface):
    """Marker interface for ATOM entry mime type."""


class IAtomServiceMime(Interface):
    """Marker interface for ATOM service mime type."""


class IResourceUrlConverter(Interface):
    def url_to_resource(url):
        """Performs URL -> resource conversion."""
    def resource_to_url(resource):
        """Performs URL -> resource conversion."""


class IRepository(Interface):
    """
    Interface for object repositories.
    
    The repository manages accessors for resources or entities. 
    """

    def new(rc):
        """
        Creates a new queryable accessor for the registered resource.
        """

    def get(rc):
        """
        Returns a queryable accessor for the registered resource. If necessary,
        a new instance is created on the fly.
        """

    def set(rc, acc):
        """
        Sets the queryable accessor to use for the registered resource.
        """

    def clear(rc):
        """
        Clears the accessor for the given registered resource.
        """

    def clear_all():
        """
        Clears all previously set or created accessors.
        """

    def load_representation(rc, url):
        """
        Loads the representation of the specified registered resource  
        pointed to by the given URL into the repository.
        """

    def configure(**config):
        """
        Applies the given configuration to the repository.
        """

    def initialize():
        """
        Performs initialization of the repository.
        """

    is_initialized = Bool(title=u'Checks if this repository has been '
                                 'initialized.')


class IRepositoryManager(Interface):
    """
    Marker interface for the repository manager.
    """


class IMessage(Interface):
    """
    Marker interface for messages.
    """

# pylint: enable=E0213,W0232,E0211
