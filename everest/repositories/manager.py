"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 25, 2013.
"""
from everest.repositories.constants import REPOSITORY_DOMAINS
from everest.repositories.constants import REPOSITORY_TYPES
from everest.repositories.filesystem.repository import FileSystemRepository
from everest.repositories.memory.aggregate import MemoryAggregate
from everest.repositories.memory.repository import MemoryRepository
from everest.repositories.rdb.aggregate import RdbAggregate
from everest.repositories.rdb.repository import RdbRepository
from everest.utils import id_generator

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
        return self.__repositories.get(name)

    def set(self, repo):
        name = repo.name
        if name in self.__repositories \
           and self.__repositories[name].is_initialized:
            raise ValueError('Can not replace repositories that have been '
                             'initialized.')
        self.__repositories[name] = repo

    def get_default(self):
        return self.__default_repo

    def new(self, repo_type, name=None, make_default=False,
            repository_class=None, aggregate_class=None,
            configuration=None):
        if name == REPOSITORY_DOMAINS.ROOT:
            # Unless explicitly configured differently, all root repositories
            # join the transaction.
            join_transaction = True
            autocommit = False
            name = repo_type
        else:
            join_transaction = False
            if name is None:
                name = "%s%d" % (repo_type, self.__repo_id_gen.next())
            # The system repository is special in that its repository
            # should not join the transaction but still commit all changes.
            autocommit = name == REPOSITORY_DOMAINS.SYSTEM
        if repo_type == REPOSITORY_TYPES.MEMORY:
            if repository_class is None:
                repository_class = MemoryRepository
            if aggregate_class is None:
                aggregate_class = MemoryAggregate
        elif repo_type == REPOSITORY_TYPES.RDB:
            if repository_class is None:
                repository_class = RdbRepository
            if aggregate_class is None:
                aggregate_class = RdbAggregate
        elif repo_type == REPOSITORY_TYPES.FILE_SYSTEM:
            if repository_class is None:
                repository_class = FileSystemRepository
            if aggregate_class is None:
                aggregate_class = MemoryAggregate
        else:
            raise ValueError('Unknown repository type.')
        repo = repository_class(name,
                                aggregate_class,
                                join_transaction=join_transaction,
                                autocommit=autocommit)
        if not configuration is None:
            repo.configure(**configuration)
        if make_default:
            self.__default_repo = repo
        return repo

    def setup_system_repository(self, repository_type, reset_on_start):
        """
        Sets up the system repository with the given repository type.
        
        :param str repository: Repository type to use for the SYSTEM 
          repository.
        :param bool reset_on_start: Flag to indicate whether stored system
          resources should be discarded on startup.
        """
        # Set up the system entity repository (this does not join the
        # transaction and is in autocommit mode).
        cnf = dict(messaging_enable=True,
                   messaging_reset_on_start=reset_on_start)
        system_repo = self.new(repository_type,
                               name=REPOSITORY_DOMAINS.SYSTEM,
                               configuration=cnf)
        self.set(system_repo)

    def initialize_all(self):
        """
        Convenience method to initialize all repositories that have not been
        initialized yet.
        """
        for repo in self.__repositories.itervalues():
            if not repo.is_initialized:
                repo.initialize()

    def on_app_created(self, event): # pylint: disable=W0613
        self.initialize_all()
