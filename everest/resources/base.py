"""
Resource base classes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 3, 2011.
"""
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.entities.utils import get_entity_class
from everest.entities.utils import identifier_from_slug
from everest.entities.utils import slug_from_identifier
from everest.querying.base import SpecificationExpressionHolder
from everest.querying.interfaces import ISpecificationVisitor
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.utils import get_filter_specification_factory
from everest.resources.attributes import ResourceAttributeControllerMixin
from everest.resources.attributes import get_resource_class_attribute
from everest.resources.descriptors import terminal_attribute
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResource
from everest.resources.link import Link
from everest.resources.utils import as_member
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.traversal import model_path
from zope.interface import implementer # pylint: disable=E0611,F0401
import uuid

__docformat__ = "reStructuredText en"
__all__ = ['Collection',
           'Member',
           'Resource',
           'ResourceToEntityFilterSpecificationVisitor',
           'ResourceToEntityOrderSpecificationVisitor',
           'ResourceToEntitySpecificationVisitor',
           ]


@implementer(IResource)
class Resource(object):
    """
    Abstract base class for all resources.
    """

    #: Authentication specifier. Override as needed.
    __acl__ = [
        (Allow, Authenticated, 'view'),
        (Allow, Authenticated, 'create'),
        (Allow, Authenticated, 'update'),
        (Allow, Authenticated, 'delete'),
        ]
    #: The parent of this resource. This is `None` for the service resource.
    __parent__ = None
    #: The name of the resource. This has to be unique within the parent.
    __name__ = None
    #: The relation identifier to show in links to this resource. Needs to
    #: be specified in derived classes.
    relation = None
    #: Descriptive title for this resource.
    title = ''
    #: Detailed description of this resource.
    description = ''

    def __init__(self, relationship=None):
        """
        Constructor:
        """
        if self.__class__ is Resource:
            raise NotImplementedError('Abstract class')
        if self.__class__.relation is None:
            raise ValueError('Resource classes must have a relation '
                             'attribute.')
        #: A relationship to some other resource. Makes this resource a
        #: "nested" resource.
        self._relationship = relationship
        self.is_nested = not relationship is None
        #: A set of links to other resources.
        self.links = set()

    def add_link(self, link):
        """
        Adds a link to another resource.

        :param link: Resource link.
        :type link: :class:`everest.resources.base.Link`
        """
        self.links.add(link)

    @property
    def path(self):
        """
        Returns the path to this resource in the tree of resources.
        """
        return model_path(self)

    @property
    def urn(self):
        """
        Returns the URN for this resource (globally unique identifier).
        """
        return uuid.uuid5(uuid.NAMESPACE_URL, self.path).urn

    @property
    def has_parent(self):
        """
        Checks if this resource has a parent.
        """
        return not self.__parent__ is None


