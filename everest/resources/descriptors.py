"""
Attribute descriptors for resource classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 19, 2011.
"""
from everest.constants import CARDINALITIES
from everest.constants import DEFAULT_CASCADE
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.entities.interfaces import IEntity
from everest.entities.relationship import DomainRelationship
from everest.relationship import RELATIONSHIP_DIRECTIONS
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IResource
from everest.resources.interfaces import IResourceAttribute
from everest.resources.relationship import ResourceRelationship
from everest.resources.utils import get_member_class
from everest.utils import get_nested_attribute
from everest.utils import id_generator
from everest.utils import set_nested_attribute
from zope.interface import implementer # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface.interfaces import IInterface # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['attribute_alias',
           'attribute_base',
           'collection_attribute',
           'member_attribute',
           'terminal_attribute',
           ]


@implementer(IResourceAttribute)
class attribute_base(object):
    """
    Abstract base class for all attribute descriptors.

    :cvar kind: the resource attribute kind
    :ivar attr_type: the type (or interface) of the controlled entity
      attribute.
    :ivar entity_attr: the entity attribute the descriptor references. May
      be *None*.
    :ivar int index: unique sequential numeric ID for this attribute. Since
      this index is incremented each time a new resource attribute is
      declared, it can be used to establish a well-defined sorting order on
      all attribute declarations of a resource.
    :ivar resource_attr: the resource attribute this descriptor is mapped to.
      This is set after instantiation.
    """
    __index_gen = id_generator()

    #: The resource attribute kind. Set in derived classes.
    kind = None

    def __init__(self, attr_type, entity_attr):
        self.attr_type = attr_type
        self.entity_attr = entity_attr
        self.index = next(self.__index_gen)
        self.resource_attr = None

    def __get__(self, resource, resource_class):
        raise NotImplementedError('Abstract method')

    def __set__(self, resource, value):
        raise NotImplementedError('Abstract method')

    def __str__(self):
        return "%s: rc attr %s, type %s" \
               % (self.__class__.__name__, self.resource_attr, self.attr_type)


class terminal_attribute(attribute_base):
    """
    Descriptor for declaring terminal attributes of a resource as attributes
    from its underlying entity.

    A terminal attribute is an attribute that the framework will not look
    into any further for querying or serialization.
    """
    kind = RESOURCE_ATTRIBUTE_KINDS.TERMINAL

    def __init__(self, attr_type, entity_attr):
        if not isinstance(attr_type, type):
            raise ValueError('The attribute type of a terminal attribute '
                             'must be a class.')
        attribute_base.__init__(self, attr_type, entity_attr)

    def __get__(self, resource, resource_class):
        if resource is None:
            # Class level access.
            obj = self
        else:
            obj = get_nested_attribute(resource.get_entity(), self.entity_attr)
        return obj

    def __set__(self, resource, value):
        set_nested_attribute(resource.get_entity(), self.entity_attr, value)


class _relation_attribute(attribute_base):
    """
    Base class for relation resource descriptors (i.e., descriptors managing
    a related member or collection resource).

    :ivar cardinality: indicates the cardinality of the relationship for
      non-terminal attributes. This is always `None` for terminal attributes.
    :ivar cascade: sets the cascading rules for this relation attribute.
    :ivar resource_backref: attribute of the related resource (relatee) which
      back-references the current resource (relator).
    """
    def __init__(self, attr_type, entity_attr=None, cardinality=None,
                 cascade=DEFAULT_CASCADE, backref=None):
        if not (isinstance(attr_type, type)
                or IInterface in provided_by(attr_type)):
            raise ValueError('The attribute type of a member or collection '
                             ' attribute must be a class or an interface.')
        if entity_attr is None and backref is None:
            raise ValueError('Either the entity_attr or the backref parameter '
                             'to a relation resource attribute may be None, '
                             'but not both.')
        attribute_base.__init__(self, attr_type, entity_attr)
        self.cardinality = cardinality
        self.cascade = cascade
        self.resource_backref = backref
        self.__entity_backref = None

    def __get__(self, resource, resource_class):
        raise NotImplementedError('Abstract method')

    def __set__(self, resource, value):
        raise NotImplementedError('Abstract method')

    def make_relationship(self, relator,
                          direction=
                            RELATIONSHIP_DIRECTIONS.BIDIRECTIONAL):
        """
        Create a relationship object for this attribute from the given
        relator and relationship direction.
        """
        if IEntity.providedBy(relator): # pylint:disable=E1101
            rel = DomainRelationship(relator, self,
                                     direction=direction)
        elif IResource.providedBy(relator): # pylint:disable=E1101
            rel = ResourceRelationship(relator, self,
                                       direction=direction)
        else:
            raise ValueError('Invalid relator argument "%s" for '
                             'relationship; must provide IEntity or '
                             'IResource.' % relator)
        return rel

    @property
    def entity_backref(self):
        if self.__entity_backref is None:
            if self.resource_backref is None:
                self.__entity_backref = None
            else:
                attr_mb_class = get_member_class(self.attr_type)
                backref_rc_descr = getattr(attr_mb_class,
                                           self.resource_backref, None)
