"""
URL <-> resource conversion.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 28, 2011.
"""
from everest.compat import parse_qsl
from everest.interfaces import IResourceUrlConverter
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.filterparser import parse_filter
from everest.querying.orderparser import parse_order
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResource
from everest.resources.utils import get_root_collection
from everest.utils import get_filter_specification_visitor
from everest.utils import get_order_specification_visitor
from pyparsing import ParseException
from pyramid.compat import url_unquote
from pyramid.compat import urlparse
from pyramid.traversal import find_resource
from pyramid.traversal import traversal_path
from zope.interface import implementer # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from everest.querying.refsparser import parse_refs

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceUrlConverter',
           'UrlPartsConverter',
           ]


@implementer(IResourceUrlConverter)
class ResourceUrlConverter(object):
    """
    Performs URL <-> resource instance conversion.

    See http://en.wikipedia.org/wiki/Query_string for information on characters
    supported in query strings.
    """

    def __init__(self, request):
        # The request is needed for access to app URL, registry, traversal.
        self.__request = request

    def url_to_resource(self, url):
        """
        Returns the resource that is addressed by the given URL.

        :param str url: URL to convert
        :return: member or collection resource

        :note: If the query string in the URL has multiple values for a
          query parameter, the last definition in the query string wins.
        """
        parsed = urlparse.urlparse(url)
        parsed_path = parsed.path # namedtupble problem pylint: disable=E1101
        rc = find_resource(self.__request.root, traversal_path(parsed_path))
        if ICollectionResource in provided_by(rc):
            # In case we found a collection, we have to filter, order, slice.
            parsed_query = parsed.query # namedtuple problem pylint: disable=E1101
            params = dict(parse_qsl(parsed_query))
            filter_string = params.get('q')
            if not filter_string is None:
                rc.filter = \
                    UrlPartsConverter.make_filter_specification(filter_string)
            order_string = params.get('sort')
            if not order_string is None:
                rc.order = \
                    UrlPartsConverter.make_order_specification(order_string)
            start_string = params.get('start')
            size_string = params.get('size')
            if not (start_string is None or size_string is None):
                rc.slice = \
                  UrlPartsConverter.make_slice_key(start_string, size_string)
        elif not IMemberResource in provided_by(rc):
            raise ValueError('Traversal found non-resource object "%s".' % rc)
        return rc

    def resource_to_url(self, resource, quote=False):
        """
        Returns the URL for the given resource.

        :param resource: Resource to create a URL for.
        :param bool quote: If set, the URL returned will be quoted.
        :raises ValueError: If the given resource is floating (i.e., has
          the parent attribute set to `None`)
        """
        ifc = provided_by(resource)
        if not IResource in ifc:
            raise TypeError('Can not generate URL for non-resource "%s".'
                            % resource)
        elif resource.__parent__ is None:
            raise ValueError('Can not generate URL for floating resource '
                             '"%s".' % resource)
        if ICollectionResource in ifc:
            query = {}
            if not resource.filter is None:
                query['q'] = \
                    UrlPartsConverter.make_filter_string(resource.filter)
            if not resource.order is None:
                query['sort'] = \
                    UrlPartsConverter.make_order_string(resource.order)
            if not resource.slice is None:
                query['start'], query['size'] = \
                    UrlPartsConverter.make_slice_strings(resource.slice)
            if query != {}:
                options = dict(query=query)
            else:
                options = dict()
            if not resource.is_root_collection:
                # For nested collections, we check if the referenced root
                # collection is exposed (i.e., has the service as parent).
                # If yes, we return an absolute URL, else a nested URL.
                root_coll = get_root_collection(resource)
                if not root_coll.has_parent:
                    url = self.__request.resource_url(resource)
                else:
                    url = self.__request.resource_url(root_coll, **options)
            else:
                url = self.__request.resource_url(resource, **options)
        else:
            if not resource.is_root_member:
                # For nested members, we check if the referenced root
                # collection is exposed (i.e., has the service as parent).
                # If yes, we return an absolute URL, else a nested URL.
                root_coll = get_root_collection(resource)
                if not root_coll.has_parent:
                    url = self.__request.resource_url(resource)
                else:
                    par_url = self.__request.resource_url(root_coll)
                    url = "%s%s/" % (par_url, resource.__name__)
            else:
                url = self.__request.resource_url(resource)
        if not quote:
            url = url_unquote(url)
        return url


class UrlPartsConverter(object):
    """
    Helper class providing functionality to convert parts of a URL to
    specifications and vice versa.
    """
    @classmethod
    def make_filter_specification(cls, filter_string):
        """
        Converts the given CQL filter expression into a filter specification.
        """
        try:
            return parse_filter(filter_string)
        except ParseException as err:
            raise ValueError('Expression parameters have errors. %s' % err)

    @classmethod
    def make_filter_string(cls, filter_specification):
        """
        Converts the given filter specification to a CQL filter expression.
        """
        visitor_cls = get_filter_specification_visitor(EXPRESSION_KINDS.CQL)
        visitor = visitor_cls()
        filter_specification.accept(visitor)
        return str(visitor.expression)

    @classmethod
    def make_order_specification(cls, order_string):
        """
        Converts the given CQL sort expression to a order specification.
        """
        try:
            return parse_order(order_string)
        except ParseException as err:
            raise ValueError('Expression parameters have errors. %s' % err)

    @classmethod
    def make_order_string(cls, order_specification):
        """
        Converts the given order specification to a CQL order expression.
        """
        visitor_cls = get_order_specification_visitor(EXPRESSION_KINDS.CQL)
        visitor = visitor_cls()
        order_specification.accept(visitor)
        return str(visitor.expression)

    @classmethod
    def make_slice_key(cls, start_string, size_string):
        """
        Converts the given start and size query parts to a slice key.

        :return: slice key
        :rtype: slice
        """
        try:
            start = int(start_string)
        except ValueError:
            raise ValueError('Query parameter "start" must be a number.')
        if start < 0:
            raise ValueError('Query parameter "start" must be zero or '
                             'a positive number.')
        try:
            size = int(size_string)
        except ValueError:
            raise ValueError('Query parameter "size" must be a number.')
        if size < 1:
            raise ValueError('Query parameter "size" must be a positive '
                             'number.')
        return slice(start, start + size)

    @classmethod
    def make_slice_strings(cls, slice_key):
        """
        Converts the given slice key to start and size query parts.
        """
        start = slice_key.start
        size = slice_key.stop - start
        return (str(start), str(size))

    @classmethod
    def make_refs_options(cls, refs_string):
        """
        Converts the given CQL resource references string to a dictionary of
        attribute representer options.
        """
        try:
            return parse_refs(refs_string)
        except ParseException as err:
            raise ValueError('Refs string has errors. %s' % err)
