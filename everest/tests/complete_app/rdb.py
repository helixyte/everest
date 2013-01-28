"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 1, 2011.
"""
from everest.repositories.rdb.utils import mapper
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityGrandchild
from everest.tests.complete_app.entities import MyEntityParent
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.orm import relationship

__docformat__ = 'reStructuredText en'
__all__ = ['create_metadata',
           ]



def create_metadata(engine):
    metadata = MetaData()
    #
    # TABLES
    #
    my_entity_parent_tbl = \
        Table('my_entity_parent', metadata,
              Column('my_entity_parent_id', Integer, primary_key=True),
              Column('text', String),
              Column('text_ent', String),
              )
    # 1:1 MyEntity <=> MyEntityParent
    my_entity_tbl = \
        Table('my_entity', metadata,
              Column('my_entity_id', Integer, primary_key=True),
              Column('text', String),
              Column('text_ent', String),
              Column('number', Integer),
              Column('my_entity_parent_id', Integer,
                     ForeignKey(my_entity_parent_tbl.c.my_entity_parent_id),
                     nullable=False),
              )
    # 1:n MyEntity <-> MyEntityChild
    my_entity_child_tbl = \
        Table('my_entity_child', metadata,
              Column('text', String),
              Column('text_ent', String),
              Column('my_entity_child_id', Integer, primary_key=True),
              Column('my_entity_id', Integer,
                     ForeignKey(my_entity_tbl.c.my_entity_id),
                     nullable=False),
              )
    # n:m MyEntityChild <-> MyEntityGrandchild
    my_entity_grandchild_tbl = \
        Table('my_entity_grandchild', metadata,
              Column('text', String),
              Column('text_ent', String),
              Column('my_entity_grandchild_id', Integer, primary_key=True),
              )
    my_entity_child_children_tbl = \
        Table('my_entity_child_children', metadata,
              Column('my_entity_child_id', Integer,
                     ForeignKey(my_entity_child_tbl.c.my_entity_child_id),
                     nullable=False),
              Column('my_entity_grandchild_id', Integer,
                     ForeignKey(
                        my_entity_grandchild_tbl.c.my_entity_grandchild_id),
                     nullable=False)
              )
    #
    # MAPPERS
    #

    mapper(MyEntityParent, my_entity_parent_tbl,
           id_attribute='my_entity_parent_id',
           properties=
            dict(child=relationship(MyEntity,
                                    uselist=False,
                                    back_populates='parent'),
                 )
           )
    mapper(MyEntity, my_entity_tbl,
           id_attribute='my_entity_id',
           properties=
            dict(parent=relationship(MyEntityParent,
                                     uselist=False,
                                     back_populates='child'),
                 children=relationship(MyEntityChild,
                                       back_populates='parent',
                                       cascade="all, delete-orphan"),
                 )
           )
    mapper(MyEntityChild, my_entity_child_tbl,
           id_attribute='my_entity_child_id',
           properties=
            dict(parent=relationship(MyEntity,
                                     uselist=False,
                                     back_populates='children',
                                     cascade='save-update'
                                     ),
                 children=
                    relationship(MyEntityGrandchild,
                                 secondary=my_entity_child_children_tbl,
                                 back_populates='parent'),
                 ),
           )
    mapper(MyEntityGrandchild, my_entity_grandchild_tbl,
           id_attribute='my_entity_grandchild_id',
           properties=
            dict(parent=relationship(MyEntityChild,
                                     uselist=False,
                                     secondary=my_entity_child_children_tbl,
                                     back_populates='children'),
                 ),
           )
    # Create the mappers.
#    metadata.bind = engine
    metadata.create_all(engine)
    return metadata
