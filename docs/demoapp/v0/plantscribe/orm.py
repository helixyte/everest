"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 27, 2012.
"""
from everest.orm import as_slug_expression
from everest.orm import mapper
from plantscribe.entities.customer import Customer
from plantscribe.entities.incidence import Incidence
from plantscribe.entities.project import Project
from plantscribe.entities.site import Site
from plantscribe.entities.species import Species
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import literal
from sqlalchemy.sql import select

__docformat__ = 'reStructuredText en'
__all__ = []


def customer_slug(cls):
    return as_slug_expression(cls.last_name + literal('-') + cls.first_name)


def project_slug(cls):
    return as_slug_expression(cls.name)


def species_slug(cls):
    return as_slug_expression(cls.genus_name + literal('-') +
                              cls.species_name + literal('-') +
                              cls.cultivar + literal('-') +
                              cls.author)


def site_slug(cls):
    return as_slug_expression(cls.name)


def incidence_slug(cls):
    return \
        select([Species.slug]).where(cls.species_id == Species.id).as_scalar()


def create_metadata(engine):
    # Create metadata.
    metadata = MetaData()
    # Define a database schema..
    customer_tbl = \
        Table('customer', metadata,
              Column('customer_id', Integer, primary_key=True),
              Column('first_name', String, nullable=False),
              Column('last_name', String, nullable=False),
              )
    project_tbl = \
        Table('project', metadata,
              Column('project_id', Integer, primary_key=True),
              Column('name', String, nullable=False),
              Column('customer_id', Integer,
                     ForeignKey(customer_tbl.c.customer_id),
                     nullable=False),
              )
    site_tbl = \
        Table('site', metadata,
              Column('site_id', Integer, primary_key=True),
              Column('name', String, nullable=False),
              Column('project_id', Integer,
                     ForeignKey(project_tbl.c.project_id),
                     nullable=False),
              )
    species_tbl = \
        Table('species', metadata,
              Column('species_id', Integer, primary_key=True),
              Column('species_name', String, nullable=False),
              Column('genus_name', String, nullable=False),
              Column('cultivar', String, nullable=False, default=''),
              Column('author', String, nullable=False),
              )
    incidence_tbl = \
        Table('incidence', metadata,
              Column('site_id', Integer,
                     ForeignKey(site_tbl.c.site_id),
                     primary_key=True, index=True, nullable=False),
              Column('species_id', Integer,
                     ForeignKey(species_tbl.c.species_id),
                     primary_key=True, index=True, nullable=False),
              Column('quantity', Float, nullable=False),
              )
    # Map tables to entity classes.
    mapper(Customer, customer_tbl,
           id_attribute='customer_id', slug_expression=customer_slug)
    mapper(Project, project_tbl,
           id_attribute='project_id', slug_expression=project_slug,
           properties=dict(customer=relationship(Customer, uselist=False)))
    mapper(Site, site_tbl,
           id_attribute='site_id', slug_expression=site_slug,
           properties=dict(project=relationship(Project, uselist=False)))
    mapper(Species, species_tbl,
           id_attribute='species_id', slug_expression=species_slug)
    mapper(Incidence, incidence_tbl,
           slug_expression=incidence_slug,
           properties=dict(species=relationship(Species, uselist=False),
                           site=relationship(Site, uselist=False)))
    # Configure and initialize metadata.
    metadata.bind = engine
    metadata.create_all()
    return metadata
