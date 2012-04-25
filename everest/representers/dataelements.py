"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Data element classes.

Created on Apr 25, 2012
"""

from everest.representers.attributes import CollectionAttributeMapper
from everest.representers.attributes import LinkAttributeMapper
from everest.representers.attributes import MemberAttributeMapper
from everest.representers.base import RepresenterConfiguration
from everest.representers.base import data_element_tree_to_string
from everest.representers.interfaces import ICollectionDataElement
from everest.representers.interfaces import IDataElementRegistry
from everest.representers.interfaces import ILinkedDataElement
from everest.representers.interfaces import IMemberDataElement
from everest.representers.interfaces import IResourceDataElement
from everest.resources.interfaces import ICollectionResource
from everest.resources.interfaces import IMemberResource
from everest.resources.interfaces import IResourceLink
from everest.resources.link import Link
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

    #: The class to be mapped to a representation.
    mapped_class = None
    #: Static attribute mapper.
    mapper = None

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
        Adds the given member data element to this data element.
        """
        raise NotImplementedError('Abstract method.')

    def get_members(self):
        """
        Returns all member data elements added to this data element.
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
        return getattr(self, attr.representation_name, None)

    def set_terminal(self, attr, value):
        setattr(self, attr.representation_name, value)

    def get_nested(self, attr):
        nested = self.__get_nested()
        return nested.get(attr.representation_name)

    def set_nested(self, attr, data_element):
        nested = self.__get_nested()
        nested[attr.representation_name] = data_element

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


class LinkedDataElement(object):
    """
    Data element managing a linked resource during serialization and
    deserialization.
    """

    implements(ILinkedDataElement)

    mapped_class = Link

    @classmethod
    def create(cls, linked_data_element_class, url,
               relation=None, title=None):
        raise NotImplementedError('Abstract method.')

    @classmethod
    def create_from_resource(cls, resource):
        raise NotImplementedError('Abstract method.')

    def get_url(self):
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
    __relation = None
    __title = None

    @classmethod
    def create(cls, linked_data_element_class, url,
               relation=None, title=None):
        inst = cls()
        inst.__url = url
        inst.__relation = relation
        inst.__title = title
        return inst

    @classmethod
    def create_from_resource(cls, resource):
        return cls.create(None, resource_to_url(resource),
                          relation=resource.relation,
                          title=resource.title)

    def get_url(self):
        return self.__url

    def get_relation(self):
        return self.__relation

    def get_title(self):
        return self.__title


class DataElementRegistry(object):

    implements(IDataElementRegistry)

    member_data_element_base_class = None
    collection_data_element_base_class = None
    linked_data_element_base_class = None
    configuration_class = None

    def __init__(self):
        self.__de_map = {}
        # Perform static initializations.
        self._initialize()

    def create_data_element_class(self, mapped_class, configuration,
                                  base_class=None):
        """
        Creates a new data element class for the given mapped class and
        representer configuration.

        :param configuration: configuration for the new data element class.
        :type configuration: :class:`RepresenterConfiguration`
        :returns: new type implementing :class:`IDataElement`
        """
        if configuration is None:
            configuration = self.configuration_class() # pylint: disable=E1102
        provided_ifcs = provided_by(object.__new__(mapped_class))
        if IMemberResource in provided_ifcs:
            if base_class is None:
                base_class = self.member_data_element_base_class
            mapper = MemberAttributeMapper(configuration)
        elif ICollectionResource in provided_ifcs:
            if base_class is None:
                base_class = self.collection_data_element_base_class
            mapper = CollectionAttributeMapper(configuration)
        elif IResourceLink in provided_ifcs:
            if base_class is None:
                base_class = self.linked_data_element_base_class
            mapper = LinkAttributeMapper(configuration)
        else:
            raise ValueError('Mapped class for data element class does not '
                             'implement one of the required interfaces.')
        name = "%s%s" % (mapped_class.__name__, base_class.__name__)
        custom_de_cls = type(name, (base_class,), {})
        custom_de_cls.mapper = mapper
        custom_de_cls.mapped_class = mapped_class
        return custom_de_cls

    def set_data_element_class(self, data_element_class):
        """
        Registers the given data element class.

        :param data_element_class: type implementing :class:`IDataElement`
        :type data_element_class: type
        """
        if self.__de_map.has_key(data_element_class.mapped_class):
            raise ValueError('Class "%s" has already been registered.'
                             % data_element_class.mapped_class)
        self.__de_map[data_element_class.mapped_class] = data_element_class

    def get_data_element_class(self, mapped_class):
        """
        Returns the data element class registered for the given mapped class.

        :param mapped_class: mapped type
        :type mapped_class: type
        :returns: type implementing :class:`IDataElement`
        """
        de_cls = None
        for base_cls in mapped_class.__mro__:
            try:
                de_cls = self.__de_map[base_cls]
            except KeyError:
                continue
            else:
                break
        if de_cls is None:
            de_cls = self.create_data_element_class(mapped_class, None)
            self.__de_map[mapped_class] = de_cls
        return de_cls

    def get_data_element_classes(self):
        """
        Returns a list of all registered data element classes.

        :returns: list of types implementing :class:`IDataElement`
        """
        return self.__de_map.iteritems()

    def _initialize(self):
        # Implement this for static initializations.
        raise NotImplementedError('Abstract method.')


class SimpleDataElementRegistry(DataElementRegistry):
    member_data_element_base_class = SimpleMemberDataElement
    collection_data_element_base_class = SimpleCollectionDataElement
    linked_data_element_base_class = SimpleLinkedDataElement
    configuration_class = RepresenterConfiguration

    def _initialize(self):
        # Create and register the linked data element class.
        configuration = self.configuration_class()
        mapped_class = self.linked_data_element_base_class.mapped_class
        de_cls = self.create_data_element_class(
                                mapped_class,
                                configuration,
                                base_class=self.linked_data_element_base_class)
        self.set_data_element_class(de_cls)

