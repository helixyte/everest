"""
View base classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.j
"""
import logging
import re

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPConflict
from pyramid.httpexceptions import HTTPError
from pyramid.httpexceptions import HTTPInternalServerError # pylint: disable=F0401
from pyramid.httpexceptions import HTTPNotAcceptable
from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPTemporaryRedirect # pylint: disable=F0401
from pyramid.httpexceptions import HTTPUnsupportedMediaType
from pyramid.interfaces import IResponse
from pyramid.threadlocal import get_current_request

from everest.messaging import UserMessageChecker
from everest.messaging import UserMessageHandlingContextManager
from everest.mime import CsvMime
from everest.mime import TextPlainMime
from everest.mime import get_registered_mime_strings
from everest.mime import get_registered_mime_type_for_name
from everest.mime import get_registered_mime_type_for_string
from everest.representers.utils import UpdatedRepresenterConfigurationContext
from everest.representers.utils import as_representer
from everest.resources.system import UserMessageMember
from everest.resources.utils import resource_to_url
from everest.url import UrlPartsConverter
from everest.utils import get_traceback
from everest.views.interfaces import IResourceView
from zope.interface import implementer # pylint: disable=E0611,F0401


__docformat__ = "reStructuredText en"
__all__ = ['GetResourceView',
           'HttpWarningResubmit',
           'ModifyingResourceView',
           'RepresentingResourceView',
           'ResourceView',
           'WarnAndResubmitExecutor',
           'WarnAndResubmitUserMessageChecker',
           ]


class WarnAndResubmitExecutor(object):
    """
    Executes a callable within a user message handling context that uses a
    :class:`WarnAndResutbmitUserMessageChecker` as checker.
    """
    def __init__(self, func):
        """
        Constructor.

        :param func: Callable to execute.
        """
        self.__func = func
        self.__checker = None

    def __call__(self, *args, **kw):
        """
        Runs the function passed to this executor with the given positional
        and keyword arguments within a user message handling context.

        Returns the result of the execution or a 307 Temporary Redirect
        response in case the user message checker voted to stop further
        processing.
        """
        self.__checker = WarnAndResubmitUserMessageChecker()
        with UserMessageHandlingContextManager(self.__checker):
            result = self.__func(*args, **kw)
        if not self.__checker.vote is True:
            result = self.__checker.create_307_response()
        return result

    @property
    def do_continue(self):
        """
        Returns `True` if the checker the executor has run and the checker
        did not vote to stop further processing.
        """
        return not self.__checker is None and self.__checker.vote is True


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


