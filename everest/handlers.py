"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.
"""

from everest.formats import FORMAT_REQUEST
from everest.mime import MIME_REQUEST
from zope.interface import alsoProvides as also_provides # pylint: disable=E0611,F0401

__docformat__ = "reStructuredText en"
__all__ = ['handle_request',
           'handle_stage_events'
           ]

def handle_request(event):
    """Categorizes a new request

    :param event: an object broadcast by the repoze.bfg framework
    :type event: :class:`repoze.bfg.interfaces.INewRequest`
    """
    request = event.request
    mime = request.headers.get('accept', '')
    req_format = request.params.get('format', '')
    iface = MIME_REQUEST.get(mime) and FORMAT_REQUEST.get(req_format) or None
    if iface is not None:
        also_provides(request, iface)
