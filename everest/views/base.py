"""
View base classes.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.j
"""
from everest.messaging import UserMessageChecker
from everest.messaging import UserMessageHandlingContextManager
from everest.mime import CsvMime
from everest.mime import TextPlainMime
from everest.mime import get_registered_mime_strings
from everest.mime import get_registered_mime_type_for_name
from everest.mime import get_registered_mime_type_for_string
from everest.representers.utils import as_representer
from everest.resources.system import UserMessageMember
from everest.utils import get_traceback
from everest.views.interfaces import IResourceView
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPConflict
from pyramid.httpexceptions import HTTPError
from pyramid.httpexceptions import HTTPInternalServerError # pylint: disable=F0401
from pyramid.httpexceptions import HTTPNotAcceptable
from pyramid.httpexceptions import HTTPTemporaryRedirect # pylint: disable=F0401
from pyramid.httpexceptions import HTTPUnsupportedMediaType
from pyramid.response import Response
from pyramid.threadlocal import get_current_request
from zope.interface import implements # pylint: disable=E0611,F0401
import logging
import re

__docformat__ = "reStructuredText en"
__all__ = ['GetResourceView',
           'HttpWarningResubmit',
           'PutOrPostResourceView',
           'ResourceView',
           'ViewUserMessageChecker',
           ]


class HttpWarningResubmit(HTTPTemporaryRedirect): # no __init__ pylint: disable=W0232
    """
    Special 307 HTTP Temporary Redirect exception which transports a URL
    at which the user may resubmit the request with the warning suppressed.
    """
    explanation = 'Your request triggered warnings. You may resubmit ' \
                  'the request under the given location to ignore ' \
                  'the warnings.'
    template = '%(explanation)s\r\n' \
               'Location: <a href="%(location)s">%(location)s</a>\r\n' \
               'Warning UserMessage: %(detail)s\r\n' \
               '<!-- %(comment)s -->'


class ResourceView(object):
    """
    Abstract base class for all resource views.
    
    Resource views know how to handle a number of things that can go wrong
    in a REST request.
    """
    implements(IResourceView)

    __context = None
    __request = None

    def __init__(self, context, request):
        if self.__class__ is ResourceView:
            raise NotImplementedError('Abstract class')
        self._logger = logging.getLogger(self.__class__.__name__)
        self.__context = context
        self.__request = request

    @property
    def context(self):
        return self.__context

    @property
    def request(self):
        return self.__request

    def __call__(self):
        raise NotImplementedError('Abstract method.')

    def _handle_unknown_exception(self, message, traceback):
        """
        Handles requests that triggered an unknown exception.
        
        Respond with a 500 "Internal Server Error".
        """
        self._logger.error('Request errors\n'
                           'Error message: %s\nTraceback:%s' %
                           (message, traceback))
        http_exc = HTTPInternalServerError(message)
        return self.request.get_response(http_exc)


