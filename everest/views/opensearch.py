"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Aug 21, 2011.
"""

from everest.resources.utils import get_root_collection
from everest.url import resource_to_url
from repoze.bfg.chameleon_zpt import get_template
from repoze.bfg.url import static_url

__docformat__ = 'reStructuredText en'
__all__ = ['OpenSearchDescriptionView',
           ]


class OpenSearchDescriptionView(object):
    """
    """

    CONTENT_TYPE = 'application/opensearchdescription+xml'
    TEMPLATE_MASTER = 'everest:templates/opensearch/master.pt'
    STATIC_IMG_PNG = 'everest:templates/static/images/%s.png'
    CACHE_FOR = 3600

    __context = None
    __request = None

    def __init__(self, context, request):
        self.__context = context
        self.__request = request

    def __call__(self):
        self.__request.response_content_type = self.CONTENT_TYPE
        self.__request.response_cache_for = self.CACHE_FOR
        master_template = get_template(self.TEMPLATE_MASTER)
        image_url = static_url(self.STATIC_IMG_PNG % self.context.__name__,
                               self.request)
        return {'master': master_template,
                'image_url': image_url}

    def get_collection_url(self, icollection):
        return resource_to_url(get_root_collection(icollection),
                               request=self.request)

    @property
    def context(self):
        return self.__context

    @property
    def request(self):
        return self.__request
