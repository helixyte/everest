"""
The repository manager class.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 25, 2013.
"""
from everest.repositories.constants import REPOSITORY_DOMAINS
from everest.repositories.interfaces import IRepository
from everest.utils import id_generator
from pyramid.compat import itervalues_
from pyramid.threadlocal import get_current_registry

__docformat__ = 'reStructuredText en'
__all__ = ['RepositoryManager',
           ]


class RepositoryManager(object):
    """
    The repository manager creates, initializes and holds repositories by
    name.
    """
    __repo_id_gen = id_generator()

    def __init__(self):
        self.__repositories = {}
        self.__default_repo = None

    def get(self, name):
        """
        Returns the specified repository.
        """
        return self.__repositories.get(name)

    def set(self, repo):
        """
        Sets the given repository (by name).
        """
        name = repo.name
        if name in self.__repositories \
           and self.__repositories[name].is_initialized:
            raise ValueError('Can not replace repositories that have been '
                             'initialized.')
        self.__repositories[name] = repo

    def get_default(self):
        """
        Returns the default repository.
        """
        return self.__default_repo

    def new(self, repo_type, name=None, make_default=False,
            repository_class=None, aggregate_class=None,
            configuration=None):
        """
        Creates a new repository of the given type. If the root repository
        domain (see :class:`everest.repositories.constants.REPOSITORY_DOMAINS`)
        is passed as a repository name, the type string is used as the name;
        if no name is passed, a unique name is created automatically.
        """
        if name == REPOSITORY_DOMAINS.ROOT:
            # Unless explicitly configured differently, all root repositories
            # join the transaction.
            join_transaction = True
            autocommit = False
            name = repo_type
        else:
            join_transaction = False
            if name is None:
                name = "%s%d" % (repo_type, next(self.__repo_id_gen))
            # The system repository is special in that its repository
            # should not join the transaction but still commit all changes.
            autocommit = name == REPOSITORY_DOMAINS.SYSTEM
        if repository_class is None:
            reg = get_current_registry()
            repository_class = reg.queryUtility(IRepository, name=repo_type)
            if repository_class is None:
                raise ValueError('Unknown repository type "%s".' % repo_type)
        repo = repository_class(name,
                                aggregate_class,
                                join_transaction=join_transaction,
                                autocommit=autocommit)
        if not configuration is None:
            repo.configure(**configuration)
        if make_default:
            self.__default_repo = repo
        return repo

    def setup_system_repository(self, repository_type, reset_on_start,
                                repository_class=None):
        """
        Sets up the system repository with the given repository type.

        :param str repository_type: Repository type to use for the SYSTEM
          repository.
        :param bool reset_on_start: Flag to indicate whether stored system
          resources should be discarded on startup.
        :param repository_class: class to use for the system repository. If
          not given, the registered class for the given type will be used.
        """
        # Set up the system entity repository (this does not join the
        # transaction and is in autocommit mode).
        cnf = dict(messaging_enable=True,
                   messaging_reset_on_start=reset_on_start)
        system_repo = self.new(repository_type,
                               name=REPOSITORY_DOMAINS.SYSTEM,
                               repository_class=repository_class,
                               configuration=cnf)
        self.set(system_repo)

    def initialize_all(self):
        """
        Convenience method to initialize all repositories that have not been
        initialized yet.
        """
        for repo in itervalues_(self.__repositories):
            if not repo.is_initialized:
                repo.initialize()

    def reset_all(self):
        for repo in itervalues_(self.__repositories):
            if repo.is_initialized:
                repo.reset()

    def on_app_created(self, event): # pylint: disable=W0613
        """
        Callback set up by the registry configurator to initialize all
        registered repositories.
        """
        self.initialize_all()
