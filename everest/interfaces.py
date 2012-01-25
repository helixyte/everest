"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from zope.interface import Interface # pylint: disable=E0611,F0401

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


class IJsonMime(Interface):
    """Marker interface for a JSON mime type."""


class IAtomMime(Interface):
    """Marker interface for an ATOM mime type."""


class IAtomFeedMime(Interface):
    """Marker interface for an ATOM feed mime type."""


class IAtomEntryMime(Interface):
    """Marker interface for an ATOM entry mime type."""


class IAtomServiceMime(Interface):
    """Marker interface for an ATOM service mime type."""


class IXmlMime(Interface):
    """Marker interface for an XML mime type."""


class ICsvMime(Interface):
    """Marker interface for an CSV mime type."""


class IXlsMime(Interface):
    """Marker interface for an Excel mime type."""

class IZipMime(Interface):
    """Marker interface for an Zip compressed mime type."""


class IHtmlMime(Interface):
    """Marker interface for a HTML mime type."""


class ITextPlainMime(Interface):
    """Marker interface for a Plain Text mime type."""


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


class IMessage(Interface):
    """
    Marker interface for messages.
    """

# pylint: enable=E0213,W0232,E0211
