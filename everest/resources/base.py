"""
Resources.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 3, 2011.
"""
from everest.entities.utils import get_entity_class
from everest.entities.utils import identifier_from_slug
from everest.querying.base import SpecificationVisitorBase
from everest.querying.interfaces import ISpecificationVisitor
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.utils import get_filter_specification_factory
from everest.representers.interfaces import ILinkedDataElement
from everest.resources.attributes import ResourceAttributeControllerMixin
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.attributes import get_resource_class_attributes
from everest.resources.descriptors import terminal_attribute
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResource
from everest.resources.link import Link
from everest.resources.utils import as_member
from everest.resources.utils import get_member_class
from everest.resources.utils import resource_to_url
from everest.resources.utils import url_to_resource
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.traversal import model_path
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
import uuid
from everest.resources.utils import get_service

__docformat__ = "reStructuredText en"
__all__ = ['Collection',
           'Member',
           'Resource',
           ]


class Resource(object):
    """
    This is the abstract base class for all resources.
    """
    implements(IResource)

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

    def __init__(self):
        """
        Constructor:
        """
        if self.__class__ is Resource:
            raise NotImplementedError('Abstract class')
        if self.__class__.relation is None:
            raise ValueError('Resource classes must have a relation '
                             'attribute.')
        #: A set of links to other resources.
        self.links = set()

    def add_link(self, link):
        """
        Adds a link to another resource.

        :param link: a resource link
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

    @classmethod
    def create_from_data(cls, data_element):
        """
        Creates a resource instance from the given data element (tree).

        :param data_element: data element (hierarchical) to create a resource
            from
        :type data_element: object implementing
         :class:`everest.resources.representers.interfaces.IExplicitDataElement`
        """
        return data_element.mapping.map_to_resource(data_element)


class Member(ResourceAttributeControllerMixin, Resource):
    """
    This is an abstract class for all member resources.
    """
    implements(IMemberResource)

    id = terminal_attribute(int, 'id')

    def __init__(self, entity, name=None):
        """
        Constructor:

        :param name: unique name of the member within the collection
        :type name: :class:`string`
        :param entity: the associated entity (domain object)
        :type entity: an object implementing an interface derived from
                :class:`everest.entities.interfaces.IEntity`
        """
        if self.__class__ is Member:
            raise NotImplementedError('Abstract class')
        if not isinstance(entity, get_entity_class(self)):
            raise ValueError(
                    'Invalid entity class "%s" for %s resource class.'
                    % (entity.__class__.__name__, self.__class__.__name__))
        super(Member, self).__init__()
        self.__entity = entity
        # Add the rel="self" link.
        self.add_link(Link(self, "self"))
        self.__name = name

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

        :return: an object implementing
            :class:`everest.entities.interfaces.IEntity`.
        """
        return self.__entity

    def delete(self):
        """
        Deletes this member.

        Deleting a member resource means removing it from its parent
        resource.
        """
        self.__parent__.remove(self)

    def update_from_entity(self, new_entity):
        """
        Updates this member from the given new entity.
        
        See :method:`Collection.update_from_entity`.
        """
        self.__parent__.update_from_entity(self, new_entity)

    def update_from_data(self, data_element):
        """
        Updates this member from the given data element.

        :param data_element: data element (hierarchical) to create a resource
            from
        :type data_element: object implementing
         `:class:everest.resources.representers.interfaces.IExplicitDataElement`

        """
        mp = data_element.mapping
        for attr in mp.attribute_iterator():
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                other_value = data_element.get_terminal(attr)
                if other_value is None:
                    # Optional attribute - continue.
                    continue
                else:
                    setattr(self, attr.name, other_value)
            else: # attr.kind MEMBER or COLLECTION
                rc_data_el = data_element.get_nested(attr)
                if rc_data_el is None:
                    # Optional attribute - continue.
                    continue
                self_rc = getattr(self, attr.name)
                if ILinkedDataElement in provided_by(rc_data_el):
                    # Found a link. Update if the URL is different.
                    url = rc_data_el.get_url()
                    if not self_rc is None \
                       and resource_to_url(self_rc) == url:
                        #
                        continue
                    new_rc = url_to_resource(url)
                    setattr(self, attr.name, new_rc)
                else:
                    if self_rc is None:
                        new_rc = mp.map_to_resource(rc_data_el)
                        setattr(self, attr.name, new_rc)
                    else:
                        self_rc.update_from_data(rc_data_el)

    def __getitem__(self, item):
        ident = identifier_from_slug(item)
        attr = get_resource_class_attributes(self.__class__).get(ident)
        if attr is None or not attr.is_nested:
            raise KeyError('%s' % ident)
        return getattr(self, ident)

    def __eq__(self, other):
        """
        Equality operator.

        Equality is based on a resource\'s name only.
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


class Collection(Resource):
    """
    This is an abstract base class for all resource collections.
    A collection is a set of member resources which can be filtered, sorted,
    and sliced.
    """
    implements(ICollectionResource)

    #: The title of the collection.
    title = None
    #: The name for the root collection (used as URL path to the root
    #: collection inside the service).
    root_name = None

    #: A description of the collection.
    description = ''
    #: The default order of the collection's members.
    default_order = AscendingOrderSpecification('id')
    # The default number of members shown on one page (superclass default: 100).
    default_limit = 100
    #: The maximum number of member that can be shown on one page
    #: (superclass default: 1000).
    max_limit = 1000

    def __init__(self, aggregate, name=None):
        """
        Constructor:

        :param name: the name of the collection
        :type name: :class:`string`
        :param aggregate: the associated aggregate
        :type aggregate: :class:`everest.entities.aggregates.Aggregate` -
                an object implementing an interface derived from
                :class:`everest.entities.interfaces.IAggregate`
        """
        if self.__class__ is Collection:
            raise NotImplementedError('Abstract class')
        if self.title is None:
            raise ValueError('Collection must have a title.')
        Resource.__init__(self)
        if name is None:
            name = self.root_name
        self.__name__ = name
        #: The filter specification for this resource. Attribute names in
        #: this specification are relative to the resource..
        self._filter_spec = None
        #: The order specification for this resource. Attribute names in
        #: this specification are relative to the resource.
        self._order_spec = None
        # The underlying aggregate.
        self.__aggregate = aggregate
        #
        self.__relationship = None

    @classmethod
    def create_from_aggregate(cls, aggregate):
        """
        Creates a new collection from the given aggregate.

        :param aggregate: aggregate containing the entities exposed by this
              collection resource
        :type aggregate: :class:`everest.entities.aggregates.Aggregate` instance
        """
        return cls(aggregate)

    def set_relationship(self, relationship):
        """
        Sets the relation parent for this collection.

        The relation parent affects the expressions built for filter and order 
        operations.

        :param relationship: relation with another resource, encapsulated in a
          :class:`everest.relationship.Relationship` instance.
        """
        self.__relationship = relationship

    def get_aggregate(self):
        """
        Returns the aggregate underlying this collection.

        :return: an object implementing
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

    @property
    def is_nested(self):
        return not self.__parent__ is get_service()

    def __len__(self):
        """
        Returns the size (count) of the collection.
        """
        return self.__aggregate.count()

    def __getitem__(self, key):
        """
        Gets a member (by name).

        :param key: the name of the member
        :type key: :class:`string` or :class:`unicode`
        :raises: :class:`everest.exceptions.DuplicateException` if more than
          one member is found for the given key value.
        :returns: object implementing
          :class:`everest.resources.interfaces.IMemberResource`
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

    def __str__(self):
        return "<%s name:%s parent:%s>" % (self.__class__.__name__,
                                           self.__name__, self.__parent__)

    def __repr__(self):
        return self.__str__()

    def add(self, member):
        """
        Adds the given member to this collection.

        :param member: member to add.
        :type member: object implementing
                    :class:`everest.resources.interfaces.IMemberResource`
        :raise ValueError: if a member with the same name exists
        """
        self.__aggregate.add(member.get_entity())
        member.__parent__ = self

    def remove(self, member):
        """
        Removes the given member from this collection.

        :param member: member to add.
        :type member: object implementing
                    :class:`everest.resources.interfaces.IMemberResource`
        :raise ValueError: if the member can not be found in this collection
        """
        self.__aggregate.remove(member.get_entity())
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

    def update_from_data(self, data_element):
        """
        Updates this collection from the given data element.

        This iterates over the members of this collection and checks if
        a member with the same ID exists in the given update data. If yes, 
        the existing member is updated with the update member; if no,
        the member is removed. All data elements in the update data that
        have no ID are added as new members. Data elements with an ID that
        can not be found in this collection trigger an error.

        :param data_element: data element (hierarchical) to create a resource
            from
        :type data_element: object implementing
         `:class:everest.resources.interfaces.IExplicitDataElement`
        :raises ValueError: when a data element with an ID that is not present
          in this collection is encountered.
        """
        attrs = data_element.mapping.get_attribute_map()
        id_attr = attrs['id']
        update_ids = set()
        new_mb_els = []
        self_id_map = dict([(self_mb.id, self_mb) for self_mb in iter(self)])
        for member_el in data_element.get_members():
#            if ILinkedDataElement in provided_by(member_el):
#                # Found a link - do not do anything.
#                mb_id = member_el.get_id()
#            else:
            mb_id = member_el.get_terminal(id_attr)
            if mb_id is None:
                # New data element without an ID - queue for adding.
                new_mb_els.append(member_el)
                continue
            else:
                self_mb = self_id_map.get(mb_id)
                if not self_mb is None:
                    # Found an existing member - update.
                    self_mb.update_from_data(member_el)
                else:
                    # New data element with a new ID. This is suspicious.
                    raise ValueError('New member data should not provide '
                                     'an ID attribute.')
            update_ids.add(mb_id)
        # Before adding any new members, check for delete operations.
        for self_mb in iter(self):
            if not self_mb.id in update_ids:
                # Found an existing member ID that was not supplied with
                # the update data- remove.
                self.remove(self_mb)
        # Now, add new members.
        mb_cls = get_member_class(self.__class__)
        for new_member_el in new_mb_els:
            new_member = mb_cls.create_from_data(new_member_el)
            self.add(new_member)

    def update_from_entity(self, member, source_entity):
        """
        Updates the given member from the given entity.
        
        Unlike :method:`update_from_data`, this completely disregards all
        resource attribute declarations and relies on the entity store to
        perform the state update.
        
        :param member: Member resource to update.
        :param source_entity: Entity (domain object) to use
        """
        self.__aggregate.update(member.get_entity(), source_entity)

    def _get_filter(self):
        if self.__relationship is None:
            filter_spec = self._filter_spec
        else:
            # Prepend the relationship specification to the current filter
            # specification.
            if self._filter_spec is None:
                filter_spec = self.__relationship.specification
            else:
                spec_fac = get_filter_specification_factory()
                filter_spec = spec_fac.create_conjunction(
                                            self.__relationship.specification,
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
        clone.__parent__ = self.__parent__
        clone.set_relationship(self.__relationship)
        # Pass filter and order specs explicitly (may differ from the ones
        # at the aggregate level).
        clone._filter_spec = self._filter_spec # pylint: disable=W0212
        clone._order_spec = self._order_spec # pylint: disable=W0212
        return clone


class ResourceToEntitySpecificationVisitor(SpecificationVisitorBase):
    """
    Base class for specification visitors that convert resource to entity
    attribute names.
    """
    implements(ISpecificationVisitor)

    def __init__(self, rc_class):
        SpecificationVisitorBase.__init__(self)
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
            rc_attr = get_resource_class_attributes(rc_class)[rc_attr_token]
            ent_attr_name = rc_attr.entity_name
            if ent_attr_name is None:
                raise ValueError('Resource attribute "%s" does not have a '
                                 'corresponding entity attribute.'
                                 % rc_attr.name)
            if rc_attr.kind != ResourceAttributeKinds.TERMINAL:
                # Look up the member class for the specified member or
                # collection resource interface.
                rc_class = get_member_class(rc_attr.value_type)
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
