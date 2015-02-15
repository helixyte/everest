"""
Session for the rdb backend.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 8, 2013.
"""
from collections import OrderedDict
from collections import defaultdict

from pyramid.compat import itervalues_
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.base import class_mapper
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.session import Session as SaSession

from everest.attributes import is_collection_attribute
from everest.attributes import is_terminal_attribute
from everest.constants import RELATION_OPERATIONS
from everest.entities.base import Entity
from everest.entities.interfaces import IEntity
from everest.entities.traversal import AruVisitor
from everest.entities.utils import get_entity_class
from everest.repositories.base import AutocommittingSessionMixin
from everest.repositories.base import Session
from everest.repositories.base import SessionFactory
from everest.repositories.state import EntityState
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import RepresenterConfigTraverser
from everest.representers.config import RepresenterConfigVisitorBase
from everest.resources.attributes import get_resource_class_attribute
from everest.resources.utils import get_member_class
from everest.resources.utils import provides_member_resource
from everest.traversal import SourceTargetDataTreeTraverser
from zope.sqlalchemy import ZopeTransactionExtension # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['RdbAutocommittingSession',
           'RdbSession',
           'RdbSessionFactory',
           'ScopedSessionMaker',
           ]


class RdbRepresenterConfigVisitor(RepresenterConfigVisitorBase):
    """
    Representer configuration visitor for a RDB session.

    This visitor builds joinedload query options depending on the traversed
    representer configuration settings for optimized loading.

    The visitor expects the incoming keys to be a) normalized (i.e., a key
    of length 3 will also have "root" keys of length 2 and 1); and b)
    traversed depth-first.

    The traversal result is recorded in the `loader_options` attribute.
    """
    def __init__(self, context):
        # Context resource.
        self._context = context
        # Dictionary mapping attributes to lists of entity attribute names.
        self.__attr_map = OrderedDict()

    def visit(self, key, attribute_options):
        # We only collect load options for attributes which are explicitly not
        # ignored or member attributes unless they are explicitly ignored.
        ignore_opt = attribute_options.get(IGNORE_OPTION)
        if not ignore_opt is True:
            rc = get_member_class(self._context)
            entity_attr_names = []
            store_key = True
            for idx, attr_name in enumerate(key):
                attr = get_resource_class_attribute(rc, attr_name)
                if attr is None:
                    # Referencing non-existing attribute; ignore.
                    store_key = False
                    break
                elif idx == 0 \
                     and is_collection_attribute(attr) \
                     and not ignore_opt is False:
                    # Referencing collection attribute which was not
                    # explicitly enabled.
                    store_key = False
                    break
                entity_attr_name = attr.entity_attr
                if is_terminal_attribute(attr):
                    if '.' in entity_attr_name:
                        entity_attr_name = \
                            entity_attr_name[:entity_attr_name.rfind('.')]
                    else:
                        store_key = False
                        break
                entity_attr_names.append(entity_attr_name)
                rc = attr.attr_type
            if store_key:
                self.__attr_map[key] = entity_attr_names

    @property
    def loader_options(self):
        """
        Dictionary mapping each entity class to configure a loader for to a
        list of (possibly nested) entity attribute names.
        """
        all_keys = set(self.__attr_map.keys())
        # Go through the collected keys and through out all keys which are
        # subkeys of others to eliminate redundancy.
        for key in sorted(self.__attr_map):
            for idx in range(1, len(key)):
                sub_key = key[:-idx]
                if sub_key in all_keys:
                    all_keys.remove(sub_key)
        if provides_member_resource(self._context):
            # If the context is a member, we need to configure the loaders
            # for the entity class belonging to each of its resource
            # attributes. Only nested keys collected from the representer
            # configuration need to be configured (and the corresponding
            # nested entity attribute needs to be shortened).
            loader_option_map = defaultdict(list)
            for key in all_keys:
                entity_attr_names = self.__attr_map[key]
                if len(entity_attr_names) > 1:
                    ent_attr_name = entity_attr_names[0]
                    nested_attr_name = '.'.join(entity_attr_names[1:])
                    opts = loader_option_map[ent_attr_name]
                    opts.append(nested_attr_name)
            # Translate to entity classes as keys. This is tricky as the
            # keys in the loader option map can itself be nested attributes.
            for ent_attr_name, nested_attr_names in loader_option_map.items():
                ent_attr_name_tokens = ent_attr_name.split('.')
                ent_cls = get_entity_class(self._context)
                ent_cls_attr = getattr(ent_cls, ent_attr_name_tokens[0])
                ent_cls = ent_cls_attr.property.mapper.entity
                if len(ent_attr_name_tokens) > 1:
                    prefix = '.'.join(ent_attr_name_tokens[1:])
                    loader_option_map[ent_cls] = \
                            ["%s.%s" % (prefix, token)
                             for token in nested_attr_names]
                else:
                    loader_option_map[ent_cls] = nested_attr_names
                del loader_option_map[ent_attr_name]
        else:
            # If the context is a collection, we need to configure the
            # loader for its entity class.
            loader_option_map = {get_entity_class(self._context) :
                                 ['.'.join(self.__attr_map[key])
                                  for key in all_keys]}
        return loader_option_map


