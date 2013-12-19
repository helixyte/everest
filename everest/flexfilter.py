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
from everest.constants import RequestMethods
from everest.mime import AtomMime
from lxml import etree
from pyramid.compat import string_types
from pyramid.httpexceptions import HTTPMovedPermanently
from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPTemporaryRedirect
from pyramid.httpexceptions import HTTPUnauthorized
from xml.sax.saxutils import escape
import re

__docformat__ = 'reStructuredText en'
__all__ = ['FlexFilter',
           ]


# FIXME: The following code is taken from Paste 1.7.5 and wsgifilter to
#        avoid a dependency on Paste which has not been ported to Python 3.x

def header_value(headers, name):
    name = name.lower()
    result = [value for header, value in headers
              if header.lower() == name]
    if result:
        return ','.join(result)
    else:
        return None


def replace_header(headers, name, value):
    name = name.lower()
    i = 0
    result = None
    while i < len(headers):
        if headers[i][0].lower() == name:
            assert not result, "two values for the header '%s' found" % name
            result = headers[i][1]
            headers[i] = (name, value)
        i += 1
    if not result:
        headers.append((name, value))
    return result


class Filter(object):
    """
    Class that implements WSGI output-filtering middleware
    """

    # If this is true, then conditional requests will be diabled
    # (e.g., If-Modified-Since)
    force_no_conditional = True

    conditional_headers = [
        'HTTP_IF_MODIFIED_SINCE',
        'HTTP_IF_NONE_MATCH',
        'HTTP_ACCEPT_ENCODING',
        ]

    # If true, then any status code will be filtered; otherwise only
    # 200 OK responses are filtered
    filter_all_status = False

    # If you provide this (a string or list of string mimetypes) then
    # only content with this mimetype will be filtered
    filter_content_types = ('text/html',)

    # If this is set, then HTTPEncode will be used to decode the value
    # given provided mimetype and this output
    format_output = None

    # You can also use a specific format object, which forces the
    # parsing with that format
    format = None

    # If you aren't using a format but you want unicode instead of
    # 8-bit strings, then set this to true
    decode_unicode = False

    # When we get unicode back from the filter, we'll use this
    # encoding and update the Content-Type:
    output_encoding = 'utf8'

    def __init__(self, app):
        self.app = app
        if isinstance(self.format, string_types):
            from httpencode import get_format
            self.format = get_format(self.format)
        if (self.format is not None
            and self.filter_content_types is Filter.filter_content_types):
            self.filter_content_types = self.format.content_types

    def __call__(self, environ, start_response):
        if self.force_no_conditional:
            for key in self.conditional_headers:
                if key in environ:
                    del environ[key]
        # @@: I should actually figure out a way to deal with some
        # encodings, particular since stuff we don't care about like
        # text/javascript could be gzipped usefully.
        if 'HTTP_ACCEPT_ENCODING' in environ:
            del environ['HTTP_ACCEPT_ENCODING']
        shortcutted = []
        captured = []
        written_output = []
        def replacement_start_response(status, headers, exc_info=None):
            if not self.should_filter(status, headers, exc_info):
                shortcutted.append(None)
                return start_response(status, headers, exc_info)
            if exc_info is not None and shortcutted:
                raise exc_info[0], exc_info[1], exc_info[2]
            # Otherwise we don't care about exc_info...
            captured[:] = [status, headers]
            return written_output.append
        app_iter = self.app(environ, replacement_start_response)
        if shortcutted:
            # We chose not to filter
            return app_iter
        if not captured or written_output:
            # This app hasn't called start_response We can't do
            # anything magic with it; or it used the start_response
            # writer, and we still can't do anything with it
            try:
                for chunk in app_iter:
                    written_output.append(chunk)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()
            app_iter = written_output
        try:
            return self.filter_output(
                environ, start_response,
                captured[0], captured[1], app_iter)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close() # pylint: disable=E1103

    def paste_deploy_middleware(cls, app, global_conf, **app_conf): # pylint: disable=W0613
        # You may wish to override this to make it convert the
        # arguments or use global_conf.  To declare your entry
        # point use:
        # setup(
        #   entry_points="""
        #   [paste.filter_app_factory]
        #   myfilter = myfilter:MyFilter.paste_deploy_middleware
        #   """)
        return cls(app, **app_conf)

    paste_deploy_middleware = classmethod(paste_deploy_middleware)

    def should_filter(self, status, headers, exc_info): # pylint: disable=W0613
        if not self.filter_all_status:
            if not status.startswith('200'):
                return False
        content_type = header_value(headers, 'content-type')
        if content_type and ';' in content_type:
            content_type = content_type.split(';', 1)[0]
        if content_type in self.filter_content_types:
            return True
        return False

    _charset_re = re.compile(
        r'charset="?([a-z0-9-_.]+)"?', re.I)

    # @@: I should do something with these:
    #_meta_equiv_type_re = re.compile(
    #    r'<meta[^>]+http-equiv="?content-type"[^>]*>', re.I)
    #_meta_equiv_value_re = re.compile(
    #    r'value="?[^">]*"?', re.I)

    def filter_output(self, environ, start_response,
                      status, headers, app_iter):
        content_type = header_value(headers, 'content-type')
        if ';' in content_type:
            content_type = content_type.split(';', 1)[0]
        if self.format_output:
            import httpencode
            format = httpencode.registry.find_format_match(self.format_output, content_type) # pylint: disable=W0622
        else:
            format = self.format
        if format:
            data = format.parse_wsgi_response(status, headers, app_iter)
        else:
            data = ''.join(app_iter)
            if self.decode_unicode:
                # @@: Need to calculate encoding properly
                full_ct = header_value(headers, 'content-type') or ''
                match = self._charset_re.search(full_ct)
                if match:
                    encoding = match.group(1)
                else:
                    # @@: Obviously not a great guess
                    encoding = 'utf8'
                data = data.decode(encoding, 'replace')
        new_output = self.filter(
            environ, headers, data)
        if format:
            app = format.responder(new_output, headers=headers)
            app_iter = app(environ, start_response)
            return app_iter
        else:
            enc_data = []
            encoding = self.output_encoding
            if not isinstance(new_output, string_types):
                for chunk in new_output:
                    if isinstance(chunk, unicode):
                        chunk = chunk.encode(encoding)
                    enc_data.append(chunk)
            elif isinstance(new_output, unicode):
                enc_data.append(new_output.encode(encoding))
            else:
                enc_data.append(new_output)
            start_response(status, headers)
            return enc_data

    def filter(self, environ, headers, data):
        raise NotImplementedError


class FlexFilter(Filter):

    def __call__(self, environ, start_response):
        if self.__detect_flex(environ) \
           and environ['REQUEST_METHOD'] == RequestMethods.GET \
           and environ.get('HTTP_ACCEPT'):
            # Override the Accept header. We prefer ATOM, but also allow
            # the server to decide if ATOM is not available.
            environ['HTTP_ACCEPT'] = \
                 "%s;q=0.9,*/*;q=0.8" % AtomMime.mime_type_string
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
