"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.entities.base import Entity
from everest.entities.system import UserMessage
from everest.entities.utils import get_root_aggregate
from everest.interfaces import IUserMessage
from everest.mime import CsvMime
from everest.repositories.constants import REPOSITORY_TYPES
from everest.repositories.memory import Aggregate
from everest.repositories.memory import Repository
from everest.resources.io import get_collection_name
from everest.resources.io import get_read_collection_path
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import get_service
from everest.resources.utils import new_stage_collection
from everest.testing import Pep8CompliantTestCase
from everest.testing import ResourceTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild
from everest.tests.complete_app.interfaces import IMyEntityGrandchild
from everest.tests.complete_app.interfaces import IMyEntityParent
from everest.tests.complete_app.resources import MyEntityMember
from everest.tests.simple_app.entities import FooEntity
from everest.tests.simple_app.interfaces import IFoo
from everest.tests.simple_app.resources import FooMember
from everest.utils import get_repository_manager
from pkg_resources import resource_filename # pylint: disable=E0611
import glob
import os
import shutil
import tempfile
import transaction

__docformat__ = 'reStructuredText en'
__all__ = ['BasicRepositoryTestCase',
           'MemorySystemRepositoryTestCase',
           'RdbSystemRepositoryTestCase',
           'RepositoryTestCase',
           'FileSystemEmptyRepositoryTestCase',
           'FileSystemRepositoryTestCase',
           ]


class BasicRepositoryTestCase(Pep8CompliantTestCase):
    def test_args(self):
        self.assert_raises(ValueError, Repository, 'DUMMY', Aggregate,
                           autocommit=True, join_transaction=True)


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

    def test_set_collection_parent_fails(self):
        self.config.add_resource(IFoo, FooMember, FooEntity, expose=False)
        coll = new_stage_collection(IFoo)
        srvc = get_service()
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORY_TYPES.MEMORY)
        with self.assert_raises(ValueError) as cm:
            repo.set_collection_parent(coll, srvc)
        self.assert_true(cm.exception.message.startswith('No root collect'))



class _SystemRepositoryBaseTestCase(ResourceTestCase):
    package_name = 'everest.tests.simple_app'

    def test_add_update_delete(self):
        agg = get_root_aggregate(IUserMessage)
        txt = 'user message.'
        msg = UserMessage(txt)
        agg.add(msg)
        self.assert_is_not_none(msg.id)
        txt1 = 'user message 1.'
        msg1 = UserMessage(txt1)
        agg.update(msg, msg1)
        self.assert_equal(msg.text, txt1)
        agg.remove(msg)
        self.assert_equal(len(list(agg.iterator())), 0)


class MemorySystemRepositoryTestCase(_SystemRepositoryBaseTestCase):
    def _load_custom_zcml(self):
        self.config.setup_system_repository(REPOSITORY_TYPES.MEMORY)


class RdbSystemRepositoryTestCase(_SystemRepositoryBaseTestCase):
    def _load_custom_zcml(self):
        self.config.setup_system_repository(REPOSITORY_TYPES.RDB)


class _FileSystemRepositoryTestCaseMixin(object):
    _data_dir = None
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_fs.zcml'

    def _set_data_dir(self):
        self._data_dir = os.path.join(os.path.dirname(__file__),
                                       'complete_app', 'data')


class FileSystemEmptyRepositoryTestCase(_FileSystemRepositoryTestCaseMixin,
                                        ResourceTestCase):
    def set_up(self):
        self._set_data_dir()
        ResourceTestCase.set_up(self)

    def test_initialization_with_empty_data_dir(self):
        colls = [
                 get_root_collection(IMyEntityParent),
                 get_root_collection(IMyEntity),
                 get_root_collection(IMyEntityChild),
                 get_root_collection(IMyEntityGrandchild),
                 ]
        for coll in colls:
            self.assert_equal(len(coll), 0)


