"""
Get collection view.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 7, 2011.
"""
from copy import deepcopy

from everest.batch import Batch
from everest.resources.base import Link
from everest.url import UrlPartsConverter
from everest.utils import get_traceback
from everest.views.base import GetResourceView

__docformat__ = "reStructuredText en"
__all__ = ['GetCollectionView',
           ]


class GetCollectionView(GetResourceView):
    """
    View for GET requests on collection resources.

    If the request is sucessful, the server responds with status HTTP OK.
    """
    def _prepare_resource(self):
        try:
            self.__filter_collection()
            self.__order_collection()
            self.__slice_collection()
        except ValueError as err:
            result = self._handle_unknown_exception(err.args[0],
                                                    get_traceback())
        else:
            needs_default_order = self.context.order is None
            if needs_default_order:
                # Make sure we have defined an ordering on the collection
                # to guarantee an order on the result set. This should not
                # be reflected in the links' URLs.
                self.context.order = deepcopy(self.context.default_order)
            # Build batch links.
            batch = self.__create_batch()
            self_link = Link(self.context, 'self', self.context.title)
            self.context.add_link(self_link)
            if batch.index > 0:
                first_link = self.__create_nav_link(batch.first, 'first',
                                                    not needs_default_order)
                self.context.add_link(first_link)
            if not batch.previous is None:
                prev_link = self.__create_nav_link(batch.previous, 'previous',
                                                   not needs_default_order)
                self.context.add_link(prev_link)
            if not batch.next is None:
                next_link = self.__create_nav_link(batch.next, 'next',
                                                   not needs_default_order)
                self.context.add_link(next_link)
            if not batch.index == batch.number - 1:
                last_link = self.__create_nav_link(batch.last, 'last',
                                                   not needs_default_order)
                self.context.add_link(last_link)
            result = self.context
        return result

    def __create_batch(self):
        start = self.context.slice.start
        size = self.context.slice.stop - start
        total_size = len(self.context)
        return Batch(start, size, total_size)

    def __create_nav_link(self, batch, rel, reset_order):
        coll_clone = self.context.clone()
        if reset_order:
            coll_clone.order = None
        coll_clone.slice = slice(batch.start,
                                 batch.start + batch.size)
        return Link(coll_clone, rel, self.context.title)

    def __filter_collection(self):
        query_string = self.request.params.get('q')
        if not query_string is None:
            filter_spec = \
                UrlPartsConverter.make_filter_specification(query_string)
            self.context.filter = filter_spec

    def __order_collection(self):
        order_string = self.request.params.get('sort')
        if not order_string is None:
            order_spec = \
                UrlPartsConverter.make_order_specification(order_string)
            self.context.order = order_spec

    def __slice_collection(self):
        start_string = self.request.params.get('start')
        if start_string is None:
            start_string = '0'
        size_string = self.request.params.get('size')
        if size_string is None:
            size_string = str(self.context.default_limit)
        slice_key = UrlPartsConverter.make_slice_key(start_string, size_string)
        if not self.context.max_limit is None \
           and slice_key.stop - slice_key.start > self.context.max_limit:
            # Apply maximum batch size, if necessary.
            slice_key = slice(slice_key.start,
                              slice_key.start + self.context.max_limit)
        self.context.slice = slice_key