class RepresentingResourceView(ResourceView): # still abstract pylint: disable=W0223
    """
    A resource view with an associated representer.
    """
    def __init__(self, context, request,
                 default_content_type=None,
                 default_response_content_type=None, convert_response=True):
        if self.__class__ is RepresentingResourceView:
            raise NotImplementedError('Abstract class')
        ResourceView.__init__(self, context, request)
        #: Flag indicating if the response body should be converted using
        #: the representer associated with this view.
        self._convert_response = convert_response
        #: The default content type for the representer associated with this
        #: view.
        if default_content_type is None:
            # FIXME: make this configurable.
            default_content_type = CsvMime
        self._default_content_type = default_content_type
        self._default_response_content_type = default_response_content_type

    def _get_response_representer(self):
        """
        Creates a representer for this view.
        
        :raises: :class:`pyramid.httpexceptions.HTTPNotAcceptable` if the
          MIME content type(s) the client specified can not be handled by 
          the view.
        :returns: :class:`everest.representers.base.ResourceRepresenter`
        """
        view_name = self.request.view_name
        if view_name != '':
            mime_type = get_registered_mime_type_for_name(view_name)
            rpr = as_representer(self.context, mime_type)
        else:
            mime_type = None
            acc = None
            for acc in self.request.accept:
                if acc == '*/*':
                    # The client does not care; use the default.
                    mime_type = self.__get_default_response_mime_type()
                    break
                try:
                    mime_type = \
                            get_registered_mime_type_for_string(acc.lower())
                except KeyError:
                    pass
                else:
                    break
            if mime_type is None:
                if not acc is None:
                    # The client specified a MIME type we can not handle; this
                    # is a 406 exxception. We supply allowed MIME content
                    # types in the body of the response.
                    headers = \
                        [('Location', self.request.path_url),
                         ('Content-Type', TextPlainMime.mime_type_string),
                         ]
                    mime_strings = get_registered_mime_strings()
                    exc = HTTPNotAcceptable('Requested MIME content type(s) '
                                            'not acceptable.',
                                            body=','.join(mime_strings),
                                            headers=headers)
                    raise exc
                mime_type = self.__get_default_response_mime_type()
            rpr = as_representer(self.context, mime_type)
        return rpr

    def _get_result(self, resource):
        """
        Converts the given resource to a result to be returned from the view.
        Unless a custom renderer is employed, this will involve creating
        a representer and using it to convert the resource to a string.
        
        :returns: :class:`pyramid.reposnse.Response` object or a dictionary
          with a single key "context" mapped to the given resource (to be
          passed on to a custom renderer).
        """
        if self._convert_response:
            try:
                rpr = self._get_response_representer()
            except HTTPError, http_exc:
                result = self.request.get_response(http_exc)
            else:
                # Set content type and body of the response.
                self.request.response.content_type = \
                                        rpr.content_type.mime_type_string
                self.request.response.body = rpr.to_string(resource)
                result = self.request.response
        else:
            result = dict(context=resource)
        return result

    def __get_default_response_mime_type(self):
        if not self._default_response_content_type is None:
            mime_type = self._default_response_content_type
        else:
            mime_type = self._default_content_type
        return mime_type


class GetResourceView(RepresentingResourceView): # still abstract pylint: disable=W0223
    """
    Abstract base class for all collection views
    """
    def __init__(self, resource, request, **kw):
        if self.__class__ is GetResourceView:
            raise NotImplementedError('Abstract class')
        RepresentingResourceView.__init__(self, resource, request, **kw)

    def __call__(self):
        self._logger.debug('Request URL: %s' % self.request.url)
        result = self._prepare_resource()
        if not isinstance(result, Response):
            # Return a response to bypass Pyramid rendering.
            result = self._get_result(result)
        return result

    def _prepare_resource(self):
        raise NotImplementedError('Abstract method.')


