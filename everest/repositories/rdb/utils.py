"""
Utilities for the RDBMS backend.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.entities.system import UserMessage
from everest.repositories.rdb.session import ScopedSessionMaker as Session
from everest.repositories.utils import GlobalObjectManager
from inspect import isdatadescriptor
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import clear_mappers as sa_clear_mappers
from sqlalchemy.orm import mapper as sa_mapper
from sqlalchemy.orm.mapper import _mapper_registry
from sqlalchemy.sql.expression import cast
from threading import Lock

__docformat__ = 'reStructuredText en'
__all__ = ['RdbTestCaseMixin',
           'as_slug_expression',
           'clear_mappers',
           'empty_metadata',
           'get_metadata',
           'is_metadata_initialized',
           'map_system_entities',
           'mapper',
           'reset_metadata',
           'set_metadata',
           ]


class _MetaDataManager(GlobalObjectManager):
    _globs = {}
    _lock = Lock()

    @classmethod
    def reset(cls):
        for md in cls._globs.values():
            md.clear()
        clear_mappers()
        super(_MetaDataManager, cls).reset()

get_metadata = _MetaDataManager.get
set_metadata = _MetaDataManager.set
is_metadata_initialized = _MetaDataManager.is_initialized
reset_metadata = _MetaDataManager.reset


def as_slug_expression(attr):
    """
    Converts the given instrumented string attribute into an SQL expression
    that can be used as a slug.

    Slugs are identifiers for members in a collection that can be used in an
    URL. We create slug columns by replacing non-URL characters with dashes
    and lower casing the result. We need this at the ORM level so that we can
    use the slug in a query expression.
    """
    slug_expr = func.replace(attr, ' ', '-')
    slug_expr = func.replace(slug_expr, '_', '-')
    slug_expr = func.lower(slug_expr)
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
    # Set up the slug attribute as a hybrid property.
    if slug_expression is None:
        cls_expr = lambda cls: cast(getattr(cls, 'id'), String)
    else:
        cls_expr = slug_expression
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
        descr = slug_descr.descriptor
    else:
        descr = slug_descr
    class_.slug = hybrid_descriptor(descr, expr=cls_expr)
    return mpr


def synonym(name):
    """
    Utility function mimicking the behavior of the old SA synonym function
    with the new hybrid property semantics.
    """
    return hybrid_property(lambda inst: getattr(inst, name),
                           lambda inst, value: setattr(inst, name, value),
                           expr=lambda cls: getattr(cls, name))


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


def map_system_entities(engine, metadata, reset):
    # Map the user message system entity.
    msg_tbl = Table('_user_messages', metadata,
                    Column('guid', String, nullable=False, primary_key=True),
                    Column('text', String, nullable=False),
                    Column('time_stamp', DateTime(timezone=True),
                           nullable=False, default=func.now()),
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


class RdbTestCaseMixin(object):
    def tear_down(self):
        super(RdbTestCaseMixin, self).tear_down()
        Session.remove()

    @classmethod
    def teardown_class(cls):
        base_cls = super(RdbTestCaseMixin, cls)
        try:
            base_cls.teardown_class()
        except AttributeError:
            pass
        assert not Session.registry.has()
        reset_metadata()
