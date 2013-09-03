"""
Data elements.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 25, 2012
"""
from collections import OrderedDict
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.constants import RESOURCE_KINDS
from everest.representers.converters import SimpleConverterRegistry
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.representers.interfaces import IResourceDataElement
from everest.representers.utils import data_element_tree_to_string
from everest.resources.utils import provides_collection_resource
from everest.resources.utils import provides_member_resource
from everest.resources.utils import resource_to_url
from pyramid.compat import iteritems_
from zope.interface import implementer # pylint: disable=E0611,F0401
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['CollectionDataElement',
           'DataElement',
           'DataElementAttributeProxy',
           'LinkedDataElement',
           'MemberDataElement',
           'SimpleCollectionDataElement',
           'SimpleLinkedDataElement',
           'SimpleMemberDataElement',
           ]


@implementer(IResourceDataElement)
class DataElement(object):
    """
    Abstract base class for data element classes.

    Data elements manage value state during serialization and deserialization.
    Implementations may need to be adapted to the format of the external
    representation they manage.
    """

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


@implementer(IMemberDataElement)
class MemberDataElement(DataElement):
    """
    Abstract base class for member data element classes.
    """

    #: Registry of representation string <-> value converters. To be set
    #: in derived classes.
    converter_registry = None

    def get_terminal(self, attr):
        """
        Returns the value for the given mapped terminal resource attribute.

        :param attr: attribute to retrieve.
        :type attr: :class:`everest.representers.attributes.MappedAttribute`
        :returns: attribute value or `None` if no value is found for the given
            attribute name.
        """
        raise NotImplementedError('Abstract method.')

    def set_terminal(self, attr, value):
        """
        Sets the value for the given mapped terminal resource attribute.

        :type attr: :class:`everest.representers.attributes.MappedAttribute`
        :param value: value of the attribute to set.
        """
        raise NotImplementedError('Abstract method.')

    def get_nested(self, attr):
        """
        Returns the mapped nested resource attribute (either a member or a
        collection resource attribute).

        :type attr: :class:`everest.representers.attributes.MappedAttribute`
        :returns: object implementing `:class:IDataelement` or
          `None` if no nested resource is found for the given attribute name.
        """
        raise NotImplementedError('Abstract method.')

    def set_nested(self, attr, data_element):
        """
        Sets the value for the given mapped nested resource attribute (either
        a member or a collection resource attribute).

        :type attr: :class:`everest.representers.attributes.MappedAttribute`
        :param data_element: a :class:DataElement or :class:LinkedDataElement
          object containing nested resource data.
        """
        raise NotImplementedError('Abstract method.')


@implementer(ICollectionDataElement)
class CollectionDataElement(DataElement):
    """
    Abstract base class for collection data elements.
    """

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
    converter_registry = SimpleConverterRegistry

    __data = None

    @property
    def data(self):
        if self.__data is None:
            self.__data = OrderedDict()
        return self.__data

    @property
    def terminals(self):
        if self.__data is None:
            self.__data = OrderedDict()
        return OrderedDict((k, v)
                           for (k, v) in iteritems_(self.__data)
                           if not isinstance(v, DataElement))

    @property
    def nesteds(self):
        if self.__data is None:
            self.__data = OrderedDict()
        return OrderedDict((k, v)
                           for (k, v) in iteritems_(self.__data)
                           if isinstance(v, DataElement))

    def get_nested(self, attr):
        return self.data.get(attr.repr_name)

    def set_nested(self, attr, data_element):
        self.data[attr.repr_name] = data_element

    def get_terminal(self, attr):
        return self.data.get(attr.repr_name)

    def set_terminal(self, attr, value):
        self.data[attr.repr_name] = value

    def get_terminal_converted(self, attr):
        """
        Returns the value of the specified attribute converted to a 
        representation value.
        
        :param attr: attribute to retrieve.
        :type attr: :class:`everest.representers.attributes.MappedAttribute`
        :returns: representation string
        """
        value = self.data.get(attr.repr_name)
        return self.converter_registry.convert_to_representation(
                                                            value,
                                                            attr.value_type)

    def set_terminal_converted(self, attr, repr_value):
        """
        Converts the given representation value and sets the specified 
        attribute value to the converted value. 

        :param attr: attribute to set.
        :param str repr_value: string value of the attribute to set.
        """
        value = self.converter_registry.convert_from_representation(
                                                            repr_value,
                                                            attr.value_type)
        self.data[attr.repr_name] = value


class SimpleCollectionDataElement(_SimpleDataElementMixin,
                                  CollectionDataElement):
    """
    Basic implementation of a collection data element.
    """
    __members = None

    def add_member(self, data_element):
        self.members.append(data_element)

    def get_members(self):
        return self.members

    @property
    def members(self):
        if self.__members is None:
            self.__members = []
        return self.__members

    def __len__(self):
        return len(self.__members)


@implementer(ILinkedDataElement)
class LinkedDataElement(DataElement):
    """
    Data element managing a linked resource during serialization and
    deserialization.
    """

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
        # pylint: disable=W0212
        inst.__url = url
        inst.__kind = kind
        inst.__relation = relation
        inst.__title = title
        # pylint: enable=W0212
        return inst

    @classmethod
    def create_from_resource(cls, resource):
        if provides_member_resource(resource):
            kind = RESOURCE_KINDS.MEMBER
        elif provides_collection_resource(resource):
            kind = RESOURCE_KINDS.COLLECTION
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
    """
    Convenience proxy for accessing data from data elements.
    
    The proxy allows you to transparently access terminal, member, and
    collection attributes. Nested access is also supported.
    
    Example: ::
    
       prx = DataElementAttributeProxy(data_element)
       de_id = prx.id                              # terminal access
       de_parent = prx.parent                      # member access
       de_child = prx.children[0]                  # collection access
       de_grandchild = prx.children[0].children[0] # nested collection access
    """
    def __init__(self, data_element):
        if ILinkedDataElement in provided_by(data_element):
            raise ValueError('Do not use data element proxies with linked '
                             'data elements.')
        attrs = data_element.mapping.attribute_iterator()
        self.__attr_map = dict([(attr.repr_name, attr) for attr in attrs])
        self.__data_element = data_element

    def get_data_element(self):
        """
        Returns the wrapped data element. Useful for proxies returned from
        accessing nested attributes.
        """
        return self.__data_element

    def __getattr__(self, name):
        try:
            attr = self.__attr_map[name]
        except KeyError:
            raise AttributeError(name)
        else:
            if attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                value = self.__data_element.get_terminal(attr)
            else:
                nested_data_el = self.__data_element.get_nested(attr)
                if nested_data_el is None:
                    value = None
                elif ILinkedDataElement in provided_by(nested_data_el):
                    value = nested_data_el # links are returned as-is.
                elif attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
                    value = DataElementAttributeProxy(nested_data_el)
                else:
                    value = [DataElementAttributeProxy(mb_el)
                             for mb_el in nested_data_el.get_members()]
        return value

    def __setattr__(self, name, value):
        # Avoid recursion for setting instance data during constructor call.
        if name in ['_DataElementAttributeProxy__data_element',
                    '_DataElementAttributeProxy__attr_map']:
            self.__dict__[name] = value
        else:
            try:
                attr = self.__attr_map[name]
            except KeyError:
                raise AttributeError(name)
            else:
                if attr.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                    self.__data_element.set_terminal(attr, value)
                else:
                    if not (isinstance(value, DataElement) or value is None):
                        raise ValueError('Need a data element or None as '
                                         'attribute value.')
                    self.__data_element.set_nested(attr, value)
