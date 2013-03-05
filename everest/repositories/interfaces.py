"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 25, 2013.
"""
from zope.interface import Attribute # pylint: disable=E0611,F0401
from zope.interface import Interface # pylint: disable=E0611,F0401
from zope.schema import Bool # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['IRepository',
           'IRepositoryManager',
           ]

# interfaces do not provide a constructor. pylint: disable=W0232
# interface methods do not have self pylint: disable = E0213
# interface methods may have no arguments pylint:disable = E0211

class IRepository(Interface):
    """
    """

    def get_aggregate(rc):
        """
        Returns the root agregate for the registered resource. If necessary,
        a new instance is created on the fly.
        """

    def get_collection(rc):
        """
        Returns the root collection for the registered resource. If necessary,
        a new instance is created on the fly.
        """

    def load_representation(rc, url):
        """
        Loads the representation of the specified registered resource  
        pointed to by the given URL into the repository.
        """

    def configure(**config):
        """
        Sets configuration options for this repository which can then be used
        during initialization.
        """

    def initialize():
        """
        Initializes the repository.
        """

    session_factory = Attribute('The session factory provided by this '
                                'repository.')

    name = Attribute('Unique name for this repository.')

    is_initialized = Bool(title=u'Flag indicating if this repository has '
                                 'been initialized.')

    join_transaction = Bool(title=u'Flag indicating if this repository '
                                   'should participate in the Zope '
                                   'transaction (mutually exclusive with '
                                   '"autocommit")')

    autocommit = Bool(title=u'Flag indicating that changes should be '
                             'committed automatically (mutually exclusive '
                             'with "join_transaction").')

    configuration = Attribute('Copy of the map of configuration options.')


class IRepositoryManager(Interface):
    """
    Marker interface for the repository manager.
    """

# pylint: enable=W0232,E0213,E0211
