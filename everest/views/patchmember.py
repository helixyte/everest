"""
PATCH member view.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 29, 2013.
"""
from everest.mime import XmlMime
from everest.representers.utils import UpdatedRepresenterConfigurationContext
from everest.representers.xml import XML_VALIDATE_OPTION
from everest.views.base import PutOrPatchResourceView


__docformat__ = 'reStructuredText en'
__all__ = ['PatchMemberView',
           ]


class PatchMemberView(PutOrPatchResourceView):
    """
    View for PATCH requests on member resources.

    The client sends a PATCH request to perform a partial update on a member
    resource. Note that the representation sent by the client typically is
    incomplete and possibly invalid (cf. PUT for replacing a member).
    """
    def _extract_request_data(self):
        rpr = self._get_request_representer()
        if rpr.content_type is XmlMime:
            ctxt = UpdatedRepresenterConfigurationContext(
                            type(self.context),
                            rpr.content_type,
                            options={XML_VALIDATE_OPTION:False})
            with ctxt:
                data = rpr.data_from_bytes(self.request.body)
        else:
            data = rpr.data_from_bytes(self.request.body)
        return data