@implementer(IResourceView)
class ResourceView(object):
    """
    Abstract base class for all resource views.

    Resource views know how to handle a number of things that can go wrong
    in a REST request.
    """
    def __init__(self, context, request):
        if self.__class__ is ResourceView:
            raise NotImplementedError('Abstract class')
        #: View logger (qualname "everest.views").
        self._logger = logging.getLogger('everest.views')
        #: The contetxt of the view.
        self.__context = context
        #: The request for the view.
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
                 default_response_content_type=None, convert_response=True,
                 enable_messaging=False):
        if self.__class__ is RepresentingResourceView:
            raise NotImplementedError('Abstract class')
        ResourceView.__init__(self, context, request)
        #: Flag indicating if the response body should be converted using
        #: the representer associated with this view.
        self._convert_response = convert_response
        if default_content_type is None:
            # FIXME: make this configurable.
            default_content_type = CsvMime
        #: The default content type for this view.
        self._default_content_type = default_content_type
        #: The default content type for the response.
        self._default_response_content_type = default_response_content_type
        #: Flag indicating if a messaging context should be used when
        #: processing calls into this view.
        self._enable_messaging = enable_messaging

    def _get_response_mime_type(self):
        """
        Returns the reponse MIME type for this view.

        :raises: :class:`pyramid.httpexceptions.HTTPNotAcceptable` if the
          MIME content type(s) the client specified can not be handled by
          the view.
        """
        view_name = self.request.view_name
        if view_name != '':
            mime_type = get_registered_mime_type_for_name(view_name)
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
                    # is a 406 exception. We supply allowed MIME content
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
        return mime_type

    def _get_response_representer(self):
        """
        Creates a representer for this view.

        :returns: :class:`everest.representers.base.ResourceRepresenter`
        """
        mime_type = self._get_response_mime_type()
        return as_representer(self.context, mime_type)

    def _get_result(self, resource):
        """
        Converts the given resource to a result to be returned from the view.
        Unless a custom renderer is employed, this will involve creating
        a representer and using it to convert the resource to a string.

        :param resource: Resource to convert.
        :type resource: Object implementing
          :class:`evererst.interfaces.IResource`.
        :returns: :class:`pyramid.reposnse.Response` object or a dictionary
          with a single key "context" mapped to the given resource (to be
          passed on to a custom renderer).
        """
        if self._convert_response:
            self._update_response_body(resource)
            result = self.request.response
        else:
            result = dict(context=resource)
        return result

    def _update_response_body(self, resource):
        """
        Creates a representer and updates the response body with the byte
        representation created for the given resource.
        """
        rpr = self._get_response_representer()
        # Set content type and body of the response.
        self.request.response.content_type = \
                                rpr.content_type.mime_type_string
        rpr_body = rpr.to_bytes(resource)
        self.request.response.body = rpr_body

    def _update_response_location_header(self, resource):
        """
        Adds a new or replaces an existing Location header to the response
        headers pointing to the URL of the given resource.
        """
        location = resource_to_url(resource, request=self.request)
        loc_hdr = ('Location', location)
        hdr_names = [hdr[0].upper() for hdr in self.request.response.headerlist]
        try:
            idx = hdr_names.index('LOCATION')
        except ValueError:
            self.request.response.headerlist.append(loc_hdr)
        else:
            # Replace existing location header.
            # FIXME: It is not clear under which conditions this happens, so
            #        we do not have a test for it yet.
            self.request.response.headerlist[idx] = loc_hdr # pragma: no cover

    def __get_default_response_mime_type(self):
        if not self._default_response_content_type is None:
            mime_type = self._default_response_content_type
        else:
            mime_type = self._default_content_type
        return mime_type


class GetResourceView(RepresentingResourceView): # still abstract pylint: disable=W0223
    """
    Abstract base class for all resource views processing GET requests.
    """
    def __init__(self, resource, request, **kw):
        if self.__class__ is GetResourceView:
            raise NotImplementedError('Abstract class')
        # Messaging is disabled by default for GET views.
        if kw.get('enable_messaging') is None:
            kw['enable_messaging'] = False
        RepresentingResourceView.__init__(self, resource, request, **kw)

    def __call__(self):
        self._logger.debug('Request URL: %s.', self.request.url)
        try:
            if self._enable_messaging:
                prep_executor = \
                    WarnAndResubmitExecutor(self._prepare_resource)
                data = prep_executor()
                do_continue = prep_executor.do_continue
            else:
                data = self._prepare_resource()
                do_continue = not IResponse.providedBy(data) # pylint: disable=E1101
            if do_continue:
                # Return a response to bypass Pyramid rendering.
                if self._enable_messaging:
                    res_executor = WarnAndResubmitExecutor(self._get_result)
                    result = res_executor(data)
                else:
                    result = self._get_result(data)
            else:
                result = data
        except HTTPError as http_exc:
            result = self.request.get_response(http_exc)
        except Exception as err: # catch Exception pylint: disable=W0703
            result = self._handle_unknown_exception(str(err),
                                                    get_traceback())
        return result

    def _prepare_resource(self):
        raise NotImplementedError('Abstract method.')

    def _update_response_body(self, resource):
        """
        Extends the base class method with links options processing.
        """
        links_options = self.__configure_refs()
        if not links_options is None:
            with UpdatedRepresenterConfigurationContext(
                                        type(self.context),
                                        self._get_response_mime_type(),
                                        attribute_options=links_options):
                RepresentingResourceView._update_response_body(self, resource)
        else:
            RepresentingResourceView._update_response_body(self, resource)

    def __configure_refs(self):
        refs_options_string = self.request.params.get('refs')
        if not refs_options_string is None:
            links_options = \
                UrlPartsConverter.make_refs_options(refs_options_string)
        else:
            links_options = None
        return links_options


