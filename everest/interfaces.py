"""
Interfaces for everest.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""
from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.schema import Bool # pylint: disable=E0611,F0401
from zope.schema import List # pylint: disable=E0611,F0401
from zope.schema import Text # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['IAtomEntryMime',
           'IAtomFeedMime',
           'IAtomMime',
           'IAtomRequest',
           'IAtomServiceMime',
           'ICsvMime',
           'IDataTraversalProxyAdapter',
           'IDataTraversalProxyAdapter',
           'ICsvRequest',
           'IHtmlRequest',
           'IHtmlMime',
           'IJsonMime',
           'IJsonRequest',
           'IUserMessage',
           'IUserMessageChecker',
           'IUserMessageNotifier',
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
    mime_type_string = Text(title=u'MIME string for this MIME content type. '
                                   '(e.g., "application/json".')
    representer_name = Text(title=u'Name of the representer associated with '
                                   'this MIME content type (e.g., "json").')
    file_extensions = List(title=u'Known file extensions for this MIME '
                                  'content type.')

class IJsonMime(IMime):
    """Marker interface for JSON mime type."""


class IAtomMime(IMime):
    """Marker interface for ATOM mime type."""


class IXmlMime(IMime):
    """Marker interface for XML mime type."""


class ICsvMime(IMime):
    """Marker interface for CSV mime type."""


class IXlsMime(IMime):
    """Marker interface for Excel mime type."""


class IZipMime(IMime):
    """Marker interface for Zip compressed mime type."""


class IHtmlMime(IMime):
    """Marker interface for HTML mime type."""


class ITextPlainMime(IMime):
    """Marker interface for Plain Text mime type."""


class IAtomFeedMime(Interface):
    """Marker interface for ATOM feed mime type."""


class IAtomEntryMime(Interface):
    """Marker interface for ATOM entry mime type."""


class IAtomServiceMime(Interface):
    """Marker interface for ATOM service mime type."""


class IUserMessage(Interface):
    """
    Interface for the user message system resource.
    """
    text = Text(title=u'message text.')


class IUserMessageNotifier(Interface):
    """
    Interface for user message notifiers.
    """
    def notify(message_text):
        """
        Notifies all subscribers to
        :class:`everest.messaging.IUserMessage` of the given message
        and returns their collective vote.

        :param str message_text: message to notify subcribers about. The
          notifier will need to convert this to a :class:`UserMessage`
          instance.
        """


class IUserMessageChecker(Interface):
    """
    Interface for user message checkers.
    """
    def __call__(message):
        """
        This is required so that instances of user message checkers can
        serve as an adapter to a user message.

        :param message: message to check
        :type message: :class:`everest.entities.system.UserMessage`.
        """

    def check():
        """
        Evaluates the message held by this checker. Returns `False`,
        `True`, or `None` to signal abortion, continuation conditional on
        other checkers approval, or unconditional continuation to the caller.
        """

    vote = Bool(title=u'Result of the voting from all subscribed checkers.')


class IResourceUrlConverter(Interface):
    """
    Interface for resource <-> URL converters.
    """
    def url_to_resource(url):
        """Performs URL -> resource conversion."""
    def resource_to_url(resource):
        """Performs URL -> resource conversion."""


class IDataTraversalProxyFactory(Interface):
    """
    Interface for data traversal proxy factories.
    """
    def make_source_proxy(data, options=None):
        """
        Creates a source data traversal proxy.
        """

    def make_target_proxy(data, accessor,
                          manage_back_references=True, options=None):
        """
        Creates a target data traversal proxy.
        """

    def make_proxy(self, data, accessor, relationship_direction,
                   options=None):
        """
        Creates a data traversal proxy.
        """


class IDataTraversalProxyAdapter(IDataTraversalProxyFactory):
    """
    Interface for data traversal proxy adapters.
    """
    proxy_class = Attribute('The data traversal proxy class for this '
                            'adapter.')


class IRelationship(Interface):
    specification = Attribute('Filter specification for the objects '
                              'defined by this relationship.')

    def add(related, direction=None, safe=False):
        """
        Adds the given related object to the relationship.

        The add operation is performed on both ends of the relationship if
        appropriate entity attribute declarations have been made.

        :param related: object to ADD.
        :param direction: One of the constants defined in
          :class:`everest.constants.RELATIONSHIP_DIRECTIONS`. Indicates if
          the attribute of the relator (FORWARD), of the relatee (REVERSE),
          or both (BIDIRECTIONAL) should be updated.
        :param safe: Flag indicating if the ADD operation should
          only proceed if the object to add is not already in the
          relationship.
        """

    def remove(related, direction=None, safe=False):
        """
        Removes the given related object from the relationship.

        The remove operation is performed on both ends of the relationship if
        appropriate entity attribute declarations have been made.

        :param related: object to REMOVE.
        :param direction: One of the constants defined in
          :class:`everest.constants.RELATIONSHIP_DIRECTIONS`. Indicates if
          the attribute of the relator (FORWARD), of the relatee (REVERSE),
          or both (BIDIRECTIONAL) should be updated.
        :param safe: Flag indicating if the REMOVE operation should succeed
          even when the object being removed is not in the relationship.
        :raises ValueError: If :param:`related` is not in the relationship
          and :param:`safe` is not set.
        """

# pylint: enable=E0213,W0232,E0211
