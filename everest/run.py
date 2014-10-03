"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 9, 2014.
"""
from everest.configuration import Configurator
from everest.plugins import IPluginManager
from everest.root import RootFactory
from paste.deploy.loadwsgi import APP
from paste.deploy.loadwsgi import ConfigLoader


__docformat__ = 'reStructuredText en'
__all__ = ['app_factory',
           ]


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
    if 'configure.zcml' in local_settings:
        config.load_zcml(local_settings['configure.zcml'])
    app = config.make_wsgi_app()
    # In the absence of an application name in the settings, we use the
    # distribution project name of the loaded application as the next best
    # thing. Unfortunately, this requires parsing the config file again.
    cfg = ConfigLoader(global_settings['__file__'])
    ctxt = cfg.get_context(APP)
    if not ctxt.app_context.distribution is None:
        app_name = ctxt.app_context.distribution.project_name
    else:
        app_name = 'everest'
    ep_group = "%s.plugins" % app_name
    plugin_mgr = config.get_registered_utility(IPluginManager)
    plugin_mgr.load_all(ep_group)
    return app
