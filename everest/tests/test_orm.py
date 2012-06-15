"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.entities.interfaces import IEntity
from everest.orm import as_slug_expression
from everest.orm import get_engine
from everest.orm import get_metadata
from everest.orm import is_engine_initialized
from everest.orm import is_metadata_initialized
from everest.orm import mapper
from everest.orm import reset_engines
from everest.orm import reset_metadata
from everest.orm import set_engine
from everest.orm import set_metadata
from everest.testing import Pep8CompliantTestCase
from everest.tests.testapp_db.entities import MyEntity
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.engine import create_engine
from sqlalchemy.sql.expression import Function
from sqlalchemy.sql.expression import cast
from zope.interface import implements # pylint: disable=E0611,F0401
from everest.orm import commit_veto
import os

__docformat__ = 'reStructuredText en'
__all__ = ['OrmTestCase',
           ]


class OrmTestCase(Pep8CompliantTestCase):
    def test_db_engine_manager(self):
        key = 'test'
        self.assert_false(is_engine_initialized(key))
        eng = create_engine('sqlite://')
        set_engine(key, eng)
        self.assert_raises(ValueError, set_engine, key, eng)
        self.assert_true(is_engine_initialized(key))
        self.assert_true(get_engine(key) is eng)
        reset_engines()
        self.assert_false(is_engine_initialized(key))

    def test_metadata_manager(self):
        key = 'test'
        self.assert_false(is_metadata_initialized(key))
        md = MetaData()
        set_metadata(key, md)
        self.assert_raises(ValueError, set_metadata, key, md)
        self.assert_true(is_metadata_initialized(key))
        self.assert_true(get_metadata(key) is md)
        reset_metadata()
        self.assert_false(is_metadata_initialized(key))

    def test_mapper(self):
        class MyDerivedEntity(MyEntity):
            pass
        class MyEntityWithCustomId(object):
            implements(IEntity)

            def __init__(self, id=None): # redefining id pylint: disable=W0622
                self.__id = id
                self.__slug = str(id)

            @property
            def id(self):
                return str(self.__id)

            @property
            def slug(self):
                return str(self.__id)
        t1 = self._make_table(True)
        with self.assert_raises(ValueError) as cm:
            mpr = mapper(MyDerivedEntity, t1, id_attribute='my_id')
        msg_str = 'Attempting to overwrite the mapped'
        self.assert_true(cm.exception.message.startswith(msg_str))
        t2 = self._make_table(False)
        with self.assert_raises(ValueError) as cm:
            mpr = mapper(MyEntityWithCustomId, t2, id_attribute='my_id')
        msg_str = 'Attempting to overwrite the custom data'
        self.assert_true(cm.exception.message.startswith(msg_str))
        #
        slug_expr = lambda cls: as_slug_expression(cast(cls.id, String))
        mpr = mapper(MyDerivedEntity, t2,
                     id_attribute='my_id', slug_expression=slug_expr)
        self.assert_true(MyDerivedEntity.__dict__['slug'].expr
                         is slug_expr)
        self.assert_true(isinstance(MyDerivedEntity.slug, Function))
        mpr.dispose()

    def test_commit_veto(self):
        self.assert_false(commit_veto(os.environ, '200', dict()))
        self.assert_true(commit_veto(os.environ, '300', dict()))
        self.assert_false(commit_veto(os.environ, '300', {'x-tm':'commit'}))

    def _make_table(self, with_id):
        md = MetaData()
        cols = [Column('my_id', Integer, primary_key=True)]
        if with_id:
            cols.append(Column('id', Integer))
        return Table('my_table_with_id_col', md, *cols)
