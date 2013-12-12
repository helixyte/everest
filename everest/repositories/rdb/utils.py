"""
Utilities for the rdb backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.entities.system import UserMessage
from everest.repositories.utils import GlobalObjectManager
from inspect import isdatadescriptor
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import func as sa_func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import clear_mappers as sa_clear_mappers
from sqlalchemy.orm import mapper as sa_mapper
from sqlalchemy.orm.interfaces import MANYTOMANY
from sqlalchemy.orm.interfaces import MANYTOONE
from sqlalchemy.orm.interfaces import ONETOMANY
from sqlalchemy.orm.mapper import _mapper_registry
from sqlalchemy.sql.expression import cast
from threading import Lock

__docformat__ = 'reStructuredText en'
__all__ = ['OrmAttributeInspector',
           'as_slug_expression',
           'clear_mappers',
           'empty_metadata',
           'get_metadata',
           'hybrid_descriptor',
           'is_metadata_initialized',
           'map_system_entities',
           'mapper',
           'reset_metadata',
           'set_metadata',
           'synonym',
           ]


class _MetaDataManager(GlobalObjectManager):
    _globs = {}
    _lock = Lock()

    @classmethod
    def reset(cls):
        # This removes all attribute instrumentation from the entity classes.
        clear_mappers()
        # This is *very* important - the ORM attribute inspector caches
        # attributes which have become invalidated by the clearing of the
        # mappers.
        OrmAttributeInspector.reset()
        for md in cls._globs.values():
            md.clear()
        super(_MetaDataManager, cls).reset()

get_metadata = _MetaDataManager.get
set_metadata = _MetaDataManager.set
is_metadata_initialized = _MetaDataManager.is_initialized
reset_metadata = _MetaDataManager.reset


def clear_mappers():
    """
    Clears all mappers set up by SA and also clears all custom "id" and
    "slug" attributes inserted by the :func:`mapper` function in this module.

    This should only ever be needed in a testing context.
    """
    # Remove our hybrid property constructs.
    for mpr, is_primary in _mapper_registry.items():
        if is_primary:
            for attr_name in ('id', 'slug'):
                try:
                    attr = object.__getattribute__(mpr.class_, attr_name)
                    if isinstance(attr, hybrid_property):
                        if attr_name == 'id':
                            delattr(mpr.class_, attr_name)
                        else:
                            setattr(mpr.class_, attr_name, attr.descriptor)
                except AttributeError:
                    pass
    sa_clear_mappers()


def as_slug_expression(attr):
    """
    Converts the given instrumented string attribute into an SQL expression
    that can be used as a slug.

    Slugs are identifiers for members in a collection that can be used in an
    URL. We create slug columns by replacing non-URL characters with dashes
    and lower casing the result. We need this at the ORM level so that we can
    use the slug in a query expression.
    """
    slug_expr = sa_func.replace(attr, ' ', '-')
    slug_expr = sa_func.replace(slug_expr, '_', '-')
    slug_expr = sa_func.lower(slug_expr)
    return slug_expr


class hybrid_descriptor(hybrid_property):
    """
    Helper class wrapping a data descriptor into a hybrid property.
    """
    def __init__(self, descriptor, expr=None):
        self.__descriptor = descriptor
        hybrid_property.__init__(self, descriptor.fget,
                                 fset=descriptor.fset, fdel=descriptor.fdel,
                                 expr=expr)

    @property
    def descriptor(self):
        return self.__descriptor


def mapper(class_, local_table=None, id_attribute='id', slug_expression=None,
           *args, **kwargs):
    """
    Convenience wrapper around the SA mapper which will set up the hybrid
    "id" and "slug" attributes required by everest after calling the SA
    mapper.

    If you (e.g., for testing purposes) want to clear mappers created with
    this function, use the :func:`clear_mappers` function in this module.

    :param str id_attribute: the name of the column in the table to use as
      ID column (will be aliased to a new "id" attribute in the mapped class)
    :param slug_expression: function to generate a slug SQL expression given
      the mapped class as argument.
    """
    mpr = sa_mapper(class_, local_table=local_table, *args, **kwargs)
    # Set up the ID attribute as a hybrid property, if necessary.
    if id_attribute != 'id':
        # Make sure we are not overwriting an already mapped or customized
        # 'id' attribute.
        if 'id' in mpr.columns:
            mpr.dispose()
            raise ValueError('Attempting to overwrite the mapped "id" '
                             'attribute.')
        elif isdatadescriptor(getattr(class_, 'id', None)):
            mpr.dispose()
            raise ValueError('Attempting to overwrite the custom data '
                             'descriptor defined for the "id" attribute.')
        class_.id = synonym(id_attribute)
    # If this is a polymorphic class, a base class may already have a
    # hybrid descriptor set as slug attribute.
    slug_descr = None
    for base_cls in class_.__mro__:
        try:
            slug_descr = object.__getattribute__(base_cls, 'slug')
        except AttributeError:
            pass
        else:
            break
    if isinstance(slug_descr, hybrid_descriptor):
        if not slug_expression is None:
            raise ValueError('Attempting to overwrite the expression for '
                             'an inherited slug hybrid descriptor.')
        hyb_descr = slug_descr
    else:
        # Set up the slug attribute as a hybrid property.
        if slug_expression is None:
            cls_expr = lambda cls: cast(getattr(cls, 'id'), String)
        else:
            cls_expr = slug_expression
        hyb_descr = hybrid_descriptor(slug_descr, expr=cls_expr)
    class_.slug = hyb_descr
    return mpr


def synonym(name):
    """
    Utility function mimicking the behavior of the old SA synonym function
    with the new hybrid property semantics.
    """
    return hybrid_property(lambda inst: getattr(inst, name),
                           lambda inst, value: setattr(inst, name, value),
                           expr=lambda cls: getattr(cls, name))


def map_system_entities(engine, metadata, reset):
    """
    Maps all system entities.
    """
    # Map the user message system entity.
    msg_tbl = Table('_user_messages', metadata,
                    Column('guid', String, nullable=False, primary_key=True),
                    Column('text', String, nullable=False),
                    Column('time_stamp', DateTime(timezone=True),
                           nullable=False, default=sa_func.now()),
                    )
    mapper(UserMessage, msg_tbl, id_attribute='guid')
    if reset:
        metadata.drop_all(bind=engine, tables=[msg_tbl])
    metadata.create_all(bind=engine, tables=[msg_tbl])


def empty_metadata(engine):
    """
    The default metadata factory.
    """
    metadata = MetaData()
    metadata.create_all(bind=engine)
    return metadata


class OrmAttributeInspector(object):
    """
    Helper class inspecting class attributes mapped by the ORM.
    """
    __cache = {}

    @staticmethod
    def reset():
        """
        This clears the attribute cache this inspector maintains.

        Only needed in a testing context.
        """
        OrmAttributeInspector.__cache.clear()

    @staticmethod
    def inspect(orm_class, attribute_name):
        """
        :param attribute_name: name of the mapped attribute to inspect.
        :returns: list of 2-tuples containing information about the inspected
          attribute (first element: mapped entity attribute kind; second
          attribute: mapped entity attribute)
        """
        key = (orm_class, attribute_name)
        elems = OrmAttributeInspector.__cache.get(key)
        if elems is None:
            elems = OrmAttributeInspector.__inspect(key)
            OrmAttributeInspector.__cache[key] = elems
        return elems

    @staticmethod
    def __inspect(key):
        orm_class, attribute_name = key
        elems = []
        entity_type = orm_class
        ent_attr_tokens = attribute_name.split('.')
        count = len(ent_attr_tokens)
        for idx, ent_attr_token in enumerate(ent_attr_tokens):
            entity_attr = getattr(entity_type, ent_attr_token)
            kind, attr_type = OrmAttributeInspector.__classify(entity_attr)
            if idx == count - 1:
                pass
                # We are at the last name token - this must be a TERMINAL
                # or an ENTITY.
#                if kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION:
#                    raise ValueError('Invalid attribute name "%s": the '
#                                     'last element (%s) references an '
#                                     'aggregate attribute.'
#                                     % (attribute_name, ent_attr_token))
            else:
                if kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                    # We should not get here - the last attribute was a
                    # terminal.
                    raise ValueError('Invalid attribute name "%s": the '
                                     'element "%s" references a terminal '
                                     'attribute.'
                                     % (attribute_name, ent_attr_token))
                entity_type = attr_type
            elems.append((kind, entity_attr))
        return elems

    @staticmethod
    def __classify(attr):
        # Looks up the entity attribute kind and target type for the given
        # entity attribute.
        # We look for an attribute "property" to identify mapped attributes
        # (instrumented attributes and attribute proxies).
        if not hasattr(attr, 'property'):
            raise ValueError('Attribute "%s" is not mapped.' % attr)
        # We detect terminals by the absence of an "argument" attribute of
        # the attribute's property.
        if not hasattr(attr.property, 'argument'):
            kind = RESOURCE_ATTRIBUTE_KINDS.TERMINAL
            target_type = None
        else: # We have a relationship.
            target_type = attr.property.argument
            if attr.property.direction in (ONETOMANY, MANYTOMANY):
                if not attr.property.uselist:
                    # 1:1
                    kind = RESOURCE_ATTRIBUTE_KINDS.MEMBER
                else:
                    # 1:n or n:m
                    kind = RESOURCE_ATTRIBUTE_KINDS.COLLECTION
            elif attr.property.direction == MANYTOONE:
                kind = RESOURCE_ATTRIBUTE_KINDS.MEMBER
            else:
                raise ValueError('Unsupported relationship direction "%s".' # pragma: no cover
                                 % attr.property.direction)
        return kind, target_type
