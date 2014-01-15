"""
Interfaces for repository classes.

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
    Interface for repositories.

    A repository manages aggregates and collections for a resource; also,
    it holds the session factory.
    """

    def get_aggregate(rc):
        """
        Returns a clone of the root aggregate for the given registered
        resource. If necessary, a new instance is created on the fly.

        :param rc: Registered resource.
        :raises RuntimeError: If the repository has not been initialized yet.
        """

    def get_collection(rc):
        """
        Returns a clone of the root collection for the given registered
        resource. If necessary, a new instance is created on the fly.

        :param rc: Registered resource.
        :raises RuntimeError: If the repository has not been initialized yet.
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

        :param config: Map of configuration options.
        :raises ValueError: If the configuration map contains keys which are
          not declared in the `_configurables` class variable.
        """

    configuration = Attribute('Copy of the map of configuration options.')

    def initialize():
        """
        Initializes the repository.
        """

    is_initialized = Bool(title=u'Flag indicating if this repository has '
                                 'been initialized.')

    def register_resource(rc):
        """
        Registers the given resource

        :param rc: Collection class for the resource to register.
        """

    registered_resources = Attribute('Iterator over all registered resources '
                                     'in this repository (as collection '
                                     'classes).')

    def is_registered_resource(rc):
        """
        Checks if the given object is a resource that was registered with this
        repository.
        """

    session_factory = Attribute('The session factory provided by this '
                                'repository.')

    name = Attribute('Unique name for this repository.')

    join_transaction = Bool(title=u'Flag indicating if this repository '
                                   'should participate in the Zope '
                                   'transaction (mutually exclusive with '
                                   '"autocommit")')

    autocommit = Bool(title=u'Flag indicating that changes should be '
                             'committed automatically (mutually exclusive '
                             'with "join_transaction").')


class IRepositoryManager(Interface):
    """
    Marker interface for the repository manager.
    """

# pylint: enable=W0232,E0213,E0211
