"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.entities.system import UserMessage
from everest.entities.utils import get_root_aggregate
from everest.interfaces import IUserMessage
from everest.repositories.constants import REPOSITORY_TYPES
from everest.resources.utils import get_root_collection
from everest.testing import ResourceTestCase
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityParent
from everest.utils import get_repository_manager
from pkg_resources import resource_filename # pylint: disable=E0611

__docformat__ = 'reStructuredText en'
__all__ = ['MemorySystemRepositoryTestCase',
           'RdbSystemRepositoryTestCase',
           'RepositoryTestCase',
           ]


class RepositoryTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_repo(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORY_TYPES.MEMORY)
        # Access configuration
        repo.configure(messaging_enable=False)
        self.assert_false(repo.configuration['messaging_enable'])
        # Create a clone and check if slice is the same, but ID is different.
        for meth in (repo.get_collection, repo.get_aggregate):
            acc1 = meth(IMyEntity)
            acc2 = meth(IMyEntity)
            self.assert_not_equal(id(acc1), id(acc2))

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
                            'everest.tests.complete_app',
                            'data/original/myentity-parent-collection.csv')
        coll = get_root_collection(IMyEntityParent)
        self.assert_equal(len(coll), 0)
        repo.load_representation(IMyEntityParent, 'file://%s' % data_path)
        self.assert_equal(len(coll), 1)


class _SystemRepositoryBaseTestCase(ResourceTestCase):
    package_name = 'everest.tests.simple_app'

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


class RdbSystemRepositoryTestCase(_SystemRepositoryBaseTestCase):
    def _load_custom_zcml(self):
        self.config.setup_system_repository(REPOSITORY_TYPES.RDB)
