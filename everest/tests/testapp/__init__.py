"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Package initialization file.

Created on Nov 3, 2011.
"""

from everest.configuration import Configurator
from everest.root import RootFactory
from pyramid.threadlocal import get_current_registry


def app_factory(global_settings, **local_settings): # pylint: disable=W0613
    reg = get_current_registry()
    config = Configurator(registry=reg)
    config.hook_zca()
    config.setup_registry(settings=local_settings,
                          root_factory=RootFactory())
    return config.make_wsgi_app()