class FileSystemRepositoryTestCase(_FileSystemRepositoryTestCaseMixin,
                                    ResourceTestCase):

    def set_up(self):
        self._set_data_dir()
        self.__copy_data_files()
        try:
            ResourceTestCase.set_up(self)
        except Exception:
            self.__remove_data_files() # Always remove the copied files.
            raise

    def tear_down(self):
        self.__remove_data_files()
        transaction.abort()

    def test_initialization(self):
        colls = [
                 get_root_collection(IMyEntityParent),
                 get_root_collection(IMyEntity),
                 get_root_collection(IMyEntityChild),
                 get_root_collection(IMyEntityGrandchild),
                 ]
        for coll in colls:
            self.assert_equal(len(coll), 1)

    def test_get_read_collection_path(self):
        path = get_read_collection_path(get_collection_class(IMyEntity),
                                        CsvMime, directory=self._data_dir)
        self.assert_false(path is None)
        tmp_dir = tempfile.mkdtemp()
        tmp_path = get_read_collection_path(get_collection_class(IMyEntity),
                                            CsvMime, directory=tmp_dir)
        self.assert_true(tmp_path is None)

    def test_add(self):
        coll = get_root_collection(IMyEntity)
        ent = MyEntity(id=2)
        mb_add = MyEntityMember.create_from_entity(ent)
        coll.add(mb_add)
        transaction.commit()
        self.assert_equal(len(coll), 2)

    def test_add_no_id(self):
        coll = get_root_collection(IMyEntity)
        ent = MyEntity()
        mb_add = MyEntityMember.create_from_entity(ent)
        coll.add(mb_add)
        transaction.commit()
        self.assert_is_not_none(ent.id)
        self.assert_equal(len(coll), 2)

    def test_add_remove(self):
        coll = get_root_collection(IMyEntity)
        mb_rm = iter(coll).next()
        coll.remove(mb_rm)
        ent = MyEntity(id=1)
        mb_add = MyEntityMember.create_from_entity(ent)
        coll.add(mb_add)
        transaction.commit()
        self.assert_equal(len(coll), 1)

    def test_add_remove_same_member(self):
        coll = get_root_collection(IMyEntity)
        ent = MyEntity(id=1)
        mb = MyEntityMember.create_from_entity(ent)
        coll.add(mb)
        transaction.commit()
        coll.remove(mb)
        transaction.commit()
        self.assert_equal(len(coll), 1)

    def test_repeated_add_remove_same_member_no_id(self):
        coll = get_root_collection(IMyEntity)
        ent1 = MyEntity()
        mb1 = MyEntityMember.create_from_entity(ent1)
        coll.add(mb1)
        transaction.commit()
        self.assert_equal(len(coll), 2)
        coll.remove(mb1)
        transaction.commit()
        self.assert_equal(len(coll), 1)
        ent2 = MyEntity()
        mb2 = MyEntityMember.create_from_entity(ent2)
        coll.add(mb2)
        transaction.commit()
        self.assert_equal(len(coll), 2)
        coll.remove(mb2)
        transaction.commit()
        self.assert_equal(len(coll), 1)
        self.assert_not_equal(mb1.id, mb2.id)

    def test_remove_add_same_member(self):
        coll = get_root_collection(IMyEntity)
        mb = iter(coll).next()
        coll.remove(mb)
        transaction.commit()
        coll.add(mb)
        transaction.commit()
        self.assert_equal(len(coll), 1)

    def test_commit(self):
        coll = get_root_collection(IMyEntity)
        mb = iter(coll).next()
        TEXT = 'Changed.'
        mb.text = TEXT
        transaction.commit()
        with open(os.path.join(self._data_dir,
                               "%s.csv" % get_collection_name(coll)),
                  'rU') as data_file:
            lines = data_file.readlines()
        data = lines[1].split(',')
        self.assert_equal(data[3], '"%s"' % TEXT)

    def test_abort(self):
        coll = get_root_collection(IMyEntity)
        mb = iter(coll).next()
        OLD_TEXT = mb.text
        TEXT = 'Changed.'
        mb.text = TEXT
        transaction.abort()
        old_mb = iter(coll).next()
        self.assert_equal(old_mb.text, OLD_TEXT)

    def test_failing_commit(self):
        coll = get_root_collection(IMyEntity)
        mb = iter(coll).next()
        mb.id = None
        self.assert_raises(ValueError, transaction.commit)

    def test_configure(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORY_TYPES.FILE_SYSTEM)
        self.assert_raises(ValueError, repo.configure, foo='bar')

    def __copy_data_files(self):
        orig_data_dir = os.path.join(self._data_dir, 'original')
        for fn in glob.glob1(orig_data_dir, "*.csv"):
            shutil.copy(os.path.join(orig_data_dir, fn), self._data_dir)

    def __remove_data_files(self):
        for fn in glob.glob1(self._data_dir, '*.csv'):
            os.unlink(os.path.join(self._data_dir, fn))


class _MyEntity(Entity):
    pass


class _MyEntityWithSlug(Entity):
    slug = 'slug'


class _MyEntityNoneSlug(Entity):
    slug = None
