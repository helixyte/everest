"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 13, 2012.
"""
from everest.entities.base import Entity
from everest.mime import CsvMime
from everest.repository import REPOSITORIES
from everest.resources.entitystores import CachingEntityStore
from everest.resources.entitystores import InMemorySession
from everest.resources.io import get_collection_name
from everest.resources.io import get_read_collection_path
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_root_collection
from everest.testing import Pep8CompliantTestCase
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.interfaces import IMyEntityChild
from everest.tests.testapp_db.interfaces import IMyEntityGrandchild
from everest.tests.testapp_db.interfaces import IMyEntityParent
from everest.tests.testapp_db.resources import MyEntityMember
from everest.utils import get_repository_manager
import gc
import glob
import os
import shutil
import tempfile
import threading
import transaction

__docformat__ = 'reStructuredText en'
__all__ = ['BasicEntityStoreTestCase',
           'FileSystemEmptyEntityStoreTestCase',
           'FileSystemEntityStoreTestCase',
           'InMemorySessionTestCase',
           ]


class BasicEntityStoreTestCase(Pep8CompliantTestCase):
    def test_args(self):
        self.assert_raises(ValueError, CachingEntityStore, 'DUMMY',
                           autocommit=True, join_transaction=True)


class InMemorySessionTestCase(Pep8CompliantTestCase):

    def set_up(self):
        Pep8CompliantTestCase.set_up(self)
        self._entity_store = CachingEntityStore('DUMMY', autoflush=True)
        self._session = InMemorySession(self._entity_store)

    def test_with_autoflush(self):
        ent = _MyEntity()
        self.assert_is_none(ent.id)
        self.assert_is_none(ent.slug)
        self._session.add(_MyEntity, ent)
        self.assert_true(ent in self._session.get_all(_MyEntity))
        # get_all triggered flush - we should have ID & slug now.
        self.assert_is_not_none(ent.id)
        self.assert_is_not_none(ent.slug)
        self.assert_equal(len(self._session.get_all(_MyEntity)), 1)
        self.assert_true(self._session.get_by_id(_MyEntity, ent.id) is ent)
        self.assert_true(self._session.get_by_slug(_MyEntity, ent.slug) is ent)
        self._session.remove(_MyEntity, ent)
        self.assert_equal(len(self._session.get_all(_MyEntity)), 0)
        self.assert_is_none(self._session.get_by_id(_MyEntity, ent.id))
        self.assert_is_none(self._session.get_by_slug(_MyEntity, ent.slug))

    def test_without_autoflush(self):
        ent = _MyEntity()
        self._entity_store.autoflush = False
        self._session.add(_MyEntity, ent)
        self.assert_true(ent in self._session.get_all(_MyEntity))
        # no autoflush - ID & slug should still be none
        self.assert_is_none(ent.id)
        self.assert_is_none(ent.slug)
        #
        self._session.flush()
        self.assert_is_not_none(ent.id)
        self.assert_is_not_none(ent.slug)

    def test_references(self):
        ent = _MyEntity()
        self._session.add(_MyEntity, ent)
        self._session.flush()
        self.assert_equal(len(self._session.get_all(_MyEntity)), 1)
        # Even with the last external ref gone, the cache should hold a
        # reference to the entities it manages.
        del ent
        gc.collect()
        self.assert_equal(len(self._session.get_all(_MyEntity)), 1)

    def test_id_generation(self):
        ent1 = _MyEntity()
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntity()
        self._session.flush()
        self._session.add(_MyEntity, ent2)
        self._session.flush()
        self.assert_equal(ent1.id, 0)
        self.assert_equal(ent2.id, 1)

    def test_with_id_without_slug(self):
        ent = _MyEntityNoneSlug(id=0)
        self._session.add(_MyEntityNoneSlug, ent)
        self.assert_true(self._session.get_by_id(_MyEntityNoneSlug, 0) is ent)

    def test_without_id_with_slug(self):
        ent = _MyEntityWithSlug()
        self._session.add(_MyEntityWithSlug, ent)
        self.assert_true(self._session.get_by_slug(_MyEntityWithSlug, 'slug')
                         is ent)

    def test_duplicate_id_raises_error(self):
        ent1 = _MyEntity()
        self._session.add(_MyEntity, ent1)
        # Trigger flush to create ID.
        self._session.flush()
        self.assert_equal(ent1.id, 0)
        ent2 = _MyEntity(id=0)
        self.assert_raises(ValueError, self._session.add, _MyEntity, ent2)

    def test_duplicate_slug_raises_error(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntityWithSlug, ent1)
        ent2 = _MyEntityWithSlug()
        self.assert_raises(ValueError,
                           self._session.add, _MyEntityWithSlug, ent2)

    def test_cope_with_string_id(self):
        ent = _MyEntity(id='0')
        self._session.add(_MyEntity, ent)
        self.assert_equal(self._session.get_by_id(_MyEntity, ent.id).id,
                          ent.id)
        self.assert_equal(self._session.get_by_slug(_MyEntity, ent.slug).id,
                          ent.id)

    def test_repeated_add_remove(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        self.assert_true(self._session.get_by_slug(_MyEntity, ent1.slug)
                         is ent1)
        self._session.remove(_MyEntity, ent1)
        self.assert_is_none(self._session.get_by_slug(_MyEntity, ent1.slug))
        ent2 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent2)
        self.assert_true(self._session.get_by_slug(_MyEntity, ent2.slug)
                         is ent2)
        self._session.remove(_MyEntity, ent2)
        self.assert_is_none(self._session.get_by_slug(_MyEntity, ent2.slug))
        self.assert_true(ent1.id != ent2.id)

    def test_add_remove_add(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        self._session.commit()
        self._session.remove(_MyEntity, ent1)
        self._session.add(_MyEntity, ent1)
        self.assert_equal(ent1.id, 0)

    def test_remove_without_id(self):
        ent = _MyEntity()
        self._session.add(_MyEntity, ent)
        self._session.remove(_MyEntity, ent)
        self.assert_equal(len(self._session.get_all(_MyEntity)), 0)

    def test_remove_entity_not_in_session_raises_error(self):
        ent = _MyEntity()
        self.assert_raises(ValueError, self._session.remove, _MyEntity, ent)

    def test_replace_without_id_raises_error(self):
        ent1 = _MyEntity(id=0)
        self._session.add(_MyEntity, ent1)
        self._session.commit()
        ent2 = self._session.get_by_id(_MyEntity, 0)
        ent2.id = None
        with self.assert_raises(ValueError) as cm:
            self._session.commit()
        exc_msg = 'Can only replace entities that have an ID.'
        self.assert_equal(cm.exception.message, exc_msg)

    def test_replace_with_different_slug(self):
        ent1 = _MyEntityWithSlug(id=0)
        self._session.add(_MyEntityWithSlug, ent1)
        self._session.commit()
        ent2 = self._session.get_by_id(_MyEntityWithSlug, 0)
        ent2.slug = 'foo'
        self._session.commit()
        ent3 = self._session.get_by_slug(_MyEntityWithSlug, 'foo')
        self.assert_equal(ent3.id, 0)

    def test_threaded_access(self):
        class MyThread(threading.Thread):
            ok = False
            def run(self):
                threading.Thread.run(self)
                self.ok = True
        def access_session(session):
            self.assert_equal(len(session.get_all(_MyEntity)), 0)
        thr = MyThread(target=access_session, args=(self._session,))
        thr.start()
        thr.join()
        self.assert_true(thr.ok)

    def test_failing_flush_duplicate_id(self):
        ent1 = _MyEntity()
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntity()
        self._session.add(_MyEntity, ent2)
        ent2.id = 0
        self.assert_raises(ValueError, self._session.commit)

    def test_failing_flush_duplicate_slug(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntityWithSlug()
        ent2.slug = None
        self._session.add(_MyEntity, ent2)
        ent2.slug = 'slug'
        self.assert_raises(ValueError, self._session.commit)


class _FileSystemEntityStoreTestCaseMixin(object):
    _data_dir = None
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_fs.zcml'

    def _set_data_dir(self):
        self._data_dir = os.path.join(os.path.dirname(__file__),
                                       'testapp_db', 'data')


class FileSystemEmptyEntityStoreTestCase(_FileSystemEntityStoreTestCaseMixin,
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


class FileSystemEntityStoreTestCase(_FileSystemEntityStoreTestCaseMixin,
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
        repo = repo_mgr.get(REPOSITORIES.FILE_SYSTEM)
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
