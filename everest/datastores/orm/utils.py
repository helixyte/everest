"""
Utilities for the RDBMS backend.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 7, 2013.
"""
from everest.datastores.orm import Session
from everest.entities.system import UserMessage
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
from sqlalchemy.sql.expression import ClauseList
from sqlalchemy.sql.expression import cast
from threading import Lock

__docformat__ = 'reStructuredText en'
__all__ = ['OrderClauseList',
           'OrmTestCaseMixin',
           'as_slug_expression',
           'clear_mappers',
           'commit_veto',
           'empty_metadata',
           'get_engine',
           'get_metadata',
           'is_engine_initialized',
           'is_metadata_initialized',
           'map_system_entities',
           'mapper',
           'reset_engines',
           'reset_metadata',
           'set_engine',
           'set_metadata',
           ]


class _GlobalObjectManager(object):
    _globs = None
    _lock = None

    @classmethod
    def set(cls, key, obj):
        """
        Sets the given object as global object for the given key.
        """
        with cls._lock:
            if not cls._globs.get(key) is None:
                raise ValueError('Duplicate key "%s".' % key)
            cls._globs[key] = obj
        return cls._globs[key]

    @classmethod
    def get(cls, key):
        """
        Returns the global object for the given key.
        
        :raises KeyError: if no global object was initialized for the given 
          key.
        """
        with cls._lock:
            return cls._globs[key]

    @classmethod
    def is_initialized(cls, key):
        """
        Checks if a global object with the given key has been initialized.
        """
        with cls._lock:
            return not cls._globs.get(key) is None

    @classmethod
    def reset(cls):
        """
        Discards all global objects held by this manager.
        """
        with cls._lock:
            cls._globs.clear()


class _DbEngineManager(_GlobalObjectManager):
    _globs = {}
    _lock = Lock()

    @classmethod
    def reset(cls):
        for engine in cls._globs.values():
            engine.dispose()
        super(_DbEngineManager, cls).reset()

get_engine = _DbEngineManager.get
set_engine = _DbEngineManager.set
is_engine_initialized = _DbEngineManager.is_initialized
reset_engines = _DbEngineManager.reset


class _MetaDataManager(_GlobalObjectManager):
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


class OrderClauseList(ClauseList):
    """
    Custom clause list for ORDER BY clauses.
    
    Suppresses the grouping parentheses which would trigger a syntax error.
    """
    def self_group(self, against=None):
        return self


def commit_veto(request, response): # unused request arg pylint: disable=W0613
    """
    Strict commit veto to use with the transaction manager.
    
    Unlike the default commit veto supplied with the transaction manager,
    this will veto all commits for HTTP status codes other than 2xx unless
    a commit is explicitly requested by setting the "x-tm" response header to
    "commit".
    """
    return not response.status.startswith('2') \
            and not response.headers.get('x-tm') == 'commit'


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
        fget = lambda obj: getattr(obj, id_attribute)
        fset = lambda self, value: setattr(self, id_attribute, value)
        class_.id = hybrid_property(fget, fset=fset, expr=fget)
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


class OrmTestCaseMixin(object):
    def tear_down(self):
        super(OrmTestCaseMixin, self).tear_down()
        Session.remove()

    @classmethod
    def teardown_class(cls):
        base_cls = super(OrmTestCaseMixin, cls)
        try:
            base_cls.teardown_class()
        except AttributeError:
            pass
        assert not Session.registry.has()
        reset_metadata()