class ModifyingResourceView(RepresentingResourceView): # still abstract pylint: disable=W0223
    """
    Abstract base class for all modifying member views.
    """
    def __init__(self, resource, request, **kw):
        if self.__class__ is ModifyingResourceView:
            raise NotImplementedError('Abstract class')
        # Messaging is enabled by default for modifying views.
        if kw.get('enable_messaging') is None:
            kw['enable_messaging'] = True
        RepresentingResourceView.__init__(self, resource, request, **kw)

    def __call__(self):
        self._logger.debug('%s request received on %s.',
                           self.request.method, self.request.url)
        self._logger.debug('Request body: %s', self.request.body,
                           extra=dict(output_limit=500))
        if len(self.request.body) == 0:
            # Empty body - return 400 Bad Request.
            result = self._handle_empty_body()
        else:
            try:
                if self._enable_messaging:
                    extract_executor = \
                        WarnAndResubmitExecutor(self._extract_request_data)
                    data = extract_executor()
                    do_continue = extract_executor.do_continue
                else:
                    data = self._extract_request_data()
                    do_continue = not IResponse.providedBy(data) # pylint: disable=E1101
                if do_continue:
                    if self._enable_messaging:
                        process_executor = \
                          WarnAndResubmitExecutor(self._process_request_data)
                        result = process_executor(data)
                    else:
                        result = self._process_request_data(data)
                else:
                    result = data
            except HTTPError as err:
                result = self.request.get_response(err)
            except Exception as err: # catch Exception pylint: disable=W0703
                result = self._handle_unknown_exception(str(err),
                                                        get_traceback())
        return result

    def _get_request_representer(self):
        """
        Returns a representer for the content type specified in the request.

        :raises HTTPUnsupportedMediaType: If the specified content type is
          not supported.
        """
        try:
            mime_type = \
              get_registered_mime_type_for_string(self.request.content_type)
        except KeyError:
            # The client sent a content type we do not support (415).
            raise HTTPUnsupportedMediaType()
        return as_representer(self.context, mime_type)

    def _extract_request_data(self):
        """
        Extracts the data from the representation submitted in the request
        body and returns it.

        This default implementation uses a representer for the content type
        specified by the request to perform the extraction and returns an
        object implementing the
        :class:`everest.representers.interfaces.IResourceDataElement`
        interface.

        :raises HTTPError: To indicate problems with the request data
          extraction in terms of HTTP codes.
        """
        rpr = self._get_request_representer()
        return rpr.data_from_bytes(self.request.body)

    def _process_request_data(self, data):
        """
        Processes the data extracted from the representation.

        Implementations of this method need to check for a conflict caused
        by the request data (e.g., if the slug for a new member in a POST
        request is already used) and call the :meth:`_handle_conflict`
        method in case a conflict was detected.

        :param data: data returned by the :meth:`_extract_request_data`
          method.
        :raises HTTPError: To indicate problems with the request data
          processing in terms of HTTP codes.
        :returns: Response object or dictionary (rendering context).
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


class PutOrPatchResourceView(ModifyingResourceView):
    """
    Base class for views that modify a member through PUT and PATCH requests.
    """
    def _process_request_data(self, data):
        initial_name = self.context.__name__
        self.context.update(data)
        current_name = self.context.__name__
        self.request.response.status = self._status(HTTPOk)
        if initial_name != current_name:
            # FIXME: add conflict detection!
            self._update_response_location_header(self.context)
        # We return the (representation of) the updated member to
        # assist the client in doing the right thing (some clients block
        # access to the Response headers so we may not be able to find the
        # new location when HTTP/1.1 301 is returned).
        return self._get_result(self.context)


class WarnAndResubmitUserMessageChecker(UserMessageChecker):
    """
    Custom user message checker for showing warning messages to the user
    with the possibility for resubmission with warnings suppressed.
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
