"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Package initialization file.

Created on Nov 3, 2011.
"""
from everest.configuration import Configurator
from everest.interfaces import IRepositoryManager
from everest.root import RootFactory


def app_factory(global_settings, **local_settings): # pylint: disable=W0613
    config = Configurator()
    config.setup_registry(settings=local_settings,
                          root_factory=RootFactory())
    # Initialize all root repositories.
    repo_mgr = config.get_registered_utility(IRepositoryManager)
    repo_mgr.initialize_all()
    return config.make_wsgi_app()