#                # We require the backref to be a resource attribute of the
#                # target.
#                if backref_rc_descr is None:
#                    raise ValueError('The "backref" attribute must be a '
#                                     'resource attribute declared on the '
#                                     'target of the descriptor.')
                if not backref_rc_descr is None:
                    self.__entity_backref = backref_rc_descr.entity_attr
                else:
                    self.__entity_backref = self.resource_backref
        return self.__entity_backref


class member_attribute(_relation_attribute):
    """
    Descriptor for declaring member attributes of a resource as attributes
    of its underlying entity.
    """
    kind = RESOURCE_ATTRIBUTE_KINDS.MEMBER

    def __init__(self, attr_type, entity_attr=None,
                 cardinality=CARDINALITIES.MANYTOONE,
                 cascade=DEFAULT_CASCADE, backref=None):
        _relation_attribute.__init__(self, attr_type,
                                     entity_attr=entity_attr,
                                     cardinality=cardinality,
                                     cascade=cascade,
                                     backref=backref)

    def __get__(self, resource, resource_class):
        if not resource is None:
            ent = get_nested_attribute(resource.get_entity(),
                                       self.entity_attr)
            if not ent is None:
                fac = get_member_class(self.attr_type).as_related_member
                member = fac(ent, self.make_relationship(resource))
            else:
                member = None
        else:
            # class level access
            member = self
        return member

    def __set__(self, resource, value):
        if not value is None:
            ent = value.get_entity()
        else:
            ent = None
        set_nested_attribute(resource.get_entity(), self.entity_attr, ent)


class collection_attribute(_relation_attribute):
    """
    Descriptor for declaring collection attributes of a resource as attributes
    from its underlying entity.
    """
    kind = RESOURCE_ATTRIBUTE_KINDS.COLLECTION

    def __init__(self, attr_type, entity_attr=None,
                 cardinality=CARDINALITIES.ONETOMANY,
                 cascade=DEFAULT_CASCADE, backref=None):
        _relation_attribute.__init__(self, attr_type,
                                     entity_attr=entity_attr,
                                     cardinality=cardinality,
                                     cascade=cascade,
                                     backref=backref)

    def __get__(self, member, member_class):
        if not member is None:
            # Create a collection. We can not just return the
            # entity attribute here as that would load the whole entity
            # collection; so we construct a related collection instead.
            parent_coll = member.__parent__
            while not getattr(parent_coll, '__parent__', None) is None \
                  and not ICollectionResource in provided_by(parent_coll):
                parent_coll = parent_coll.__parent__ # pragma: no cover FIXME: test case!
            root_coll = parent_coll.get_root_collection(self.attr_type)
            coll = root_coll.as_related_collection(
                                        root_coll.get_aggregate(),
                                        self.make_relationship(member))
        else:
            # Class level access.
            coll = self
        return coll

    # FIXME: Not sure if we want to support replacement of child containers.
    def __set__(self, member, value):
        raise NotImplementedError('Not implemented.')


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