@implementer(IMemberResource)
class Member(ResourceAttributeControllerMixin, Resource):
    """
    Base class for all member resources.
    """

    id = terminal_attribute(int, 'id')

    def __init__(self, entity, name=None, relationship=None):
        """
        Constructor:

        :param str name: Unique name of the member within the collection
        :param entity: Associated entity (domain object).
        :type entity: Object implementing an interface derived from
                :class:`everest.entities.interfaces.IEntity`.
        """
        if self.__class__ is Member:
            raise NotImplementedError('Abstract class')
        if not isinstance(entity, get_entity_class(self)):
            raise ValueError(
                    'Invalid entity class "%s" for %s resource class.'
                    % (entity.__class__.__name__, self.__class__.__name__))
        super(Member, self).__init__(relationship=relationship)
        self.__entity = entity
        self.__name = name
        # Add the rel="self" link.
        self.add_link(Link(self, "self"))

    def _get__name__(self):
        # The name of a member resource defaults to the slug of the underlying
        # entity.
        return self.__name or self.__entity.slug

    def _set__name__(self, name):
        self.__name = name

    __name__ = property(_get__name__, _set__name__)

    @classmethod
    def create_from_entity(cls, entity):
        """
        Class factory method creating a new resource from the given entity.
        """
        return cls(entity)

    def get_entity(self):
        """
        Returns the entity this resource manages.

        :return: Object implementing
            :class:`everest.entities.interfaces.IEntity`.
        """
        return self.__entity

    def update(self, data):
        """
        Updates this member from the given data.

        See :method:`Collection.update`.
        """
        self.__parent__.update(data, target=self)

    def __getitem__(self, item):
        ident = identifier_from_slug(item)
        attr = get_resource_class_attribute(self.__class__, ident)
        if attr is None:
            raise KeyError('%s' % ident)
        return getattr(self, ident)

    def __hash__(self):
        """
        Hash value, based on the resource class and the name.
        """
        return hash((self.__class__, self.__name__))

    def __eq__(self, other):
        """
        Equality operator. Two members compare equal if they belong to the
        same class and have the same name.
        """
        return (isinstance(other, self.__class__) and
                self.__name__ == other.__name__)

    def __ne__(self, other):
        """
        Inequality operator.
        """
        return not (self == other)

    def __str__(self):
        return "%s(id: %s, name: %s)" \
               % (self.__class__.__name__, self.id, self.__name__)

    @property
    def is_root_member(self):
        # The parent might be a member, so we use getattr with a default.
        return not self.__parent__ is None \
               and getattr(self.__parent__, 'is_root_collection', False)

    @classmethod
    def as_related_member(cls, entity, relationship):
        """
        Creates a new relationship member with the relationship's relator
        as a parent.
        """
        rel_mb = cls.create_from_entity(entity)
        rel_mb._relationship = relationship # pylint: disable=W0212
        rel_mb.__parent__ = relationship.relator
        return rel_mb


