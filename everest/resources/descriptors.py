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
from everest.resources.utils import get_stage_collection
from everest.utils import id_generator
from repoze.bfg.traversal import find_root

__docformat__ = 'reStructuredText en'
__all__ = ['attribute_alias',
           'attribute_base',
           'collection_attribute',
           'member_attribute',
           'terminal_attribute',
           ]


class attribute_base(object):
    """
    Abstract base class for all attribute descriptors.

    :ivar entity_attr: the controlled entity attribute.
    :ivar entity_type: the type (or interface) of the controlled entity 
      attribute.
    :ivar int id: unique sequential numeric ID for this attribute. Since this
      ID is incremented each time a new resource attribute is declared,
      it can be used to establish a well-defined sorting order on all
      attribute declarations of a resource.
    :ivar resource_attr: the resource attribute this descriptor is mapped to.
      This is set after instantiation. 
    """

    __id_gen = id_generator()

    def __init__(self, entity_attr, entity_type):
        self.entity_attr = entity_attr
        self.entity_type = entity_type
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
    def __init__(self, entity_attr, entity_type, is_nested=False):
        """
        :param bool is_nested: indicates if the URLs generated for this
            relation descriptor should be relative to the parent ("nested")
            or absolute.
        """
        attribute_base.__init__(self, entity_attr, entity_type)
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
        self._set_nested(resource.get_entity(), self.entity_attr,
                         value.get_entity())


class collection_attribute(_relation_attribute):
    """
    Descriptor for declaring collection attributes of a resource as attributes
    from its underlying entity.
    """
    def __init__(self, entity_attr, entity_type, backref_attr=None,
                 is_nested=True, **kw):
        """
        :param str backref_attr: attribute of the members of the target
          collection which back-references the current resource (parent).
        """
        _relation_attribute.__init__(self, entity_attr, entity_type,
                                     is_nested=is_nested, **kw)
        self.backref_attr = backref_attr
        self.__resource_backref_attr = None
        self.__entity_backref_attr = None
        self.__need_backref_setup = True

    def __get__(self, resource, resource_class):
        if self.__need_backref_setup:
            self.__setup_backref()
        if not resource is None:
            coll = self.__make_collection(resource)
        else:
            # Class level access.
            coll = self
        return coll

    def __set__(self, resource, value):
        ent_coll = self._get_nested(resource.get_entity(), self.entity_attr)
        ent_coll_cls = type(ent_coll)
        new_ent_coll = ent_coll_cls([mb.get_entity() for mb in value])
        self._set_nested(resource.get_entity(), self.entity_attr, new_ent_coll)

    def __setup_backref(self):
        attr_mb_class = get_member_class(self.entity_type)
        if not self.backref_attr is None:
            backref_rc_descr = getattr(attr_mb_class,
                                       self.backref_attr, None)
            if not backref_rc_descr is None:
                self.__resource_backref_attr = self.backref_attr
                self.__entity_backref_attr = backref_rc_descr.entity_attr
            else:
                self.__entity_backref_attr = self.backref_attr
        self.__need_backref_setup = False

    def __make_collection(self, resource):
        # Create relation collection. We can not just return the
        # entity attribute here as that would load the whole entity
        # collection (Alternatively, we could use dynamic attributes).
        parent = resource.get_entity()
        children = self._get_nested(parent, self.entity_attr)
        if children is None:
            coll = None
        else:
            if not resource.__parent__ is None:
                # Find the resource repository used for this resource's parent
                # and use it to create the new collection.
                rc_repo = \
                        ResourceRepository.get_repository(resource.__parent__)
                coll = rc_repo.get(self.entity_type)
            else:
                # This is a floating member, assume stage repository.
                coll = get_stage_collection(self.entity_type)
            # All resource references are relationships; we need to set this 
            # up on the aggregate.
            agg = coll.get_aggregate()
            rel = Relationship(parent, children,
                               backref_attribute=self.__entity_backref_attr)
            agg.set_relationship(rel)
            if self.is_nested:
                # Make URL generation relative to the resource.
                coll.set_parent(resource)
                # Set the collection's name to the descriptor's resource
                # attribute name.
                coll.__name__ = slug_from_identifier(self.resource_attr)
            else:
                # Make URL generation relative to the app root.
                rel = Relationship(resource, coll,
                                   backref_attribute=
                                        self.__resource_backref_attr)
                coll.set_parent(find_root(resource), relation=rel)
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
