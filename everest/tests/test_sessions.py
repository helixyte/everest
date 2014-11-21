"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 13, 2012.
"""
import gc

import pytest

from everest.entities.utils import new_entity_id
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityParent


__docformat__ = 'reStructuredText en'
__all__ = ['TestJoinedTransactionMemorySession',
           'TestTransactionLessMemorySession',
           ]


class _TestMemorySession(object):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'
    def test_basics(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        assert ent.id is None
        assert ent.slug is None
        # Load without ID fails.
        with pytest.raises(ValueError) as cm:
            session.load(MyEntity, ent)
        assert cm.value.args[0].startswith('Can not load')
        session.add(MyEntity, ent)
        assert ent in session
        assert ent in session.query(MyEntity)
        assert list(session.new) == [ent]
        # Commit triggers ID generation.
        session.commit()
        assert not ent.id is None
        assert not ent.slug is None
        # After commit, the session is empty.
        assert not ent in session
        assert len(session.query(MyEntity).all()) == 1
        # Test loading by ID and slug.
        fetched_ent0 = session.get_by_id(MyEntity, ent.id)
        assert fetched_ent0.slug == ent.slug
        fetched_ent1 = session.get_by_slug(MyEntity, ent.slug)[0]
        assert fetched_ent1.id == ent.id
        # We get a clone when we load an entity from the session.
        assert not fetched_ent0 is ent
        # Once loaded, we always get the same entity.
        assert fetched_ent0 is fetched_ent1
        session.remove(MyEntity, fetched_ent0)
        assert len(session.query(MyEntity).all()) == 0
        assert session.get_by_id(MyEntity, ent.id) is None
        assert session.get_by_slug(MyEntity, ent.slug) is None
        assert list(session.deleted) == [fetched_ent0]

    def test_remove_entity_not_in_session_raises_error(self,
                                                       class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        with pytest.raises(ValueError):
            session.remove(MyEntity, ent)

    def test_add_deleted(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        session.add(MyEntity, ent)
        session.commit()
        session.remove(MyEntity, ent)
        session.add(MyEntity, ent)

    def test_add_same_slug(self, class_entity_repo, monkeypatch):
        monkeypatch.setattr(MyEntity, 'slug', None)
        session = class_entity_repo.session_factory()
        ent0 = MyEntity(id=0)
        ent0.slug = str(ent0.id)
        ent1 = MyEntity(id=1)
        ent1.slug = ent0.slug
        session.add(MyEntity, ent0)
        session.add(MyEntity , ent1)
        ents = session.get_by_slug(MyEntity, '0')
        assert len(ents) == 2

    def test_nested(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        parent = MyEntityParent()
        ent.parent = parent
        child = MyEntityChild()
        ent.children.append(child)
        session.add(MyEntity, ent)
        session.commit()
        assert len(session.query(MyEntityChild).all()) == 1
        assert len(session.query(MyEntityParent).all()) == 1
        fetched_ent = session.query(MyEntity).one()
        assert not fetched_ent.parent is None
        assert len(fetched_ent.children) == 1

    def test_nested_with_set_collection_type(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        child = MyEntityChild()
        ent.children = set([child])
        session.add(MyEntity, ent)
        session.commit()
        fetched_ent = session.query(MyEntity).one()
        assert isinstance(fetched_ent.children, set)

    def test_nested_with_invalid_collection_type(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        child = MyEntityChild()
        ent.children = (child,)
        with pytest.raises(ValueError):
            session.add(MyEntity, ent)
        ent.id = 0
        child.id = 0
        with pytest.raises(ValueError) as cm:
            session.load(MyEntity, ent)
        assert cm.value.args[0].startswith('Do not know')

    def test_nested_with_invalid_collection_data(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        ent.children = [None]
        with pytest.raises(ValueError):
            session.add(MyEntity, ent)


class TestJoinedTransactionMemorySession(_TestMemorySession):
    repo_joins_transaction = True


class TestTransactionLessMemorySession(_TestMemorySession):
    repo_joins_transaction = False

    def test_update_entity_not_in_session_raises_error(self,
                                                       class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        with pytest.raises(ValueError):
            session.update(MyEntity, ent)

    def test_get_entity_not_in_session(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        assert session.get_by_id(MyEntity, '-1') is None

    def test_references(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        session.add(MyEntity, ent)
        assert len(session.query(MyEntity).all()) == 1
        # Even with the last external ref gone, the cache should hold a
        # reference to the entities it manages.
        del ent
        gc.collect()
        assert len(session.query(MyEntity).all()) == 1

    def test_id_generation(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent1 = MyEntity()
        session.add(MyEntity, ent1)
        session.commit()
        assert not ent1.id is None
        ent2 = MyEntity()
        session.add(MyEntity, ent2)
        session.commit()
        assert not ent2.id is None
        # entity IDs can be sorted by creation time.
        assert ent2.id > ent1.id

    def test_with_id_without_slug(self, class_entity_repo, monkeypatch):
        monkeypatch.setattr(MyEntity, 'slug', None)
        session = class_entity_repo.session_factory()
        ent = MyEntity(id=0)
        session.add(MyEntity, ent)
        assert session.get_by_id(MyEntity, 0) is ent

    def test_without_id_with_slug(self, class_entity_repo, monkeypatch):
        monkeypatch.setattr(MyEntity, 'slug', 'slug')
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        session.add(MyEntity, ent)
        assert session.get_by_slug(MyEntity, 'slug')[0] is ent

    def test_duplicate_id_raises_error(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent_id = new_entity_id()
        ent1 = MyEntity(id=ent_id)
        session.add(MyEntity, ent1)
        ent2 = MyEntity(id=ent_id)
        with pytest.raises(ValueError):
            session.add(MyEntity, ent2)

    def test_cope_with_numeric_id(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity(id=0)
        session.add(MyEntity, ent)
        assert session.get_by_id(MyEntity, ent.id).id == ent.id
        assert session.get_by_slug(MyEntity, ent.slug)[0].id == ent.id

    def test_repeated_add_remove(self, class_entity_repo, monkeypatch):
        monkeypatch.setattr(MyEntity, 'slug', 'slug')
        session = class_entity_repo.session_factory()
        ent1 = MyEntity()
        session.add(MyEntity, ent1)
        assert session.get_by_slug(MyEntity, ent1.slug)[0] is ent1
        session.remove(MyEntity, ent1)
        assert session.get_by_slug(MyEntity, ent1.slug) is None
        ent2 = MyEntity()
        session.add(MyEntity, ent2)
        assert session.get_by_slug(MyEntity, ent2.slug)[0] is ent2
        session.remove(MyEntity, ent2)
        assert session.get_by_slug(MyEntity, ent2.slug) is None

    def test_remove_flush_add(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent = MyEntity()
        session.add(MyEntity, ent)
        session.commit()
        assert len(session.query(MyEntity).all()) == 1
        session.remove(MyEntity, ent)
        assert len(session.query(MyEntity).all()) == 0
        session.add(MyEntity, ent)
        assert len(session.query(MyEntity).all()) == 1

    def test_add_immediate_remove(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent1 = MyEntity()
        session.add(MyEntity, ent1)
        session.remove(MyEntity, ent1)
        assert not ent1 in session
        assert len(session.query(MyEntity).all()) == 0

    def test_add_remove_add(self, class_entity_repo, monkeypatch):
        monkeypatch.setattr(MyEntity, 'slug', 'slug')
        session = class_entity_repo.session_factory()
        ent1 = MyEntity()
        session.add(MyEntity, ent1)
        assert ent1 in session
        session.remove(MyEntity, ent1)
        assert not ent1 in session
        session.add(MyEntity, ent1)
        assert ent1 in session

    def test_update_without_id_raises_error(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent1 = MyEntity(id=0)
        session.add(MyEntity, ent1)
        session.commit()
        # Re-load.
        ent2 = session.load(MyEntity, ent1)
        ent2.id = None
        with pytest.raises(ValueError) as cm:
            session.commit()
        exc_msg = 'Could not persist data - target entity not found'
        assert str(cm.value).startswith(exc_msg)

    def test_update_with_different_slug(self, class_entity_repo, monkeypatch):
        monkeypatch.setattr(MyEntity, 'slug', 'slug')
        session = class_entity_repo.session_factory()
        ent_id = 0
        ent1 = MyEntity(id=ent_id)
        session.add(MyEntity, ent1)
        ent2 = session.get_by_id(MyEntity, ent_id)
        text = 'foo'
        ent2.slug = text
        session.commit()
        ent3 = session.query(MyEntity).filter_by(slug=text).one()
        assert ent3.id == ent_id

    def test_failing_commit_duplicate_id(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent1 = MyEntity()
        session.add(MyEntity, ent1)
        ent2 = MyEntity()
        session.add(MyEntity, ent2)
        assert ent1.id is None
        assert ent2.id is None
        ent2.id = ent1.id = 0
        with pytest.raises(ValueError):
            session.commit()

    def test_find_added_by_id(self, class_entity_repo, monkeypatch):
        monkeypatch.setattr(MyEntity, 'slug', 'slug')
        session = class_entity_repo.session_factory()
        ent1 = MyEntity(id=0)
        session.add(MyEntity, ent1)
        ent2 = session.get_by_id(MyEntity, ent1.id)
        assert not ent2 is None
        assert ent1.id == ent2.id

    def test_find_added_by_slug(self, class_entity_repo, monkeypatch):
        monkeypatch.setattr(MyEntity, 'slug', 'slug')
        session = class_entity_repo.session_factory()
        ent1 = MyEntity()
        session.add(MyEntity, ent1)
        ents = session.get_by_slug(MyEntity, ent1.slug)
        assert not ents is None
        assert ent1.id == ents[0].id

    def test_find_added_with_none_slug_by_slug(self, class_entity_repo,
                                               monkeypatch):
        monkeypatch.setattr(MyEntity, 'slug', None)
        session = class_entity_repo.session_factory()
        ent1 = MyEntity()
        session.add(MyEntity, ent1)
        ent1.slug = 'testslug'
        ents = session.get_by_slug(MyEntity, ent1.slug)
        assert not ents is None
        assert ent1.id == ents[0].id

    def test_update(self, class_entity_repo):
        session = class_entity_repo.session_factory()
        ent1 = MyEntity(id=0)
        session.add(MyEntity, ent1)
        ent2 = MyEntity()
        ent2.id = ent1.id
        my_attr_value = 1
        ent2.number = my_attr_value
        session.update(MyEntity, ent2)
        ent3 = session.get_by_id(MyEntity, ent1.id)
        assert not ent3 is None
        assert ent3.id == ent1.id
        assert ent3.number == my_attr_value
