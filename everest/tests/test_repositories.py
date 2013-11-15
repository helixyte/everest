"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.entities.system import UserMessage
from everest.entities.utils import get_root_aggregate
from everest.interfaces import IUserMessage
from everest.mime import CsvMime
from everest.repositories.constants import REPOSITORY_TYPES
from everest.repositories.interfaces import IRepository
from everest.repositories.manager import HAS_MONGO
from everest.repositories.memory import Aggregate
from everest.repositories.memory import Repository
from everest.resources.io import get_collection_name
from everest.resources.io import get_read_collection_path
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import get_service
from everest.testing import Pep8CompliantTestCase
from everest.testing import ResourceTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityGrandchild
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild
from everest.tests.complete_app.interfaces import IMyEntityGrandchild
from everest.tests.complete_app.interfaces import IMyEntityParent
from everest.tests.complete_app.resources import MyEntityMember
from everest.tests.simple_app.entities import FooEntity
from everest.tests.simple_app.interfaces import IFoo
from everest.tests.simple_app.resources import FooMember
from everest.utils import get_repository_manager
from iso8601 import iso8601
import glob
import os
import shutil
import tempfile
import transaction

__docformat__ = 'reStructuredText en'
__all__ = ['BasicRepositoryTestCase',
           'FileSystemEmptyRepositoryTestCase',
           'FileSystemRepositoryTestCase',
           'MemorySystemRepositoryTestCase',
           'RdbSystemRepositoryTestCase',
           'RepositoryManagerTestCase',
           ]


class BasicRepositoryTestCase(Pep8CompliantTestCase):
    def test_args(self):
        self.assert_raises(ValueError, Repository, 'DUMMY',
                           aggregate_class=Aggregate,
                           autocommit=True, join_transaction=True)


class RepositoryManagerTestCase(ResourceTestCase):
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

    def test_init_no_name(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.new(REPOSITORY_TYPES.MEMORY)
        self.assert_true(repo.name.startswith(REPOSITORY_TYPES.MEMORY))

    def test_manager(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORY_TYPES.MEMORY)
        self.assert_raises(ValueError, repo_mgr.set, repo)
        with self.assert_raises(ValueError) as cm:
            repo_mgr.new('foo', 'bar')
        exc_msg = 'Unknown repository type.'
        self.assert_equal(str(cm.exception), exc_msg)

    def test_set_collection_parent_fails(self):
        self.config.add_resource(IFoo, FooMember, FooEntity, expose=False)
        coll = create_staging_collection(IFoo)
        srvc = get_service()
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORY_TYPES.MEMORY)
        with self.assert_raises(ValueError) as cm:
            repo.set_collection_parent(coll, srvc)
        self.assert_true(str(cm.exception).startswith('No root collect'))


class _SystemRepositoryBaseTestCase(ResourceTestCase):
    package_name = 'everest.tests.simple_app'

    def test_add_update_delete(self):
        agg = get_root_aggregate(IUserMessage)
        txt = 'user message.'
        msg = UserMessage(txt)
        agg.add(msg)
        txt1 = 'user message 1.'
        msg1 = UserMessage(txt1, id=msg.id)
        self.assert_equal(msg1.id, msg.id)
        msg2 = agg.update(msg1)
        self.assert_equal(msg2.id, msg1.id)
        self.assert_equal(msg2.text, txt1)
        msg3 = agg.get_by_id(msg.id)
        self.assert_equal(msg3.text, txt1)
        agg.remove(msg3)
        self.assert_equal(len(list(agg.iterator())), 0)


class MemorySystemRepositoryTestCase(_SystemRepositoryBaseTestCase):
    def _load_custom_zcml(self):
        self.config.setup_system_repository(REPOSITORY_TYPES.MEMORY)


class RdbSystemRepositoryTestCase(_SystemRepositoryBaseTestCase):
    def _load_custom_zcml(self):
        self.config.setup_system_repository(REPOSITORY_TYPES.RDB)


