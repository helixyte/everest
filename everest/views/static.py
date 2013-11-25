"""
Static view.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 22, 2010.
"""
from pyramid.static import static_view
from pyramid.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['public_view',
           'PublicViewFactory',
           ]


class PublicViewFactory(object):

    PUBLIC_DIR = 'public_dir'
    PUBLIC_CACHE_MAX_AGE = 'public_cache_max_age'
    DEFAULT_CACHE_MAX_AGE = 3600

    def __init__(self):
        self.__static_view = None

    def __call__(self, context, request):
        if self.__static_view is None:
            self.__static_view = self._create_static_view()
        return self.__static_view(context, request)

    def _create_static_view(self):
        registry = get_current_registry()
        cache_max_age = int(registry.settings.get(self.PUBLIC_CACHE_MAX_AGE,
                                                  self.DEFAULT_CACHE_MAX_AGE))
        return static_view(registry.settings.get(self.PUBLIC_DIR),
                           cache_max_age=cache_max_age,
                           use_subpath=True)

public_view = PublicViewFactory()
