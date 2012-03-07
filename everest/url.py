"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 28, 2011.
"""

from cgi import parse_qsl
from everest.interfaces import IResourceUrlConverter
from everest.querying.base import EXPRESSION_KINDS
from everest.querying.filterparser import parse_filter
from everest.querying.interfaces import IFilterSpecificationBuilder
from everest.querying.interfaces import IFilterSpecificationDirector
from everest.querying.interfaces import IOrderSpecificationBuilder
from everest.querying.interfaces import IOrderSpecificationDirector
from everest.querying.orderparser import parse_order
from everest.querying.utils import get_filter_specification_factory
from everest.querying.utils import get_order_specification_factory
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.utils import get_filter_specification_visitor
from everest.utils import get_order_specification_visitor
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_resource
from pyramid.traversal import traversal_path
from pyramid.url import model_url
from urllib import unquote
from urlparse import urlparse
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceUrlConverter',
           'UrlPartsConverter',
           'resource_to_url',
           'url_to_resource',
           ]


class ResourceUrlConverter(object):
    """
    Performs URL <-> resource instance conversion.

    See http://en.wikipedia.org/wiki/Query_string for information on characters
    supported in query strings.
    """

    implements(IResourceUrlConverter)

    def __init__(self, request):
        # The request is needed for access to app URL, registry, traversal.
        self.__request = request

    def url_to_resource(self, url):
        """
        Converts the given url into a resource.

        :param str url: URL to convert
        :return: member or collection resource

        ::note : If the query string in the URL has multiple values for a
          query parameter, the last definition in the query string wins.
        """
        parsed = urlparse(url)
        parsed_path = parsed.path # namedtupble problem pylint: disable=E1101
        rc = find_resource(self.__request.root, traversal_path(parsed_path))
        if ICollectionResource in provided_by(rc):
            # In case we found a collection, we have to filter, order, slice.
            parsed_query = parsed.query # namedtupble problem pylint: disable=E1101
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

    def resource_to_url(self, resource, **kw):
        if ICollectionResource in provided_by(resource):
            query = {}
            query.update(kw)
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
                url = model_url(resource, self.__request, query=query)
            else:
                url = model_url(resource, self.__request)
        elif not IMemberResource in provided_by(resource):
            raise ValueError('Can not convert non-resource object "%s to '
                             'URL".' % resource)
        else:
            if resource.__parent__ is None:
                raise ValueError('Can not generate URL for floating member '
                                 '"%s".' % resource)
            url = model_url(resource, self.__request)
        return unquote(url)


def resource_to_url(resource, request=None):
    if request is None:
        request = get_current_request()
    cnv = request.registry.getAdapter(request, IResourceUrlConverter)
    return cnv.resource_to_url(resource)


def url_to_resource(url, request=None):
    if request is None:
        request = get_current_request()
    cnv = request.registry.getAdapter(request, IResourceUrlConverter)
    return cnv.url_to_resource(url)


class UrlPartsConverter(object):

    @classmethod
    def make_filter_specification(cls, filter_string):
        """
        Extracts the "query" parameter from the given request and converts
        the given query string into a filter specification.
        """
        reg = get_current_registry()
        spec_factory = get_filter_specification_factory()
        builder_cls = reg.getUtility(IFilterSpecificationBuilder)
        builder = builder_cls(spec_factory)
        director_cls = reg.getUtility(IFilterSpecificationDirector)
        director = director_cls(parse_filter, builder)
        director.construct(unquote(filter_string))
        if director.has_errors():
            errors = '\n'.join(director.get_errors())
            raise ValueError(errors)
        return builder.specification

    @classmethod
    def make_filter_string(cls, filter_specification):
        visitor_cls = get_filter_specification_visitor(EXPRESSION_KINDS.CQL)
        visitor = visitor_cls()
        filter_specification.accept(visitor)
        return str(visitor.expression)

    @classmethod
    def make_order_specification(cls, order_string):
        reg = get_current_registry()
        order_factory = get_order_specification_factory()
        builder_cls = reg.getUtility(IOrderSpecificationBuilder)
        builder = builder_cls(order_factory)
        director_cls = reg.getUtility(IOrderSpecificationDirector)
        director = director_cls(parse_order, builder)
        director.construct(unquote(order_string))
        if director.has_errors():
            errors = '\n'.join(director.get_errors())
            raise ValueError(errors)
        return builder.specification

    @classmethod
    def make_order_string(cls, order_specification):
        visitor_cls = get_order_specification_visitor(EXPRESSION_KINDS.CQL)
        visitor = visitor_cls()
        order_specification.accept(visitor)
        return str(visitor.expression)

    @classmethod
    def make_slice_key(cls, start_string, size_string):
        """
        Extracts the "start" and "size" parameters from the given
        start and size parameter strings and constructs a slice from it.

        :return: slice key
        :rtype: slice
        """
        try:
            start = int(start_string)
        except ValueError, err:
            err.message = 'Query parameter "start" must be a number.'
            raise err
        if start < 0:
            raise ValueError('Query parameter "start" must be zero or '
                             'a positive number.')
        try:
            size = int(size_string)
        except ValueError, err:
            err.message = 'Query parameter "size" must be a number.'
            raise err
        if size < 1:
            raise ValueError('Query parameter "size" must be a positive '
                             'number.')
        return slice(start, start + size)

    @classmethod
    def make_slice_strings(cls, slice_key):
        start = slice_key.start
        size = slice_key.stop - start
        return (str(start), str(size))