class _RepositoryTestCase(ResourceTestCase):
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
        mb_rm = next(iter(coll))
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
        coll.remove(mb)
        self.assert_equal(len(coll), 1)

    def test_add_commit_remove_same_member(self):
        coll = get_root_collection(IMyEntity)
        ent1 = MyEntity()
        mb1 = MyEntityMember.create_from_entity(ent1)
        coll.add(mb1)
        transaction.commit()
        self.assert_equal(len(coll), 2)
        #
        mb2 = coll[mb1.id]
        coll.remove(mb2)
        transaction.commit()
        self.assert_equal(len(coll), 1)

    def test_remove_add_same_member(self):
        coll = get_root_collection(IMyEntity)
        mb = next(iter(coll))
        coll.remove(mb)
        transaction.commit()
        # If we add the member with its parent, we will get a duplicate key
        # error for the parent.
        mb.parent = None
        coll.add(mb)
        transaction.commit()
        self.assert_equal(len(coll), 1)

    def test_rollback_add(self):
        coll = get_root_collection(IMyEntity)
        ent = MyEntity(id=2)
        mb_add = MyEntityMember.create_from_entity(ent)
        coll.add(mb_add)
        self.assert_equal(len(coll), 2)
        transaction.abort()
        self.assert_equal(len(coll), 1)

    def test_rollback_remove(self):
        coll = get_root_collection(IMyEntity)
        coll.remove(next(iter(coll)))
        self.assert_equal(len(coll), 0)
        transaction.abort()
        self.assert_equal(len(coll), 1)

    def test_rollback_modified(self):
        coll = get_root_collection(IMyEntity)
        mb = next(iter(coll))
        orig_text = mb.text
        new_text = 'CHANGED'
        ent1 = MyEntity(id=0, text=new_text)
        # FIXME: Right now, using .update is necessary to trigger a flush.
        mb.update(ent1)
        self.assert_equal(next(iter(coll)).text, new_text)
        transaction.abort()
        mb1 = next(iter(coll))
        self.assert_equal(mb1.text, orig_text)

    def test_failing_commit(self):
        coll = get_root_collection(IMyEntity)
        mb = next(iter(coll))
        mb.id = None
        self.assert_raises(ValueError, transaction.commit)


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
                                   _RepositoryTestCase):

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

    def test_commit(self):
        coll = get_root_collection(IMyEntity)
        mb = next(iter(coll))
        TEXT = 'Changed.'
        mb.text = TEXT
        transaction.commit()
        with open(os.path.join(self._data_dir,
                               "%s.csv" % get_collection_name(coll)),
                  'rU') as data_file:
            lines = data_file.readlines()
        data = lines[1].split(',')
        self.assert_equal(data[2], '"%s"' % TEXT)

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


class MemoryRepoWithCacheLoaderTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_memory_repo_with_cache_loader.zcml'

    def test_repo_has_loaded_entities(self):
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get('CUSTOM_MEMORY_WITH_CACHE_LOADER')
        agg = repo.get_aggregate(IMyEntity)
        self.assert_equal(len(list(agg.iterator())), 1)


def entity_loader(entity_class):
    return [entity_class()]


if HAS_MONGO:
    class NoSqlRepositoryTestCase(_RepositoryTestCase):
        package_name = 'everest.tests.complete_app'
        config_file_name = 'configure_nosql.zcml'

        def set_up(self):
            ResourceTestCase.set_up(self)
            # FIXME: This uses a lot of the machinery we are trying to test
            #        here. We should have some sort of pre-loading facility
            #        like the cache loader for the entity repo.
            ent = MyEntity(id=0, number=1, text_ent='TEST',
                           date_time=
                             iso8601.parse_date('2012-06-13 11:06:47+02:00'))
            parent = MyEntityParent(id=0, text_ent='TEXT')
            ent.parent = parent
            child = MyEntityChild(id=0, text_ent='TEXT')
            ent.children.append(child)
            grandchild = MyEntityGrandchild(id=0, text='TEXT')
            child.children.append(grandchild)
            coll = get_root_collection(IMyEntity)
            coll.create_member(ent)
            transaction.commit()

        def tear_down(self):
            transaction.abort()

        def test_init(self):
            repo_mgr = get_repository_manager()
            repo = repo_mgr.get(REPOSITORY_TYPES.NO_SQL)
            self.assert_true(IRepository.providedBy(repo)) # pylint: disable=E1101

        def test_commit(self):
            coll = get_root_collection(IMyEntity)
            mb = next(iter(coll))
            TEXT = 'Changed.'
            mb.text = TEXT
            transaction.commit()
