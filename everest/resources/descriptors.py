"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Descriptors for resource classes.

Created on Apr 19, 2011.
"""

from everest.entities.utils import get_aggregate
from everest.resources.interfaces import ICollectionResource
from everest.querying.nesting import Nesting
from everest.resources.utils import as_member
from everest.resources.utils import get_member_class
from everest.resources.utils import get_root_collection
from everest.utils import id_generator
from repoze.bfg.traversal import find_root
from zope.component import getAdapter as get_adapter # pylint: disable=E0611,F0401

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

    :ivar int id: unique sequential numeric ID for this attribute. Since this
      ID is incremented each time a new resource attribute is declared,
      it can be used to establish a well-defined sorting order on all
      attribute declarations of a resource.
    """

    __id_gen = id_generator()

    def __init__(self, attr_name, attr_type):
        """
        :param str attr_name: the name of the entity attribute this descriptor
            controls.
        :param attr_type: the type (or interface) of the controlled entity
            attribute.
        """
        self.attr_name = attr_name
        self.attr_type = attr_type
        self.id = self.__id_gen.next()

    def __get__(self, resource, resource_class):
        raise NotImplementedError('Abstract method')

    def __set__(self, resource, value):
        raise NotImplementedError('Abstract method')

    def _set_nested(self, entity, attr_name, value):
        parent, attr_name = self.__resolve_nested(entity, attr_name)
        if parent is None:
            raise AttributeError('Can not set attribute "%s" on None value.'
                                 % attr_name)
        setattr(parent, attr_name, value)

    def _get_nested(self, entity, attr_name):
        parent, attr_name = self.__resolve_nested(entity, attr_name)
        if not parent is None:
            attr_value = getattr(parent, attr_name)
        else:
            attr_value = None
        return attr_value

    def __resolve_nested(self, entity, attr_name):
        tokens = attr_name.split('.')
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
            obj = self._get_nested(resource.get_entity(), self.attr_name)
        return obj

    def __set__(self, resource, value):
        self._set_nested(resource.get_entity(), self.attr_name, value)


class _relation_attribute(attribute_base):
    """
    Base class for relation resource descriptors (i.e., descriptors managing
    a related member or collection resource).
    """
    def __init__(self, attr_name, attr_type, is_nested=False):
        """
        :param bool is_nested: indicates if the URLs generated for this
            relation descriptor should be relative to the parent ("nested")
            or absolute.
        """
        attribute_base.__init__(self, attr_name, attr_type)
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
            obj = self._get_nested(resource.get_entity(), self.attr_name)
            if not obj is None:
                if not self.is_nested:
                    member = as_member(obj)
                    coll = get_root_collection(member)
                    member.__parent__ = coll
                else:
                    member = as_member(obj, parent=resource)
            else:
                member = obj
        else:
            # class level access
            member = self
        return member

    def __set__(self, resource, value):
        self._set_nested(resource.get_entity(), self.attr_name,
                         value.get_entity())


class collection_attribute(_relation_attribute):
    """
    Descriptor for declaring collection attributes of a resource as attributes
    from its underlying entity.
    """
    def __init__(self, attr_name, attr_type, backref_attr_name=None,
                 is_nested=True, ** kw):
        """
        :param str backref_attr_name:
        """
        _relation_attribute.__init__(self, attr_name, attr_type,
                                     is_nested=is_nested, **kw)
        self.backref_attr_name = backref_attr_name
        self.__resource_backref_attr_name = None
        self.__entity_backref_attr_name = None
        self.__need_backref_setup = True

    def __get__(self, resource, resource_class):
        if self.__need_backref_setup:
            self.__setup_backref()
        if not resource is None:
            # Create relation collection. We can not just return the
            # entity attribute here as that would load the whole entity
            # collection (Alternatively, we could use dynamic attributes).
            parent = resource.get_entity()
            children = None
            for attr_token in self.attr_name.split('.'):
                if children is None:
                    children = getattr(parent, attr_token)
                else:
                    children = getattr(children, attr_token)
                if children is None:
                    break
            if children is None:
                coll = None
            else:
                nst = Nesting(parent, children,
                              backref_attribute=self.__entity_backref_attr_name)
                agg = get_aggregate(self.attr_type, relation=nst)
                coll = get_adapter(agg, ICollectionResource)
                if self.is_nested:
                    # Make URL generation relative to the resource.
                    coll.set_parent(resource)
                else:
                    # Make URL generation relative to the app root.
                    nst = Nesting(resource, coll,
                                  backref_attribute=
                                            self.__resource_backref_attr_name)
                    coll.set_parent(find_root(resource), nesting=nst)
        else:
            # Class level access.
            coll = self
        return coll

    def __set__(self, resource, value):
        ent_coll = self._get_nested(resource.get_entity(), self.attr_name)
        ent_coll_cls = type(ent_coll)
        new_ent_coll = ent_coll_cls([mb.get_entity() for mb in value])
        self._set_nested(resource.get_entity(), self.attr_name, new_ent_coll)

    def __setup_backref(self):
        attr_mb_class = get_member_class(self.attr_type)
        if not self.backref_attr_name is None:
            backref_rc_descr = getattr(attr_mb_class,
                                       self.backref_attr_name, None)
            if not backref_rc_descr is None:
                self.__resource_backref_attr_name = self.backref_attr_name
                self.__entity_backref_attr_name = backref_rc_descr.attr_name
            else:
                self.__entity_backref_attr_name = self.backref_attr_name
        self.__need_backref_setup = False


class attribute_alias(object):
    """
    Descriptor for declaring an alias to another attribute declared by an
    attribute descriptor.
    """
    def __init__(self, alias_attr_name):
        self.alias_attr_name = alias_attr_name

    def __get__(self, resource, resource_class):
        if resource is None:
            # Class level access.
            obj = self
        else:
            descr = getattr(resource_class, self.alias_attr_name)
            obj = descr.__get__(resource, resource_class)
        return obj

    def __set__(self, resource, value):
        descr = getattr(type(resource), self.alias_attr_name)
        descr.__set__(resource, value)
