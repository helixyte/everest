"""
Post collection view.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 14, 2011.
"""
from pyramid.httpexceptions import HTTPCreated

from everest.resources.utils import provides_member_resource
from everest.resources.utils import provides_resource
from everest.views.base import ModifyingResourceView


__docformat__ = 'reStructuredText en'
__all__ = ['PostCollectionView',
           ]


class PostCollectionView(ModifyingResourceView):
    """
    View for POST requests on collection resources.

    The client POSTs a representation of the member to the URI of the
    collection. If the new member resource was created successfully, the
    server responds with a status code of HTTP CREATED (201) and a Location
    header that contains the IRI of the newly created resource and a
    representation of it in the body of the response.
    """
    def _process_request_data(self, data):
        if not provides_resource(data):
            rpr = self._get_request_representer()
            resource = rpr.resource_from_data(data)
        else:
            resource = data
        data_is_member = provides_member_resource(resource)
        if data_is_member:
            new_members = [resource]
        else:
            new_members = resource
        was_created = True
        sync_with_repo = False
        for new_member in new_members:
            name_is_none = new_member.__name__ is None
            sync_with_repo |= name_is_none
            if not name_is_none \
               and not self.context.get(new_member.__name__) is None:
                # We have a member with the same name - 409 Conflict.
                result = self._handle_conflict(new_member.__name__)
                was_created = False
                break
            else:
                self.context.add(new_member)
        if was_created:
            if sync_with_repo:
                # This is not pretty, but necessary: When the resource
                # name depends on the entity ID, the pending entity needs
                # to be flushed to the repository before we can access
                # the ID.
                self.context.get_aggregate().sync_with_repository()
            self.request.response.status = self._status(HTTPCreated)
            if data_is_member:
                loc_rc = resource
            else:
                loc_rc = self.context
            self._update_response_location_header(loc_rc)
            result = self._get_result(resource)
        return result