@implementer(ICollectionResource)
class Collection(Resource):
    """
    This is an abstract base class for all resource collections.
    A collection is a set of member resources which can be filtered, sorted,
    and sliced.
    """
    #: The title of the collection.
    title = None
    #: The name for the root collection (used as URL path to the root
    #: collection inside the service).
    root_name = None
    #: A description of the collection.
    description = ''
    #: The default order of the collection's members.
    default_order = AscendingOrderSpecification('id')
    #: The page size default for this collection.
    default_limit = 100
    #: The default maximum page size limit for this collection. Unless
    #: this is set in derived classes, no limit is enforced (i.e., the
    #: default maximum limit is None).
    max_limit = None

    def __init__(self, aggregate, name=None, relationship=None):
        """
        Constructor.

        :param str name: Name of the collection.
        :param aggregate: Associated aggregate.
        :type aggregate: :class:`everest.entities.aggregates.Aggregate` -
                an object implementing an interface derived from
                :class:`everest.entities.interfaces.IAggregate`.
        """
        if self.__class__ is Collection:
            raise NotImplementedError('Abstract class')
        Resource.__init__(self, relationship=relationship)
        if self.title is None:
            raise ValueError('Collection must have a title.')
        if name is None:
            name = self.root_name
        self.__name__ = name
        #: The filter specification for this resource. Attribute names in
        #: this specification are relative to the resource.
        self._filter_spec = None
        #: The order specification for this resource. Attribute names in
        #: this specification are relative to the resource.
        self._order_spec = None
        # The underlying aggregate.
        self.__aggregate = aggregate

    @classmethod
    def create_from_aggregate(cls, aggregate, relationship=None):
        """
        Creates a new collection from the given aggregate.

        :param aggregate: Aggregate containing the entities exposed by this
            collection resource.
        :param relationship: Resource relationship. If given, the root
            aggregate is converted to a relationship aggregate and the
            relationship is passed on to the collection class constructor.
        :type aggregate: :class:`everest.entities.aggregates.RootAggregate`
        """
        if not relationship is None:
            aggregate = aggregate.make_relationship_aggregate(
                                            relationship.domain_relationship)
        return cls(aggregate, relationship=relationship)

    def get_aggregate(self):
        """
        Returns the aggregate underlying this collection.

        :returns: Object implementing
            :class:`everest.entities.interfaces.IAggregate`.
        """
        return self.__aggregate

    def create_member(self, entity):
        """
        Creates a new member resource from the given entity and adds it to
        this collection.
        """
        member = as_member(entity)
        self.add(member)
        return member

    def __len__(self):
        """
        Returns the size (count) of the collection.
        """
        return self.__aggregate.count()

    def __getitem__(self, key):
        """
        Gets a member (by name).

        :param key: Name of the member
        :type key: :class:`string` or :class:`unicode`
        :raises: :class:`everest.exceptions.MultipleResultsException` if more
          than one member is found for the given key value.
        :raises: KeyError If no entity is found for the given key.
        :returns: Object implementing
          :class:`everest.resources.interfaces.IMemberResource`.
        """
        ent = self.__aggregate.get_by_slug(key)
        if ent is None:
            raise KeyError(key)
        rc = as_member(ent, parent=self)
        return rc

    def __iter__(self):
        """
        Returns an iterator over the (possibly filtered and ordered)
        collection.
        """
        for obj in self.__aggregate.iterator():
            rc = as_member(obj, parent=self)
            yield rc

    def __contains__(self, member):
        """
        Checks if this collection contains the given member.

        :returns: `False` if a lookup of the ID of the given member returns
            `None` or if the ID is `None`; else, `True`.
        """
        return not (member.id is None \
                    or self.__aggregate.get_by_id(member.id) is None)

    def __str__(self):
        return "<%s name:%s parent:%s>" % (self.__class__.__name__,
                                           self.__name__, self.__parent__)

    def __repr__(self):
        return self.__str__()

    def add(self, member):
        """
        Adds the given member to this collection.

        :param member: Member to add.
        :type member: Object implementing
                    :class:`everest.resources.interfaces.IMemberResource`
        :raise ValueError: if a member with the same name exists
        """
        if IMemberResource.providedBy(member): #pylint: disable=E1101
            member.__parent__ = self
            data = member.get_entity()
        else:
            data = member
        self.__aggregate.add(data)

    def remove(self, member):
        """
        Removes the given member from this collection.

        :param member: Member to remove.
        :type member: Object implementing
                    :class:`everest.resources.interfaces.IMemberResource`
        :raise ValueError: if the member can not be found in this collection
        """
        is_member = IMemberResource.providedBy(member) #pylint: disable=E1101
        if is_member:
            data = member.get_entity()
        else:
            data = member
        self.__aggregate.remove(data)
        if is_member:
            member.__parent__ = None

    def get(self, key, default=None):
        """
        Returns a member for the given key or the given default value if no
        match was found in the collection.
        """
        try:
            rc = self.__getitem__(key)
        except KeyError:
            rc = default
        return rc

    def update(self, data, target=None):
        """
        Updates this collection from the given data.

        :param data: Any object that can be adapted to
          :class:`everest.interfaces.IDataTraversalProxyAdapter`.
        :returns: New updated member.
        """
        if not target is None:
            target = target.get_entity()
        updated_entity = self.__aggregate.update(data, target=target)
        return as_member(updated_entity, parent=self)

    def _get_filter(self):
        if self._relationship is None:
            filter_spec = self._filter_spec
        else:
            rel_spec = self._relationship.specification
            if self._filter_spec is None:
                filter_spec = rel_spec
            else:
                spec_fac = get_filter_specification_factory()
                filter_spec = spec_fac.create_conjunction(rel_spec,
                                                          self._filter_spec)
        return filter_spec

    def _set_filter(self, filter_spec):
        if not filter_spec is None:
            # Translate to entity filter expression before passing on to the
            # aggregate.
            visitor = ResourceToEntityFilterSpecificationVisitor(
                                                    get_member_class(self))
            filter_spec.accept(visitor)
            self.__aggregate.filter = visitor.expression
        else:
            self.__aggregate.filter = None
        self._filter_spec = filter_spec

    filter = property(_get_filter, _set_filter)

    def _get_order(self):
        return self._order_spec

    def _set_order(self, order_spec):
        if not order_spec is None:
            # Translate to entity order expression before passing on to the
            # aggregate.
            visitor = ResourceToEntityOrderSpecificationVisitor(
                                                    get_member_class(self))
            order_spec.accept(visitor)
            self.__aggregate.order = visitor.expression
        else:
            self.__aggregate.order = None
        self._order_spec = order_spec

    order = property(_get_order, _set_order)

    def _get_slice(self):
        return self.__aggregate.slice

    def _set_slice(self, slice_key):
        self.__aggregate.slice = slice_key

    slice = property(_get_slice, _set_slice)

    def clone(self):
        """
        Returns a clone of this collection.
        """
        agg = self.__aggregate.clone()
        clone = self.create_from_aggregate(agg)
        # Pass filter and order specs explicitly (may differ from the ones
        # at the aggregate level).
        # pylint: disable=W0212
        clone._filter_spec = self._filter_spec
        clone._order_spec = self._order_spec
        # pylint: enable=W0212
        clone.__parent__ = self.__parent__
        return clone

    @property
    def is_root_collection(self):
        return self._relationship is None and not self.__parent__ is None

    def get_root_collection(self, rc):
        """
        Returns a root collection for the given resource.

        The root collection is created using a root aggregate fetched from
        the same repository that was used to create the root aggregate for
        this collection.
        """
        root_agg = self.__aggregate.get_root_aggregate(rc)
        coll_cls = get_collection_class(rc)
        return coll_cls.create_from_aggregate(root_agg)

    @classmethod
    def as_related_collection(cls, aggregate, relationship):
        """
        Creates a new relationship collection with a relationship aggregate
        and the relationship's relator as a parent.
        """
        rel_coll = cls.create_from_aggregate(aggregate,
                                             relationship=relationship)
        # The member at the origin of the relationship is the parent.
        rel_coll.__parent__ = relationship.relator
        # Set the collection's name to the descriptor's resource
        # attribute name.
        rel_coll.__name__ = \
            slug_from_identifier(relationship.descriptor.resource_attr)
        return rel_coll


