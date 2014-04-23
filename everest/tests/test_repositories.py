"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
import os
import tempfile

import pytest
import transaction

from everest.entities.system import UserMessage
from everest.interfaces import IUserMessage
from everest.mime import CsvMime
from everest.repositories.constants import REPOSITORY_TYPES
from everest.repositories.memory import Aggregate
from everest.repositories.memory import Repository
from everest.resources.staging import create_staging_collection
from everest.resources.storing import get_collection_name
from everest.resources.storing import get_read_collection_path
from everest.resources.utils import get_service
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
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.resources import MyEntityChildMember


__docformat__ = 'reStructuredText en'
__all__ = ['TestBasicRepository',
           'TestFileSystemRepository',
           'TestMemorySystemRepository',
           'TestRdbSystemRepository',
           'TestRepositoryManager',
           ]


class TestBasicRepository(object):
    def test_args(self):
        with pytest.raises(ValueError):
            dummy = Repository('DUMMY',
                               aggregate_class=Aggregate,
                               autocommit=True, join_transaction=True)


class TestRepositoryManager(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_repo(self, resource_repo):
        # Access configuration
        resource_repo.configure(messaging_enable=False)
        assert not resource_repo.configuration['messaging_enable']
        # Create a clone and check if slice is the same, but ID is different.
        for meth in (resource_repo.get_collection,
                     resource_repo.get_aggregate):
            acc1 = meth(IMyEntity)
            acc2 = meth(IMyEntity)
            assert id(acc1) != id(acc2)

    def test_init_no_name(self, configurator):
        configurator.begin()
        try:
            repo_mgr = get_repository_manager()
            repo = repo_mgr.new(REPOSITORY_TYPES.MEMORY)
            assert repo.name.startswith(REPOSITORY_TYPES.MEMORY)
        finally:
            configurator.end()

    def test_manager(self, resource_repo):
        repo_mgr = get_repository_manager()
        with pytest.raises(ValueError):
            repo_mgr.set(resource_repo)
        with pytest.raises(ValueError) as cm:
            repo_mgr.new('foo', 'bar')
        exc_msg = 'Unknown repository type'
        assert str(cm.value).startswith(exc_msg)

    def test_set_collection_parent_fails(self, configurator, resource_repo):
        configurator.add_resource(IFoo, FooMember, FooEntity, expose=False)
        coll = create_staging_collection(IFoo)
        srvc = get_service()
        with pytest.raises(ValueError) as cm:
            resource_repo.set_collection_parent(coll, srvc)
        assert str(cm.value).startswith('No root collect')


class _SystemRepositoryBaseTestCase(object):
    package_name = 'everest.tests.simple_app'

    def test_add_update_delete(self, system_resource_repo):
        agg = system_resource_repo.get_aggregate(IUserMessage)
        txt = 'user message.'
        msg = UserMessage(txt)
        agg.add(msg)
        txt1 = 'user message 1.'
        msg1 = UserMessage(txt1, id=msg.id)
        assert msg1.id == msg.id
        msg2 = agg.update(msg1)
        assert msg2.id == msg1.id
        assert msg2.text == txt1
        msg3 = agg.get_by_id(msg.id)
        assert msg3.text == txt1
        agg.remove(msg3)
        assert len(list(agg.iterator())) == 0


class TestMemorySystemRepository(_SystemRepositoryBaseTestCase):
    config_file_name = 'configure_msg_mem_no_views.zcml'


class TestRdbSystemRepository(_SystemRepositoryBaseTestCase):
    config_file_name = 'configure_msg_rdb_no_views.zcml'


class TestFileSystemRepository(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_fs.zcml'

    def test_add(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        ent = MyEntity(id=2)
        mb_add = MyEntityMember.create_from_entity(ent)
        coll.add(mb_add)
        transaction.commit()
        assert len(coll) == 2

    def test_add_no_id(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        ent = MyEntity()
        mb_add = MyEntityMember.create_from_entity(ent)
        coll.add(mb_add)
        transaction.commit()
        assert not ent.id is None
        assert len(coll) == 2

    def test_add_remove(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        mb_rm = next(iter(coll))
        coll.remove(mb_rm)
        ent = MyEntity(id=1)
        mb_add = MyEntityMember.create_from_entity(ent)
        coll.add(mb_add)
        transaction.commit()
        assert len(coll) == 1

    def test_add_remove_same_member(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        ent = MyEntity(id=1)
        mb = MyEntityMember.create_from_entity(ent)
        coll.add(mb)
        coll.remove(mb)
        assert len(coll) == 1

    def test_add_commit_remove_same_member(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        ent1 = MyEntity()
        mb1 = MyEntityMember.create_from_entity(ent1)
        coll.add(mb1)
        transaction.commit()
        assert len(coll) == 2
        #
        mb2 = coll[mb1.id]
        coll.remove(mb2)
        transaction.commit()
        assert len(coll) == 1

    def test_remove_add_same_member(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        mb = next(iter(coll))
        coll.remove(mb)
        transaction.commit()
        # If we add the member with its parent or its children, we will get
        # duplicate key errors.
        ent = mb.get_entity()
        ent.parent = None
        # FIXME: The duplicate key error is actually *not* raised by the
        #        file system repository when the following statement is
        #        commented out!
        while ent.children:
            ent.children.pop()
        coll.add(mb)
        transaction.commit()
        assert len(coll) == 1

    def test_rollback_add(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        ent = MyEntity(id=2)
        mb_add = MyEntityMember.create_from_entity(ent)
        coll.add(mb_add)
        assert len(coll) == 2
        transaction.abort()
        assert len(coll) == 1

    def test_rollback_remove(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        coll.remove(next(iter(coll)))
        assert len(coll) == 0
        transaction.abort()
        assert len(coll) == 1

    def test_rollback_modified(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        mb = next(iter(coll))
        orig_text = mb.text
        new_text = 'CHANGED'
        ent1 = MyEntity(id=0, text=new_text)
        # FIXME: Right now, using .update is necessary to trigger a flush.
        mb.update(ent1)
        assert next(iter(coll)).text == new_text
        transaction.abort()
        mb1 = next(iter(coll))
        assert mb1.text == orig_text

    def test_failing_commit(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        mb = next(iter(coll))
        mb.id = None
        with pytest.raises(ValueError):
            transaction.commit()

    def test_sync_with_repository(self, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        ent = MyEntity()
        mb_add = MyEntityMember.create_from_entity(ent)
        coll.add(mb_add)
        assert mb_add.id is None
        coll.get_aggregate().sync_with_repository()
        assert not mb_add.id is None
        rel_coll = mb_add.children
        ent_child = MyEntityChild()
        mb_add_child = MyEntityChildMember.create_from_entity(ent_child)
        rel_coll.add(mb_add_child)
        assert mb_add_child.id is None
        rel_coll.get_aggregate().sync_with_repository()
        assert not mb_add_child.id is None

    @pytest.mark.parametrize('rc', [IMyEntityParent, IMyEntity,
                                    IMyEntityChild, IMyEntityGrandchild])
    def test_initialization_with_empty_data_dir(self, rc, resource_repo):
        assert len(resource_repo.get_collection(rc)) == 0


    @pytest.mark.parametrize('rc', [IMyEntityParent, IMyEntity,
                                    IMyEntityChild, IMyEntityGrandchild])
    def test_initialization(self, rc, resource_repo_with_data):
        assert len(resource_repo_with_data.get_collection(rc)) == 1

    def test_get_read_collection_path(self, data_dir, configurator):
        configurator.begin()
        try:
            reg = configurator.registry
            orig_data_dir = os.path.join(data_dir, 'original')
            coll_cls = reg.getUtility(IMyEntity, name='collection-class')
            path = get_read_collection_path(coll_cls, CsvMime,
                                            directory=orig_data_dir)
            assert not path is None
            tmp_dir = tempfile.mkdtemp()
            tmp_path = get_read_collection_path(coll_cls, CsvMime,
                                                directory=tmp_dir)
            assert tmp_path is None
        finally:
            configurator.end()

    def test_commit(self, data_dir, resource_repo_with_data):
        coll = resource_repo_with_data.get_collection(IMyEntity)
        mb = next(iter(coll))
        TEXT = 'Changed.'
        mb.text = TEXT
        transaction.commit()
        with open(os.path.join(data_dir,
                               "%s.csv" % get_collection_name(coll)),
                  'rU') as data_file:
            lines = data_file.readlines()
        data = lines[1].split(',')
        assert data[2] == '"%s"' % TEXT

    def test_configure(self, resource_repo_with_data):
        with pytest.raises(ValueError):
            resource_repo_with_data.configure(foo='bar')


class TestMemoryRepoWithCacheLoader(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_memory_repo_with_cache_loader.zcml'

    def test_repo_has_loaded_entities(self, resource_repo):
        default_agg = resource_repo.get_aggregate(IMyEntity)
        assert len(list(default_agg.iterator())) == 0
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get('CUSTOM_MEMORY_WITH_CACHE_LOADER')
        agg = repo.get_aggregate(IMyEntity)
        assert len(list(agg.iterator())) == 1


def entity_loader(entity_class):
    return [entity_class()]
