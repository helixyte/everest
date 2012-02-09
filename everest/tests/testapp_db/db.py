"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 1, 2011.
"""

from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.entities import MyEntityChild
from everest.tests.testapp_db.entities import MyEntityGrandchild
from everest.tests.testapp_db.entities import MyEntityParent
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship
from sqlalchemy.orm import synonym
from sqlalchemy.sql.expression import cast

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
    # n:m MyEntity child <-> MyEntityGrandchild
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
    def make_slug_hybrid_attr(ent_cls):
        return hybrid_property(ent_cls.slug.fget,
                               expr=lambda cls: cast(cls.id, String))

    mapper(MyEntityParent, my_entity_parent_tbl,
           properties=
            dict(id=synonym('my_entity_parent_id'),
                 child=relationship(MyEntity,
                                    uselist=False,
                                    back_populates='parent'),
                 )
           )
    MyEntityParent.slug = make_slug_hybrid_attr(MyEntityParent)
    mapper(MyEntity, my_entity_tbl,
           properties=
            dict(id=synonym('my_entity_id'),
                 parent=relationship(MyEntityParent,
                                     uselist=False,
                                     back_populates='child'),
                 children=relationship(MyEntityChild,
                                       back_populates='parent',
                                       cascade="all, delete-orphan"),
                 )
           )
    MyEntity.slug = make_slug_hybrid_attr(MyEntity)
    mapper(MyEntityChild, my_entity_child_tbl,
           properties=
            dict(id=synonym('my_entity_child_id'),
                 parent=relationship(MyEntity,
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
    MyEntityChild.slug = make_slug_hybrid_attr(MyEntityChild)
    mapper(MyEntityGrandchild, my_entity_grandchild_tbl,
           properties=
            dict(id=synonym('my_entity_grandchild_id'),
                 parent=relationship(MyEntityChild,
                                     uselist=False,
                                     secondary=my_entity_child_children_tbl,
                                     back_populates='children'),
                 ),
           )
    MyEntityGrandchild.slug = make_slug_hybrid_attr(MyEntityGrandchild)
    # Create the mappers.
    metadata.bind = engine
    metadata.create_all()
    return metadata