class PutOrPostResourceView(RepresentingResourceView): # still abstract pylint: disable=W0223
    """
    Abstract base class for all member views
    """
    def __init__(self, resource, request, **kw):
        if self.__class__ is PutOrPostResourceView:
            raise NotImplementedError('Abstract class')
        RepresentingResourceView.__init__(self, resource, request, **kw)

    def __call__(self):
        self._logger.debug('Request received on %s' % self.request.url)
        self._logger.debug('Request body:\n%s' % self.request.body)
        if len(self.request.body) == 0:
            # Empty body - return 400 Bad Request.
            response = self._handle_empty_body()
        else:
            checker = ViewUserMessageChecker()
            try:
                with UserMessageHandlingContextManager(checker):
                    data = self._extract_request_data()
                if not checker.vote is True:
                    response = checker.create_307_response()
                else:
                    with UserMessageHandlingContextManager(checker):
                        response = self._process_request_data(data)
                    if not checker.vote is True:
                        response = checker.create_307_response()
            except HTTPError, err:
                response = self.request.get_response(err)
            except Exception, err: # catch Exception pylint: disable=W0703
                response = self._handle_unknown_exception(err.message,
                                                          get_traceback())
        return response

    def _get_request_representer(self):
        try:
            mime_type = \
              get_registered_mime_type_for_string(self.request.content_type)
        except KeyError:
            # The client requested a content type we do not support (415).
            raise HTTPUnsupportedMediaType()
        return as_representer(self.context, mime_type)

    def _extract_request_data(self):
        """
        Extracts the data from the representation submitted in the request
        body and returns it.
        """
        rpr = self._get_request_representer()
        return rpr.data_from_representation(self.request.body)

    def _process_request_data(self, data):
        """
        Processes the data extracted from the representation.
        
        Implementations of this method need to check for a conflict caused
        by the request data (e.g., if the slug for a new member in a POST
        request is already used) and call the :meth:`_handle_conflict`
        method in case a conflict was detected.
        
        :param data: data returned by the :meth:`_extract_request_data` 
          method.
        :returns: response object or dictionary
        """
        raise NotImplementedError('Abstract method.')

    def _handle_empty_body(self):
        """
        Handles requests with an empty body.
        
        Respond with a 400 "Bad Request".
        """
        http_exc = HTTPBadRequest("Request's body is empty!")
        return self.request.get_response(http_exc)

    def _handle_conflict(self, name):
        """
        Handles requests that triggered a conflict.
        
        Respond with a 409 "Conflict"
        """
        err = HTTPConflict('Member "%s" already exists!' % name).exception
        return self.request.get_response(err)

    def _status(self, wsgi_http_exc_class):
        """
        Convenience method to obtain a status string from the given HTTP
        exception class.
        """
        return '%(code)s %(title)s' % wsgi_http_exc_class.__dict__


class ViewUserMessageChecker(UserMessageChecker):
    """
    Custom user message checker for views.
    """
    __guid_pattern = re.compile(r".*ignore-message=([a-z0-9\-]{36})")

    def check(self):
        """
        Implements user message checking for views.
        
        Checks if the current request has an explicit "ignore-message" 
        parameter (a GUID) pointing to a message with identical text from a 
        previous request, in which case further processing is allowed.        
        """
        request = get_current_request()
        ignore_guid = request.params.get('ignore-message')
        coll = request.root['_messages']
        vote = False
        if ignore_guid:
            ignore_mb = coll.get(ignore_guid)
            if not ignore_mb is None and ignore_mb.text == self.message.text:
                vote = True
        return vote

    def create_307_response(self):
        """
        Creates a 307 "Temporary Redirect" response including a HTTP Warning 
        header with code 299 that contains the user message received during
        processing the request.
        """
        request = get_current_request()
        msg_mb = UserMessageMember(self.message)
        coll = request.root['_messages']
        coll.add(msg_mb)
        # Figure out the new location URL.
        qs = self.__get_new_query_string(request.query_string,
                                         self.message.slug)
        resubmit_url = "%s?%s" % (request.path_url, qs)
        headers = [('Warning', '299 %s' % self.message.text),
#                       ('Content-Type', cnt_type),
                   ]
        http_exc = HttpWarningResubmit(location=resubmit_url,
                                       detail=self.message.text,
                                       headers=headers)
        return request.get_response(http_exc)

    def __get_new_query_string(self, old_query_string, new_guid):
        # In absence of a function to manipulate the URL query string in place
        # (the request URL params are read-only), resorting to explicit
        # string manipulation seems the safest thing to do.
        if old_query_string:
            # Make sure to *replace* any given ignore message.
            match = self.__guid_pattern.match(old_query_string)
            if match:
                cur_guid = match.groups()[0]
                qs = re.sub(cur_guid, new_guid, old_query_string)
            else:
                qs = "%s&ignore-message=%s" % (old_query_string,
                                               new_guid)
        else:
            qs = "ignore-message=%s" % new_guid
        return qs
