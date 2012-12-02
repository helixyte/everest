"""
WSGI filter to help a Flex client interact with an everest server.


Background:

The Flash browser plugin is not able to 

 1. Properly handle response messages for which the status code is <> 200. 
    This makes it impossible to properly handle errors on the client side
    (e.g. distinguish a bad request form an internal server error); and
 2. Set Accept headers for GET requests. This causes the default Flex 
    Accept header to be sent ::
        text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
    which prompts evererst to respond with XML, not with ATOM.

Solution:

On ingress, the filter replaces for GET calls from a Flex client the 
Accept header with 'application/atom+xml'.

On egress, this filter processes all response messages for calls from a
Flex client with status code <> 200 by a) setting the status code to
'200 OK' and b) wrapping the error message n the payload like this ::
     <error>
      <code>400</code>
      <message>Bad request</message>
      <details>...</details>
    </error>

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Sep 27, 2011.
"""
from everest.mime import AtomMime
from lxml import etree
from paste.response import header_value # pylint: disable=F0401
from paste.response import replace_header # pylint: disable=F0401
from pyramid.httpexceptions import HTTPMovedPermanently
from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.httpexceptions import HTTPUnauthorized
from wsgifilter import Filter
from xml.sax.saxutils import escape

__docformat__ = 'reStructuredText en'
__all__ = ['FlexFilter',
           ]


class FlexFilter(Filter):

    def __call__(self, environ, start_response):
        if self.__detect_flex(environ) \
           and environ['REQUEST_METHOD'] == 'GET' \
           and environ.get('HTTP_ACCEPT'):
            # Override the Accept header.
            environ['HTTP_ACCEPT'] = AtomMime.mime_type_string
        return Filter.__call__(self, environ, start_response)

    def should_filter(self, status, headers, exc_info):
        return not (status.startswith('2')
                    or status == HTTPUnauthorized().status
                    or status == HTTPMovedPermanently().status)

    def filter_output(self, environ, start_response,
                      status, headers, app_iter):
        if self.__detect_flex(environ):
            # All the fuzz is just for Flex/Flash clients.
            # Wrap start response to pass HTTP OK back to Flash. Also, we
            # need to have access to the status later.
            environ['flexfilter.status'] = status
            wrap_start_response = \
              lambda status, headers: start_response(HTTPOk().status, headers)
            return Filter.filter_output(self, environ, wrap_start_response,
                                        status, headers, app_iter)
        else:
            #unfiltered response for non flash clients
            start_response(status, headers)
            return app_iter

    def filter(self, environ, headers, data):
        status = environ.pop('flexfilter.status')
        if status == HTTPTemporaryRedirect().status:
            response = '''
                        <error>
                          <code>%s</code>
                          <location>%s</location>
                          <message>%s</message>
                        </error>
                        ''' % (status, header_value(headers, 'Location'),
                               header_value(headers, 'Warning'))
            replace_header(headers, 'Content-Length', len(response))
        else:
            root = etree.HTML(data)
            message = escape(etree.tostring(root.find('.//body'),
                                            method="text").strip())
            if not message:
                message = root.find('.//title').text
            details = ""
            code_node = root.find('.//code')
            if code_node  is not None and code_node.text  is not None:
                details = escape(code_node.text)
                # Shorten a bit.
                pos = details.find(',')
                if pos != -1:
                    details = details[:pos]
            response = '''
                        <error>
                          <code>%s</code>
                          <message>%s</message>
                          <details>%s</details>
                        </error>
                        ''' % (status, message, details)
            replace_header(headers, 'Content-Length', len(response))
        return response

    def __detect_flex(self, environ):
        query_string = environ.get('QUERY_STRING')
        referer = environ.get('HTTP_REFERER')
        return (referer and '.swf' in referer) \
               or (query_string and 'flashfilter=true' in query_string)
