"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Resource base classes.

Created on Nov 3, 2011.
"""

from everest.entities.utils import get_entity_class_for_member
from everest.representers.attributes import ResourceAttributeKinds
from everest.representers.base import DataElementParser
from everest.representers.interfaces import ILinkedDataElement
from everest.resources.descriptors import terminal_attribute
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResource
from everest.resources.link import Link
from everest.resources.utils import as_member
from everest.resources.utils import get_member_class
from everest.utils import classproperty
from repoze.bfg.security import Allow
from repoze.bfg.security import Authenticated
from repoze.bfg.traversal import model_path
from zope.component import createObject as create_object # pylint: disable=E0611,F0401
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
import uuid

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

    #: Authentication specifier.
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
    #: The relation identifier to show in links to this resource.
    relation = None
    #: Descriptive title for this resource.
    title = ''
    #: Detailed description of this resource.
    description = ''
    #: Caching time in seconds or None for no caching.
    cache_for = None

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


class Member(Resource):
    """
    This is an abstract class for all member resources.
    """

    implements(IMemberResource)

    id = terminal_attribute('id', int)

    def __init__(self, entity):
        """
        Constructor:

        :param name: unique name of the member within the collection
        :type name: :class:`string`
        :param entity: the associated entity (domain object)
        :type entity: an object implementing an interface derived from
                :class:`everest.models.interfaces.IEntity`
        """
        if self.__class__ is Member:
            raise NotImplementedError('Abstract class')
        if not isinstance(entity, get_entity_class_for_member(self)):
            raise ValueError(
                    'Invalid entity class "%s" for %s resource class.'
                    % (entity.__class__.__name__, self.__class__.__name__))
        Resource.__init__(self)
        self.__entity = entity
        # Add the rel="self" link.
        self.add_link(Link(self, "self"))

    @property
    def __name__(self):
        """
        Member resources have a read-only __name__ attribute determined by
        they underlying entitie's slug.
        """
        return self.__entity.slug

    @classmethod
    def create_from_entity(cls, entity):
        """
        Class factory method creating a new resource from the given entity.
        """
        return cls(entity)

    @classmethod
    def create_from_data(cls, data_element):
        """
        Creates a resource instance from the given data element (tree).

        :param data_element: data element (hierarchical) to create a resource
            from
        :type data_element: object implementing
         :class:`everest.resources.representers.interfaces.IExplicitDataElement`
        """
        parser = DataElementParser()
        return parser.extract_member_resource(data_element)

    def get_entity(self):
        """
        Returns the entity this resource is wrapped around.

        :return: an object of a :class:`everest.models.base.Entity` subclass
        """
        return self.__entity

    def delete(self):
        """
        Deletes this member.

        Deleting a member resource means removing it from its parent
        resource.
        """
        self.__parent__.remove(self)

    def update_from_data(self, data_element):
        """
        Updates this member from the given data element.

        :param data_element: data element (hierarchical) to create a resource
            from
        :type data_element: object implementing
         `:class:everest.resources.representers.interfaces.IExplicitDataElement`

        """
        attrs = data_element.mapper.get_mapped_attributes(self.__class__)
        for attr in attrs.values():
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                other_value = data_element.get_terminal(attr)
                if other_value is None:
                    # Optional attribute - continue.
                    continue
                else:
                    setattr(self, attr.name, other_value)
            elif attr.kind in (ResourceAttributeKinds.MEMBER,
                               ResourceAttributeKinds.COLLECTION):
                rc_data_el = data_element.get_nested(attr)
                if rc_data_el is None:
                    # Optional attribute - continue.
                    continue
                if ILinkedDataElement in provided_by(rc_data_el):
                    # Found a link - do not do anything.
                    continue
                else:
                    self_rc = getattr(self, attr.name)
                    if self_rc is None:
                        new_rc = attr.value_type.create_from_data(rc_data_el)
                        setattr(self, attr.name, new_rc)
                    else:
                        self_rc.update_from_data(rc_data_el)
            else:
                raise ValueError('Invalid resource attribute kind.')

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

    __relation = None

    @classproperty
    def relation(cls): # no self pylint: disable=E0213
        if not hasattr(cls, '__relation'):
            member_cls = get_member_class(cls)
            cls.__relation = "%s-collection" % member_cls.relation
        return cls.__relation

    #: A description of the collection.
    description = ''
    #: The default order of the collection's members.
    default_order = None
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
        :type aggregate: :class:`everest.models.aggregates.Aggregate` -
                an object implementing an interface derived from
                :class:`everest.models.interfaces.IAggregate`
        """
        if self.__class__ is Collection:
            raise NotImplementedError('Abstract class')
        if self.title is None:
            raise ValueError('Collection must have a title.')
        Resource.__init__(self)
        if name is None:
            name = self.root_name
        self.__name__ = name
        self.__aggregate = aggregate

    @classmethod
    def create_from_aggregate(cls, aggregate):
        """
        Creates a new collection from the given aggregate.

        :param aggregate: aggregate containing the entities exposed by this
              collection resource
        :type aggregate: :class:`everest.models.aggregates.Aggregate` instance
        """
        return cls(aggregate)

    @classmethod
    def create_from_data(cls, data_element):
        """
        Creates a new collection from the given data element.

        :param data_element: data element tree
        :type data_element: object implementing
         :class:`everest.resources.representers.interfaces.IExplicitDataElement`
        """
        parser = DataElementParser()
        return parser.extract_collection_resource(data_element)

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

    def get(self, key, default=None):
        """
        Returns a member or a list of members by the given key or the given
        default value if no match was found in the collection.
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
        a member with the same ID exists in the given update data; if
        yes, the existing member is updated with the update member, if no,
        the member is removed. All data elements in the update data that
        have no ID are added as new members. Data elements with an ID that
        can not be found in this collection trigger an error.

        :param data_element: data element (hierarchical) to create a resource
            from
        :type data_element: object implementing
         `:class:everest.resources.representers.interfaces.IExplicitDataElement`
        """
        mb_cls = get_member_class(self.__class__)
        attrs = data_element.mapper.get_mapped_attributes(mb_cls)
        id_attr = attrs['id']
        update_ids = set()
        new_mb_els = []
        self_id_map = dict([(self_mb.id, self_mb) for self_mb in iter(self)])
        for member_el in data_element.get_members():
            if ILinkedDataElement in provided_by(member_el):
                # Found a link - do not do anything.
                mb_id = member_el.get_id()
            else:
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
                # Found an existing member ID that was not supplierd with
                # the update data- remove.
                self.remove(self_mb)
        # Now, add new members.
        for new_member_el in new_mb_els:
            new_member = mb_cls.create_from_data(new_member_el)
            self.add(new_member)

    def _get_filter(self):
        return self.__aggregate.get_filter_spec()

    def _set_filter(self, filter_spec):
        self.__aggregate.filter(filter_spec)

    filter = property(_get_filter, _set_filter)

    def _get_order(self):
        return self.__aggregate.get_order_spec()

    def _set_order(self, order_spec):
        self.__aggregate.order(order_spec)

    order = property(_get_order, _set_order)

    def _get_slice(self):
        return self.__aggregate.get_slice_key()

    def _set_slice(self, slice_key):
        self.__aggregate.slice(slice_key)

    slice = property(_get_slice, _set_slice)

    def clone(self):
        """
        Returns a clone of this collection.
        """
        agg = self.__aggregate.clone()
        clone = self.create_from_aggregate(agg)
        clone.__parent__ = self.__parent__
        return clone

    def _format_name(self, name):
        return unicode(name)

    def _create_collection(self):
        return create_object(self.__name__)
