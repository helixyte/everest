"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Data element classes.

Created on Apr 25, 2012
"""
from everest.representers.base import data_element_tree_to_string
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.representers.interfaces import IResourceDataElement
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.kinds import ResourceKinds
from everest.resources.utils import provides_collection_resource
from everest.resources.utils import provides_member_resource
from everest.url import resource_to_url
from zope.interface import implements # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401


class DataElement(object):
    """
    Abstract base class for data element classes.

    Data elements manage value state during serialization and deserialization.
    Implementations may need to be adapted to the format of the external
    representation they manage.
    """

    implements(IResourceDataElement)

    #: Static attribute mapping.
    mapping = None

    @classmethod
    def create(cls):
        """
        Basic factory method.
        """
        inst = cls()
        return inst

    @classmethod
    def create_from_resource(cls, resource):
        """
        (Abstract) factory method taking a resource as input.
        """
        raise NotImplementedError('Abstract method.')

    def __str__(self):
        return data_element_tree_to_string(self)


class MemberDataElement(DataElement):
    """
    Abstract base class for member data element classes.
    """

    implements(IMemberDataElement)

    def get_terminal(self, attr):
        """
        Returns the value for the given mapped terminal resource attribute.

        @return: attribute value or `None` if no value is found for the given
            attribute name.
        """
        raise NotImplementedError('Abstract method.')

    def set_terminal(self, attr, value):
        """
        Sets the value for the given mapped terminal resource attribute.
        """
        raise NotImplementedError('Abstract method.')

    def get_nested(self, attr):
        """
        Returns the mapped nested resource attribute (either a member or a
        collection resource attribute).

        @returns: object implementing `:class:IDataelement` or
          `None` if no nested resource is found for the given attribute name.
        """
        raise NotImplementedError('Abstract method.')

    def set_nested(self, attr, data_element):
        """
        Sets the value for the given mapped nested resource attribute (either
        a member or a collection resource attribute).

        @param data_element: a :class:DataElement or :class:LinkedDataElement
          object containing nested resource data.
        """
        raise NotImplementedError('Abstract method.')


class CollectionDataElement(DataElement):
    """
    Abstract base class for collection data elements.
    """

    implements(ICollectionDataElement)

    def add_member(self, data_element):
        """
        Adds the given member data element to this collection data element.
        """
        raise NotImplementedError('Abstract method.')

    def get_members(self):
        """
        Returns all member data elements added to this collection data element.
        """
        raise NotImplementedError('Abstract method.')

    def __len__(self):
        """
        Returns the number of member data elements in this collection data
        element.
        """
        raise NotImplementedError('Abstract method.')


class _SimpleDataElementMixin(object):
    @classmethod
    def create_from_resource(cls, resource): # ignore resource pylint:disable=W0613,W0221
        return cls()


class SimpleMemberDataElement(_SimpleDataElementMixin, MemberDataElement):
    """
    Basic implementation of a member data element.
    """
    __nested = None

    def get_terminal(self, attr):
        return getattr(self, attr.repr_name, None)

    def set_terminal(self, attr, value):
        setattr(self, attr.repr_name, value)

    def get_nested(self, attr):
        nested = self.__get_nested()
        return nested.get(attr.repr_name)

    def set_nested(self, attr, data_element):
        nested = self.__get_nested()
        nested[attr.repr_name] = data_element

    def __get_nested(self):
        if self.__nested is None:
            self.__nested = {}
        return self.__nested


class SimpleCollectionDataElement(_SimpleDataElementMixin,
                                  CollectionDataElement):
    """
    Basic implementation of a collection data element.
    """
    __members = None

    def add_member(self, data_element):
        members = self.__get_members()
        members.append(data_element)

    def get_members(self):
        return self.__get_members()

    def __get_members(self):
        if self.__members is None:
            self.__members = []
        return self.__members

    def __len__(self):
        return len(self.__members)


class LinkedDataElement(object):
    """
    Data element managing a linked resource during serialization and
    deserialization.
    """

    implements(ILinkedDataElement)

    @classmethod
    def create(cls, url, kind, relation=None, title=None, **options):
        raise NotImplementedError('Abstract method.')

    @classmethod
    def create_from_resource(cls, resource):
        raise NotImplementedError('Abstract method.')

    def get_url(self):
        raise NotImplementedError('Abstract method.')

    def get_kind(self):
        raise NotImplementedError('Abstract method.')

    def get_relation(self):
        raise NotImplementedError('Abstract method.')

    def get_title(self):
        raise NotImplementedError('Abstract method.')


class SimpleLinkedDataElement(LinkedDataElement):
    """
    Basic implementation of a linked data element.
    """
    __url = None
    __kind = None
    __relation = None
    __title = None

    @classmethod
    def create(cls, url, kind, relation=None, title=None, **options):
        inst = cls()
        inst.__url = url
        inst.__kind = kind
        inst.__relation = relation
        inst.__title = title
        return inst

    @classmethod
    def create_from_resource(cls, resource):
        if provides_member_resource(resource):
            kind = ResourceKinds.MEMBER
        elif provides_collection_resource(resource):
            kind = ResourceKinds.COLLECTION
        else:
            raise ValueError('"%s" is not a resource.' % resource)
        return cls.create(resource_to_url(resource), kind,
                          relation=resource.relation,
                          title=resource.title)

    def get_url(self):
        return self.__url

    def get_kind(self):
        return self.__kind

    def get_relation(self):
        return self.__relation

    def get_title(self):
        return self.__title


class DataElementAttributeProxy(object):
    def __init__(self, data_element):
        self.__data_element = data_element
        if not ILinkedDataElement in provided_by(data_element):
            attrs = data_element.mapping.attribute_iterator()
        else:
            attrs = ()
        self.__attr_map = dict([(attr.repr_name, attr) for attr in attrs])

    def __getattr__(self, name):
        try:
            value = getattr(self.__data_element, name)
        except AttributeError:
            try:
                attr = self.__attr_map[name]
            except KeyError:
                raise AttributeError(name)
            else:
                if attr.kind == ResourceAttributeKinds.TERMINAL:
                    value = self.__data_element.get_terminal(attr)
                else:
                    nested_data_el = self.__data_element.get_nested(attr)
                    if nested_data_el is None:
                        value = None
                    elif attr.kind == ResourceAttributeKinds.MEMBER:
                        value = DataElementAttributeProxy(nested_data_el)
                    else:
                        value = [DataElementAttributeProxy(mb_el)
                                 for mb_el in nested_data_el.get_members()]
        return value
