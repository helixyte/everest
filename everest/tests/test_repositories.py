"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.datastores.memory import Aggregate
from everest.datastores.memory import DataStore
from everest.entities.repository import EntityRepository
from everest.entities.system import UserMessage
from everest.entities.utils import get_root_aggregate
from everest.interfaces import IUserMessage
from everest.repository import REPOSITORY_TYPES
from everest.resources.utils import get_root_collection
from everest.testing import EntityTestCase
from everest.testing import ResourceTestCase
from everest.tests.testapp.interfaces import IBar
from everest.tests.testapp.interfaces import IFoo
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityParent
from everest.utils import get_repository_manager
from pkg_resources import resource_filename  # pylint: disable=E0611

__docformat__ = 'reStructuredText en'
__all__ = ['EntityRepositoryTestCase',
           'ResourceRepositoryTestCase',
           ]


class _RepositoryBaseTestCaseMixin(object):
    def _test_repo(self, repo, ifc1, ifc2):
        # Access configuration
        repo.configure(messaging_enable=False)
        self.assert_false(repo.configuration['messaging_enable'])
        #  Create a clone and check if slice is the same, but ID is different.
        acc1 = repo.new(ifc1)
        acc1.slice = slice(0, 1)
        repo.set(ifc1, acc1)
        acc1_clone = repo.get(ifc1)
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
        ent_store = DataStore('test')
        ent_repo = EntityRepository(ent_store, Aggregate)
        ent_repo.initialize()
        self._test_repo(ent_repo, IFoo, IBar)


class ResourceRepositoryTestCase(ResourceTestCase,
                                 _RepositoryBaseTestCaseMixin):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_basics(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORY_TYPES.MEMORY)
        self._test_repo(repo, IMyEntity, IMyEntityParent)

    def test_manager(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORY_TYPES.MEMORY)
        self.assert_raises(ValueError, repo_mgr.set, repo)
        with self.assert_raises(ValueError) as cm:
            repo_mgr.new('foo', 'bar')
        exc_msg = 'Unknown repository type.'
        self.assert_equal(cm.exception.message, exc_msg)

    def test_load_representation(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORY_TYPES.MEMORY)
        data_path = resource_filename(
                            'everest.tests.testapp_db',
                            'data/original/myentity-parent-collection.csv')
        coll = get_root_collection(IMyEntityParent)
        self.assert_equal(len(coll), 0)
        repo.load_representation(IMyEntityParent, 'file://%s' % data_path)
        self.assert_equal(len(coll), 1)


class _SystemRepositoryBaseTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp'

    def test_add_delete(self):
        agg = get_root_aggregate(IUserMessage)
        msg = UserMessage('user message.')
        agg.add(msg)
        self.assert_is_not_none(msg.id)
        agg.remove(msg)
        self.assert_equal(len(list(agg.iterator())), 0)


class MemorySystemRepositoryTestCase(_SystemRepositoryBaseTestCase):
    def _load_custom_zcml(self):
        self.config.setup_system_repository(REPOSITORY_TYPES.MEMORY)


class OrmSystemRepositoryTestCase(_SystemRepositoryBaseTestCase):
    def _load_custom_zcml(self):
        self.config.setup_system_repository(REPOSITORY_TYPES.ORM)
