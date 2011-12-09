"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

WSGI filter to process result messages for flex clients.

Background: the flash plugin is not able to properly handle response messages
 for which the status code is <> 200
 this makes it impossible to properly handle errors on the client side
 (e.g. distinguish a bad request form an internal server error)

Solution:
 this filter processes all response messages where the status code <> 200
 and the referer indicates that the request came from a flash/flex client
 the status code is then modified to 200 and the error is wrapped in the
 payload of this format:
     <error>
      <code>400</code>
      <message>Bad request</message>
      <details>...</details>
    </error>

Created on Sep 27, 2011.
"""

from lxml import etree
from paste.response import header_value
from paste.response import replace_header
from wsgifilter import Filter
from xml.sax.saxutils import escape

__docformat__ = 'reStructuredText en'
__all__ = ['FlexFilter',
           ]


class FlexFilter(Filter):

    def should_filter(self, status, headers, exc_info):
        if status.startswith('2') or status.startswith('401') \
           or status.startswith('301'):
            return False
        else:
            return True

    def filter_output(self, environ, start_response,
                      status, headers, app_iter):
        referer = environ.get('HTTP_REFERER')
        if referer and '.swf' in referer:
            #all the fuzz is just for Flex/Flash clients
            content_type = header_value(headers, 'content-type')
            if ';' in content_type:
                content_type = content_type.split(';', 1)[0]
            if self.format_output:
                import httpencode
                format = httpencode.registry.find_format_match(self.format_output, content_type)
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
                environ, headers, data, status)
            if format:
                app = format.responder(new_output, headers=headers)
                app_iter = app(environ, start_response)
                return app_iter
            else:
                enc_data = []
                encoding = self.output_encoding
                if not isinstance(new_output, basestring):
                    for chunk in new_output:
                        if isinstance(chunk, unicode):
                            chunk = chunk.encode(encoding)
                        enc_data.append(chunk)
                elif isinstance(new_output, unicode):
                    enc_data.append(new_output.encode(encoding))
                else:
                    enc_data.append(new_output)
                start_response('200 OK', headers)
                return enc_data
        else:
            #unfiltered response for non flash clients
            start_response(status, headers)
            return app_iter

    def filter(self, environ, headers, data, status):
        if status.startswith('307'):
            response = '''
                        <error>
                          <code>%s</code>
                          <location>%s</location>
                          <message>%s</message>
                        </error>
                        ''' % (status, header_value(headers, 'Location'),
                               header_value(headers, 'Warning'))
            replace_header(headers, 'Content-Length', len(response))
            return response
        else:
            root = etree.HTML(data)
            message = \
              escape(etree.tostring(root.find('.//body'), method="text").strip())
            if not message:
                message = root.find('.//title').text
            details = ""
            code_node = root.find('.//code')
            if code_node  is not None and code_node.text  is not None:
                details = escape(code_node.text)

                #shorten a bit
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