class QueryFactory(object):
    """
    Query factory for the RDB session.

    The main task of the query factory is to process entity loader options
    for configured entity classes.
    """
    def __init__(self, session):
        self.__session = session
        self.loader_option_map = {}

    def __call__(self, entity_class, options):
        """
        Creates a query for the given entity class, passing the given
        option map to the constructor, and processes loader options, if
        configured.
        """
        # The "query_class" option is used to inject the optimized
        # counting query class which fetches the total result count and
        # the first result page in one call.
        query_cls = options.pop('query_class', Query)
        q = query_cls([entity_class], self.__session, **options)
        entity_attr_names = self.loader_option_map.get(entity_class)
        if not entity_attr_names is None:
            q = self.__process_loader_options(entity_attr_names,
                                              class_mapper(entity_class),
                                              q)
        return q

    def __process_loader_options(self, entity_attr_names, mapper, query):
        if len(entity_attr_names) > 0:
            prop = None
            for entity_attr_name in sorted(entity_attr_names):
                opt = None
                ent = mapper.entity
                for entity_attr_name_token in entity_attr_name.split('.'):
                    try:
                        ent_attr = getattr(ent, entity_attr_name_token)
                    except AttributeError, exc:
                        # Try finding the attribute in the polymorphic map of
                        # the parent attribute mapper.
                        ent_attr = None
                        if not prop is None:
                            for cls in itervalues_(
                                                prop.mapper.polymorphic_map):
                                ent_attr = getattr(cls,
                                                   entity_attr_name_token,
                                                   None)
                                if not ent_attr is None:
                                    break
                        if ent_attr is None:
                            raise exc
                    try:
                        prop = ent_attr.property
                    except AttributeError:
                        # The class attribute was not an instrumented
                        # attribute - skip optimization.
                        break
                    ent = prop.mapper.entity
                    if opt is None:
                        opt = joinedload(entity_attr_name_token)
                    else:
                        opt = opt.joinedload(entity_attr_name_token)
                if not opt is None:
                    query = query.options(opt)
        return query


