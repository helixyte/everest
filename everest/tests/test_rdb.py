"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 1, 2012.
"""
from everest.entities.interfaces import IEntity
from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import get_metadata
from everest.repositories.rdb.utils import hybrid_descriptor
from everest.repositories.rdb.utils import is_metadata_initialized
from everest.repositories.rdb.utils import mapper
from everest.repositories.rdb.utils import reset_metadata
from everest.repositories.rdb.utils import set_metadata
from everest.repositories.utils import get_engine
from everest.repositories.utils import is_engine_initialized
from everest.repositories.utils import reset_engines
from everest.repositories.utils import set_engine
from everest.testing import Pep8CompliantTestCase
from everest.tests.complete_app.entities import MyEntity
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.engine import create_engine
from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.sql.expression import cast
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['RdbTestCase',
           ]


class RdbTestCase(Pep8CompliantTestCase):
    def test_rdb_engine_manager(self):
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

        @implementer(IEntity)
        class MyEntityWithCustomId(object):

            def __init__(self, id=None): # redefining id pylint: disable=W0622
                self.__id = id
                self.__slug = str(id)

            @property
            def id(self):
                return str(self.__id)

            @property
            def slug(self):
                return str(self.__id)

        class MyPolymorphicEntity1(MyEntityWithCustomId):
            pass

        class MyPolymorphicEntity2(MyEntityWithCustomId):
            pass

        t1 = self._make_table(True)
        with self.assert_raises(ValueError) as cm:
            mpr = mapper(MyDerivedEntity, t1, id_attribute='my_id')
        msg_str = 'Attempting to overwrite the mapped'
        self.assert_true(str(cm.exception).startswith(msg_str))
        t2 = self._make_table(False)
        with self.assert_raises(ValueError) as cm:
            mpr = mapper(MyEntityWithCustomId, t2, id_attribute='my_id')
        msg_str = 'Attempting to overwrite the custom data'
        self.assert_true(str(cm.exception).startswith(msg_str))
        #
        slug_expr = lambda cls: as_slug_expression(cast(cls.id, String))
        mpr = mapper(MyDerivedEntity, t2,
                     id_attribute='my_id', slug_expression=slug_expr)
        self.assert_true(MyDerivedEntity.__dict__['slug'].expr
                         is slug_expr)
        self.assert_true(isinstance(MyDerivedEntity.slug, FunctionElement))
        mpr.dispose()
        # Test mapping polymorphic class with custom slug in the base class.
        base_mpr = mapper(MyEntityWithCustomId, t2,
                          polymorphic_on='my_type',
                          polymorphic_identity='base')
        poly_mpr1 = mapper(MyPolymorphicEntity1, inherits=base_mpr,
                           polymorphic_identity='derived')
        self.assert_true(isinstance(MyPolymorphicEntity1.__dict__['slug'],
                                    hybrid_descriptor))
        # We should not override the slug expression if we are inheriting
        # a hybrid descriptor from the base class.
        self.assert_raises(ValueError,
                           mapper, MyPolymorphicEntity2, inherits=base_mpr,
                           polymorphic_identity='derived',
                           slug_expression=slug_expr)
        base_mpr.dispose()
        poly_mpr1.dispose()

    def _make_table(self, with_id):
        md = MetaData()
        cols = [Column('my_id', Integer, primary_key=True),
                Column('my_type', String)]
        if with_id:
            cols.append(Column('id', Integer))
        return Table('my_table_with_id_col', md, *cols)
