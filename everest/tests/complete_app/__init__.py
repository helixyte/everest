"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Package initialization file.

Created on Dec 1, 2011.
"""
from everest.configuration import Configurator
from everest.repositories.interfaces import IRepositoryManager
from everest.root import RootFactory


def app_factory(global_settings, **local_settings): # pylint: disable=W0613
    config = Configurator()
    config.setup_registry(settings=local_settings,
                          root_factory=RootFactory())
#    reg = get_current_registry()
#    repo_mgr = reg.getUtility(IRepositoryManager)
#    repo_mgr.initialize_all()
    return config.make_wsgi_app()
