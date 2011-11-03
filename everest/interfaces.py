"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""

from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['IAtomMime',
           'IAtomEntryMime',
           'IAtomFeedMime',
           'IAtomRequest',
           'IAtomServiceMime',
           'ICsvMime',
           'ICsvRequest',
           'IJsonMime',
           'IJsonRequest',
           'IXmlMime',
           'IXmlRequest',
           'IXlsMime',
           'IXlsRequest'
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

class IXlsRequest(Interface):
    """Marker interface for an Excel request."""

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

class IResourceReferenceConverter(Interface):
    def url_to_resource(url):
        """Performs URL -> resource conversion."""
    def resource_to_url(resource):
        """Performs URL -> resource conversion."""

class IStagingContextManager(Interface):
    root_aggregate_impl = Attribute("Root aggregate implementation class.")
    relation_aggregate_impl = \
            Attribute("Relation aggregate implementation class.")
    def __enter__():
        """Enters the context."""
    def __exit__():
        """Exits the context."""

# pylint: enable=E0213,W0232,E0211
