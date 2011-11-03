"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 7, 2011.
"""

from everest.configuration import Configurator
from everest.db import initialize_db
from everest.root import RootBuilder
from repoze.bfg.threadlocal import get_current_registry

__docformat__ = "reStructuredText en"
__all__ = ['app',
           'appmaker',
           'get_db_info',
           ]


def get_db_info(settings):
    db_string = settings.get('db_string')
    if db_string is None:
        raise ValueError("No 'db_string' in application configuration.")
    db_echo = bool(settings.get('db_echo', True))
    return db_string, db_echo


def appmaker(db_string, db_echo):
    """
    Initializes the database ORM and and returns a root builder
    """
    initialize_db(db_string, db_echo)
    return RootBuilder()


def app(global_settings, **settings): # pylint: disable=W0613
    """This function returns a WSGI application.

    It is usually called by the PasteDeploy framework during
    ``paster serve``.
    """
    db_string, db_echo = get_db_info(settings)
    get_root = appmaker(db_string, db_echo)
    config = Configurator(registry=get_current_registry())
    config.setup_registry(settings=settings, root_factory=get_root)
    config.hook_zca()
    config.load_zcml('configure.zcml')
    return config.make_wsgi_app()
