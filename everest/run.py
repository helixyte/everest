"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 9, 2014.
"""

__docformat__ = 'reStructuredText en'
__all__ = ['app_factory',
           ]

from everest.configuration import Configurator
from everest.root import RootFactory


def app_factory(global_settings, **local_settings): # pylint: disable=W0613
    """
    Default factory for creating a WSGI application using the everest
    configurator and root factory.

    :param dict global_settings: Global settings extracted from an ini file.
        Not used in this default app factory.
    :param dict local_settings: App settings extracted from an ini file.
    """
    config = Configurator()
    config.setup_registry(settings=local_settings,
                          root_factory=RootFactory())
    return config.make_wsgi_app()