class RdbSession(SaSession, Session):
    """
    Special session class adapting the SQLAlchemy session for everest.
    """
    IS_MANAGING_BACKREFERENCES = False

    def __init__(self, *args, **options):
        self.__repository = options.pop('repository')
        SaSession.__init__(self, *args, **options)
        self.__query_factory = QueryFactory(self)

    def configure_loaders(self, context, representer_configuration):
        trv = RepresenterConfigTraverser(representer_configuration)
        vst = RdbRepresenterConfigVisitor(context)
        trv.run(vst)
        self.__query_factory.loader_option_map.update(vst.loader_options)

    def reset_loaders(self):
        self.__query_factory.loader_option_map.clear()

    def get_by_id(self, entity_class, id_key):
        return self.query(entity_class).get(id_key)

    def get_by_slug(self, entity_class, slug):
        # We don't have an optimization for access by slug here; returning
        # `None` indicates that a query should be run.
        return None

    def add(self, entity_class, data): # different signature pylint: disable=W0222
        if not IEntity.providedBy(data): # pylint: disable=E1101
            self.__run_traversal(entity_class, data, None,
                                 RELATION_OPERATIONS.ADD)
        else:
            SaSession.add(self, data)

    def remove(self, entity_class, data):
        if not IEntity.providedBy(data): # pylint: disable=E1101
            self.__run_traversal(entity_class, None, data,
                                 RELATION_OPERATIONS.REMOVE)
        else:
            SaSession.delete(self, data)

    def update(self, entity_class, data, target=None):
        if not IEntity.providedBy(data): # pylint: disable=E1101
            upd_ent = self.__run_traversal(entity_class, data, target,
                                           RELATION_OPERATIONS.UPDATE)
        else:
            upd_ent = SaSession.merge(self, data)
        return upd_ent

    def query(self, *entities, **options):
        if len(entities) == 1:
            ent_obj = entities[0]
            if isinstance(ent_obj, type) and issubclass(ent_obj, Entity):
                ent_cls = ent_obj
            else:
                # Assume that a mapper was passed by SQLAlchemy.
                ent_cls = ent_obj.entity
            q = self.__query_factory(ent_cls, options)
        else:
            q = Query(entities, self, **options)
        return q

    def reset(self):
        self.rollback()
        self.expunge_all()

    def __run_traversal(self, entity_class, source_data, target_data, rel_op):
        agg = self.__repository.get_aggregate(entity_class)
        trv = SourceTargetDataTreeTraverser.make_traverser(
                                    source_data, target_data, rel_op,
                                    accessor=agg,
                                    manage_back_references=False)
        vst = AruVisitor(entity_class,
                         add_callback=self.__add,
                         remove_callback=self.__remove,
                         update_callback=self.__update,
                         pass_path_to_callbacks=True)
        trv.run(vst)
        return vst.root

    def __add(self, entity, path): # pylint: disable=W0613
        if len(path) == 0:
            SaSession.add(self, entity)

    def __remove(self, entity, path): # pylint: disable=W0613
        if len(path) == 0:
            SaSession.delete(self, entity)

    def __update(self, source_data, target_entity, path): # pylint: disable=W0613
        EntityState.set_state_data(target_entity, source_data)


class RdbAutocommittingSession(AutocommittingSessionMixin, RdbSession):
    def __init__(self, **kw):
        kw['autocommit'] = True
        super(RdbAutocommittingSession, self).__init__(**kw)


#: The scoped session maker. Instantiate this to obtain a thread local
#: session instance.
ScopedSessionMaker = scoped_session(sessionmaker(class_=RdbSession))


class RdbSessionFactory(SessionFactory):
    """
    Factory for RDB repository sessions.
    """
    def __init__(self, repository, counting_query_class):
        SessionFactory.__init__(self, repository)
        if self._repository.autocommit:
            # Use an autocommitting Session class with our session factory.
            self.__fac = scoped_session(
                                sessionmaker(class_=RdbAutocommittingSession))
        else:
            # Use the default Session factory.
            self.__fac = ScopedSessionMaker
        #: This is the (optimized, if the engine supports it) counting query
        #: class used for paged queries.
        self.counting_query_class = counting_query_class

    def configure(self, **kw):
        self.__fac.configure(**kw)

    def reset(self):
        if self.__fac.registry.has():
            self.__fac().reset()

    def __call__(self, **kw):
        if not self.__fac.registry.has():
            self.__fac.configure(
                            autoflush=self._repository.autoflush,
                            repository=self._repository)
            if not self._repository.autocommit \
               and self._repository.join_transaction:
                # Enable the Zope transaction extension.
                self.__fac.configure(extension=ZopeTransactionExtension())
            else:
                # Disable extension otherwise.
                self.__fac.configure(extension=None)
        return self.__fac(**kw)
