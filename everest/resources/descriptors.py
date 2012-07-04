"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Descriptors for resource classes.

Created on Apr 19, 2011.
"""
from everest.entities.utils import slug_from_identifier
from everest.relationship import Relationship
from everest.resources.repository import ResourceRepository
from everest.resources.utils import as_member
from everest.resources.utils import get_member_class
from everest.resources.utils import get_root_collection
from everest.resources.utils import new_stage_collection
from everest.utils import id_generator
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['attribute_alias',
           'attribute_base',
           'collection_attribute',
           'member_attribute',
           'terminal_attribute',
           ]


class CARDINALITY(object):
    """
    Cardinality constants for non-terminal resource attributes.
    """
    ONETOMANY = 'ONETOMANY'
    MANYTOONE = 'MANYTOONE'
    MANYTOMANY = 'MANYTOMANY'


class attribute_base(object):
    """
    Abstract base class for all attribute descriptors.

    :ivar attr_type: the type (or interface) of the controlled entity 
      attribute.
    :ivar entity_attr: the entity attribute the descriptor references. May
      be *None*.
    :ivar cardinality: indicates the cardinality of the relationship for 
      non-terminal attributes. This is always `None` for terminal attributes. 
    :ivar int id: unique sequential numeric ID for this attribute. Since this
      ID is incremented each time a new resource attribute is declared,
      it can be used to establish a well-defined sorting order on all
      attribute declarations of a resource.
    :ivar resource_attr: the resource attribute this descriptor is mapped to.
      This is set after instantiation. 
    """

    __id_gen = id_generator()

    def __init__(self, attr_type, entity_attr, cardinality):
        self.attr_type = attr_type
        self.entity_attr = entity_attr
        self.cardinality = cardinality
        self.id = self.__id_gen.next()
        self.resource_attr = None

    def __get__(self, resource, resource_class):
        raise NotImplementedError('Abstract method')

    def __set__(self, resource, value):
        raise NotImplementedError('Abstract method')

    def _set_nested(self, entity, entity_attr, value):
        parent, entity_attr = self.__resolve_nested(entity, entity_attr)
        if parent is None:
            raise AttributeError('Can not set attribute "%s" on None value.'
                                 % entity_attr)
        setattr(parent, entity_attr, value)

    def _get_nested(self, entity, entity_attr):
        parent, entity_attr = self.__resolve_nested(entity, entity_attr)
        if not parent is None:
            attr_value = getattr(parent, entity_attr)
        else:
            attr_value = None
        return attr_value

    def __resolve_nested(self, entity, entity_attr):
        tokens = entity_attr.split('.')
        for token in tokens[:-1]:
            entity = getattr(entity, token)
            if entity is None:
                break
        return (entity, tokens[-1])


class terminal_attribute(attribute_base):
    """
    Descriptor for declaring terminal attributes of a resource as attributes
    from its underlying entity.

    A terminal attribute is an attribute that the framework will not look
    into any further for querying or serialization.
    """

    def __init__(self, attr_type, entity_attr):
        if not isinstance(attr_type, type):
            raise ValueError('The attribute type of a terminal attribute '
                             'must be a class.')
        attribute_base.__init__(self, attr_type, entity_attr, None)

    def __get__(self, resource, resource_class):
        if resource is None:
            # Class level access.
            obj = self
        else:
            obj = self._get_nested(resource.get_entity(), self.entity_attr)
        return obj

    def __set__(self, resource, value):
        self._set_nested(resource.get_entity(), self.entity_attr, value)


class _relation_attribute(attribute_base):
    """
    Base class for relation resource descriptors (i.e., descriptors managing
    a related member or collection resource).
    """
    def __init__(self, attr_type, entity_attr=None,
                 cardinality=None, is_nested=False):
        """
        :param bool is_nested: indicates if the URLs generated for this
            relation descriptor should be relative to the parent ("nested")
            or absolute.
        """
        if not (isinstance(attr_type, type)
                or IInterface in provided_by(attr_type)):
            raise ValueError('The attribute type of a member or collection '
                             ' attribute must be a class or an interface.')
        attribute_base.__init__(self, attr_type, entity_attr, cardinality)
        self.is_nested = is_nested

    def __get__(self, resource, resource_class):
        raise NotImplementedError('Abstract method')

    def __set__(self, resource, value):
        raise NotImplementedError('Abstract method')


class member_attribute(_relation_attribute):
    """
    Descriptor for declaring member attributes of a resource as attributes
    from its underlying entity.
    """
    def __init__(self, attr_type, entity_attr=None,
                 cardinality=CARDINALITY.MANYTOONE, is_nested=False):
        _relation_attribute.__init__(self, attr_type,
                                     entity_attr=entity_attr,
                                     cardinality=cardinality,
                                     is_nested=is_nested)

    def __get__(self, resource, resource_class):
        if not resource is None:
            obj = self._get_nested(resource.get_entity(), self.entity_attr)
            if not obj is None:
                if not self.is_nested:
                    member = as_member(obj)
                    coll = get_root_collection(member)
                    member.__parent__ = coll
                else:
                    member = as_member(obj, parent=resource)
                    member.__name__ = slug_from_identifier(self.resource_attr)
            else:
                member = obj
        else:
            # class level access
            member = self
        return member

    def __set__(self, resource, value):
        if not value is None:
            ent = value.get_entity()
        else:
            ent = None
        self._set_nested(resource.get_entity(), self.entity_attr, ent)


class collection_attribute(_relation_attribute):
    """
    Descriptor for declaring collection attributes of a resource as attributes
    from its underlying entity.
    """
    def __init__(self, attr_type, entity_attr=None,
                 cardinality=CARDINALITY.ONETOMANY,
                 is_nested=True, backref=None):
        """
        :param str backref: attribute of the members of the target
          collection which back-references the current resource (parent).
        """
        if entity_attr is None and backref is None:
            raise ValueError('Either the entity_attr or the backref parameter '
                             'to a collection attribute may be None, but '
                             'not both.')
        _relation_attribute.__init__(self, attr_type,
                                     entity_attr=entity_attr,
                                     cardinality=cardinality,
                                     is_nested=is_nested)
        self.backref = backref
        self.__resource_backref = None
        self.__entity_backref = None
        self.__need_backref_setup = not backref is None

    def __get__(self, resource, resource_class):
        if self.__need_backref_setup:
            self.__setup_backref()
        if not resource is None:
            # Create a collection. We can not just return the
            # entity attribute here as that would load the whole entity
            # collection.
            parent = resource.get_entity()
            if not self.entity_attr is None:
                children = self._get_nested(parent, self.entity_attr)
            else:
                children = None
            coll = self.__make_collection(resource, parent, children)
        else:
            # Class level access.
            coll = self
        return coll

# FIXME: Not sure if we want to support replacement of child containers.
#    def __set__(self, resource, value):
#        ent_coll = self._get_nested(resource.get_entity(), self.entity_attr)
#        ent_coll_cls = type(ent_coll)
#        new_ent_coll = ent_coll_cls([mb.get_entity() for mb in value])
#        self._set_nested(resource.get_entity(), self.entity_attr, new_ent_coll)

    def __set__(self, resource, value):
        raise NotImplementedError('Abstract method')

    def __setup_backref(self):
        if not self.backref is None:
            # We require the backref to be a resource attribute of the target.
            attr_mb_class = get_member_class(self.attr_type)
            backref_rc_descr = getattr(attr_mb_class, self.backref, None)
#            if backref_rc_descr is None:
#                raise ValueError('The "backref" attribute must be a '
#                                 'resource attribute declared on the '
#                                 'target of the descriptor.')
            if not backref_rc_descr is None:
                self.__resource_backref = self.backref
                self.__entity_backref = backref_rc_descr.entity_attr
            else:
                # FIXME: Falling back on the entity attribute here is fishy.
                self.__entity_backref = self.backref # pragma: no cover
        self.__need_backref_setup = False

    def __make_collection(self, resource, parent, children):
        # Create a new collection.
        if not resource.__parent__ is None:
            # Find the resource repository used for this resource's parent
            # and use it to create a new collection.
            rc_repo = ResourceRepository.get_repository(resource.__parent__)
            coll = rc_repo.get(self.attr_type)
        else:
            # This is a floating member, assume stage repository.
            coll = new_stage_collection(self.attr_type)
        # Set up entity access in the new collection.
        agg_relationship = Relationship(parent, children,
                                        backref=self.__entity_backref)
        agg = coll.get_aggregate()
        agg.set_relationship(agg_relationship)
        # Set up URL generation.
        if self.is_nested:
            # Make URL generation relative to the resource.
            coll.__parent__ = resource
            # Set the collection's name to the descriptor's resource
            # attribute name.
            coll.__name__ = slug_from_identifier(self.resource_attr)
        else:
            # Add a filter specification for the root collection through
            # a relationship.
            coll_relationship = Relationship(resource, coll,
                                             backref=self.__resource_backref)
            coll.set_relationship(coll_relationship)
        return coll


class attribute_alias(object):
    """
    Descriptor for declaring an alias to another attribute declared by an
    attribute descriptor.
    """
    def __init__(self, alias_attr):
        self.alias_attr = alias_attr

    def __get__(self, resource, resource_class):
        if resource is None:
            # Class level access.
            obj = self
        else:
            descr = getattr(resource_class, self.alias_attr)
            obj = descr.__get__(resource, resource_class)
        return obj

    def __set__(self, resource, value):
        descr = getattr(type(resource), self.alias_attr)
        descr.__set__(resource, value)
