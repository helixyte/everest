"""
No SQL repository utilities.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 12, 2013.
"""
from bson.dbref import DBRef
from bson.son import SON
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.entities.attributes import \
                    get_domain_class_relationship_attribute_iterator
from everest.entities.attributes import get_domain_class_attribute_iterator
from everest.entities.attributes import get_domain_class_attributes
from everest.entities.utils import get_entity_class
from everest.resources.utils import get_root_collection

__docformat__ = 'reStructuredText en'
__all__ = ['MongoClassRegistry',
           'MongoInstrumentedAttribute',
           'NoSqlAttributeInspector',
           'transform_incoming',
           'transform_outgoing',
           ]


class MongoClassRegistry(object):
    """
    Registry for classes that were instrumented to work with Mongo DB.
    """
    __registered_classes = set()

    @staticmethod
    def register(entity_class, mongo_db):
        """
        Registers the given entity class. DB refs will be resolved through
        the given Mongo DB client.
        """
        if entity_class in MongoClassRegistry.__registered_classes:
            raise ValueError('The class "%s" has already been registered.'
                             % entity_class)
        for attr in \
              get_domain_class_relationship_attribute_iterator(entity_class):
            # We want to return the original value in the class namespace in
            # case there is one.
            try:
                cls_val = object.__getattribute__(entity_class,
                                                  attr.entity_attr)
            except AttributeError:
                args = ()
            else:
                args = (cls_val,)
            mongo_attr = MongoInstrumentedAttribute(
                                        attr,
                                        mongo_db,
                                        *args)
            setattr(entity_class, attr.entity_attr, mongo_attr)
        MongoClassRegistry.__registered_classes.add(entity_class)

    @staticmethod
    def unregister(entity_class):
        """
        Unregisters the given entity class.

        This involves removing all custom attribute descriptors from the
        entity class namespace.
        """
        if not entity_class in MongoClassRegistry.__registered_classes:
            raise ValueError('The class "%s" is not registered.'
                             % entity_class)
        # We can not rely on the resource attribute iterators to work here -
        # the registry might already have been taken down at this point.
        for attr_name, attr_value in entity_class.__dict__.items():
            if isinstance(attr_value, MongoInstrumentedAttribute):
                try:
                    orig_cls_val = attr_value.original_class_value
                except AttributeError:
                    delattr(entity_class, attr_name)
                else:
                    setattr(entity_class, attr_name, orig_cls_val)
        MongoClassRegistry.__registered_classes.remove(entity_class)

    @staticmethod
    def unregister_all():
        """
        Unregisters all registered classes.

        This is useful e.g. in a unit test scenario where lingering
        instrumentation from a previous test can cause trouble in subsequent
        tests.
        """
        for ent_cls in MongoClassRegistry.__registered_classes.copy():
            MongoClassRegistry.unregister(ent_cls)

    @staticmethod
    def is_registered(entity_class):
        """
        Checks if the given entity class has already been registered with
        this registry.
        """
        return entity_class in MongoClassRegistry.__registered_classes


def transform_incoming(ent_cls, ent):
    """
    Converts an incoming entity into a SON object. In particular,
    this involves translating entity references to DB Refs.
    """
    son = SON()
    son['_id'] = getattr(ent, '_id')
    # We store the slug for querying purposes.
    son['slug'] = ent.slug
    for attr in get_domain_class_attribute_iterator(ent_cls):
        try:
            value = getattr(ent, attr.entity_attr)
        except AttributeError:
            continue
        if attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
            son[attr.entity_attr] = value
        else:
            if value is None:
                son[attr.entity_attr] = None
            else:
                root_coll = get_root_collection(attr.attr_type)
                if attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
                    son[attr.entity_attr] = DBRef(root_coll.__name__,
                                                  getattr(value, '_id'))
                else:
                    son[attr.entity_attr] = [DBRef(root_coll.__name__,
                                                   getattr(el, '_id'))
                                             for el in value]
    return son


def transform_outgoing(entity_class, son):
    """
    Converts an outgoing SON object into an entity. DBRefs are
    converted lazily.
    """
    ref_map = {}
    ent = object.__new__(entity_class)
    for attr in get_domain_class_attribute_iterator(entity_class):
        try:
            value = son[attr.entity_attr]
        except KeyError:
            continue
        if attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL or value is None:
            setattr(ent, attr.entity_attr, value)
        else:
            ref_map[attr.entity_attr] = value
    ent.__mongo_refs__ = ref_map
    # Set the _id attribute.
    setattr(ent, '_id', son['_id'])
    return ent


class MongoInstrumentedAttribute(object):
    """
    Lazy resolution of relation attributes through Mongo DB refs.
    """
    def __init__(self, attr, db, *args):
        self.__attr = attr
        self.__db = db
        if args:
            self.original_class_value, = args

    def __get__(self, entity, entity_class):
        if not entity is None:
            ref_val = entity.__mongo_refs__[self.__attr.entity_attr]
            attr_entity_class = get_entity_class(self.__attr.attr_type)
            if isinstance(ref_val, list):
                # FIXME: Assuming list here.
                value = [transform_outgoing(attr_entity_class,
                                            self.__db.dereference(el))
                         for el in ref_val]
            else:
                value = transform_outgoing(attr_entity_class,
                                           self.__db.dereference(ref_val))
            setattr(entity, self.__attr.entity_attr, value)
        else:
            value = self
        return value


class NoSqlAttributeInspector(object):
    """
    Analyzes attributes of entity classes to assiste building query
    expressions for the No SQL backend.
    """
    @staticmethod
    def inspect(entity_class, attribute_name):
        attr_tokens = attribute_name.split('.')
        infos = []
        for idx, attr_token in enumerate(attr_tokens):
            do_append = True
            try:
                attr = get_domain_class_attributes(entity_class)[attr_token]
            except KeyError:
                if attr_token != 'slug':
                    # If we encounter a non-resource attribute, we assume
                    # an embedded document (which implies that the last
                    # token was a terminal).
                    infos[-1][-1] = \
                        '.'.join([infos[-1][-1]] + attr_tokens[idx:])
                    # Unfortunately, we can not infer the type of embedded
                    # attributes.
                    infos[-1][1] = None
                    do_append = False
                else:
                    # The 'slug' attribute is special as it is not a properly
                    # declared resource attribute but needs to be queryable.
                    attr_kind = RESOURCE_ATTRIBUTE_KINDS.TERMINAL
                    attr_type = str
            else:
                attr_kind = attr.kind
                if attr_kind != RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                    entity_class = get_entity_class(attr.attr_type)
                    attr_type = entity_class
                else:
                    attr_type = attr.attr_type
            if do_append:
                infos.append([attr_kind, attr_type, attr_token])
        return infos
