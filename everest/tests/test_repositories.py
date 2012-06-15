"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.entities.aggregates import MemoryAggregate
from everest.entities.repository import EntityRepository
from everest.repository import REPOSITORIES
from everest.resources.entitystores import CachingEntityStore
from everest.testing import EntityTestCase
from everest.testing import ResourceTestCase
from everest.tests.testapp.interfaces import IBar
from everest.tests.testapp.interfaces import IFoo
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityParent
from everest.utils import get_repository_manager

__docformat__ = 'reStructuredText en'
__all__ = ['EntityRepositoryTestCase',
           'ResourceRepositoryTestCase',
           ]


class _RepositoryBaseTestCaseMixin(object):
    def _test_repo(self, repo, ifc1, ifc2):
        acc1 = repo.new(ifc1)
        acc1.slice = slice(0, 1)
        repo.set(ifc1, acc1)
        acc1_clone = repo.get(ifc1)
        # Clone has same slice, but different ID.
        self.assert_equal(acc1.slice, acc1_clone.slice)
        self.assert_not_equal(id(acc1), id(acc1_clone))
        acc2 = repo.new(ifc2)
        acc2.slice = slice(1, 2)
        repo.set(ifc2, acc2)
        # After clearing the cached accessor, .get(ifc1) creates a new 
        # accessor for ifc1 with the default slice.
        repo.clear(ifc1)
        acc1_new = repo.get(ifc1)
        self.assert_not_equal(acc1_new.slice, acc1.slice)
        # After clearing all cached accessors, .get(ifc2) also returns a new
        # accessor.
        repo.clear_all()
        acc2_new = repo.get(ifc2)
        self.assert_not_equal(acc2_new.slice, acc2.slice)


class EntityRepositoryTestCase(EntityTestCase, _RepositoryBaseTestCaseMixin):
    package_name = 'everest.tests.testapp'

    def test_basics(self):
        ent_store = CachingEntityStore('test', join_transaction=False)
        ent_repo = EntityRepository(ent_store, MemoryAggregate)
        ent_repo.initialize()
        self._test_repo(ent_repo, IFoo, IBar)


class ResourceRepositoryTestCase(ResourceTestCase,
                                 _RepositoryBaseTestCaseMixin):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_basics(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORIES.MEMORY)
        self._test_repo(repo, IMyEntity, IMyEntityParent)

    def test_manager(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORIES.MEMORY)
        self.assert_raises(ValueError, repo_mgr.set, repo)
        with self.assert_raises(ValueError) as cm:
            repo_mgr.new('foo', 'bar')
        exc_msg = 'Unknown repository type.'
        self.assert_equal(cm.exception.message, exc_msg)