@implementer(ISpecificationVisitor)
class ResourceToEntitySpecificationVisitor(SpecificationExpressionHolder):
    """
    Base class for specification visitors that convert resource to entity
    attribute names.
    """

    def __init__(self, rc_class):
        SpecificationExpressionHolder.__init__(self)
        self.__rc_class = rc_class

    def visit_nullary(self, spec):
        entity_attr_name = self.__convert_to_entity_attr(spec.attr_name)
        new_spec = self._make_new_spec(entity_attr_name, spec)
        self._push(new_spec)

    def visit_unary(self, spec):
        last = self._pop()
        new_spec = spec.__class__(last)
        self._push(new_spec)

    def visit_binary(self, spec):
        right = self._pop()
        left = self._pop()
        new_spec = spec.__class__(left, right)
        self._push(new_spec)

    def __convert_to_entity_attr(self, rc_attr_name):
        entity_attr_tokens = []
        rc_class = self.__rc_class
        for rc_attr_token in rc_attr_name.split('.'):
            rc_attr = get_resource_class_attribute(rc_class, rc_attr_token)
            if rc_attr is None:
                raise AttributeError('%s resource does not have an attribute '
                                     '"%s".'
                                     % (rc_class.__name__, rc_attr_name))
            ent_attr_name = rc_attr.entity_attr
            if ent_attr_name is None:
                raise ValueError('Resource attribute "%s" does not have a '
                                 'corresponding entity attribute.'
                                 % rc_attr.resource_attr)
            if rc_attr.kind != RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                # Look up the member class for the specified member or
                # collection resource interface.
                rc_class = get_member_class(rc_attr.attr_type)
            entity_attr_tokens.append(ent_attr_name)
        return '.'.join(entity_attr_tokens)

    def _make_new_spec(self, new_attr_name, old_spec):
        raise NotImplementedError('Abstract method.')


class ResourceToEntityFilterSpecificationVisitor(
                                        ResourceToEntitySpecificationVisitor):
    """
    Filter specification visitor that converts resource attribute names to
    entity attribute names.
    """
    def _make_new_spec(self, new_attr_name, old_spec):
        return old_spec.__class__(new_attr_name, old_spec.attr_value)


class ResourceToEntityOrderSpecificationVisitor(
                                        ResourceToEntitySpecificationVisitor):
    """
    Order specification visitor that converts resource attribute names to
    entity attribute names.
    """
    def _make_new_spec(self, new_attr_name, old_spec):
        return old_spec.__class__(new_attr_name)
