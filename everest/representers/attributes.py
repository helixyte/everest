"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Resource attribute handling classes.

Created on June 8, 2011.
"""

from everest.resources.attributes import get_resource_class_attributes
from everest.utils import OrderedDict
from copy import deepcopy

__docformat__ = 'reStructuredText en'
__all__ = ['CollectionAttributeMapper',
           'LinkAttributeMapper',
           'MappedAttribute',
           'MemberAttributeMapper',
           ]


class MappedAttribute(object):
    """
    Represents an attribute mapped from a class into a representation.

    This is a simple value object.
    """
    def __init__(self, name, kind, value_type, entity_name=None, **options):
        """
        :param str name: The attribute name.
        :param str kind: The attribute kind. One of the constants
          defined in :class:`ResourceAttributeKinds`.
        """
        self.name = name
        self.kind = kind
        self.value_type = value_type
        self.entity_name = entity_name
        # Make sure we have a valid representation name.
        representation_name = options.pop('repr_name', None)
        if representation_name is None:
            representation_name = name
        self.representation_name = representation_name
        # All other options are made available as attributes.
        for option_name, option_value in options.iteritems():
            setattr(self, option_name, option_value)

    def __str__(self):
        return '%s(%s -> %s, type %s)' % \
               (self.__class__.__name__, self.name,
                self.representation_name, self.kind)


class _AttributeMapper(object):
    """
    Performs attribute mapping between a mapped class and its representation.
    
    Attribute mappers have a static configuration which can be overridden at
    runtime.
    """

    def __init__(self, configuration):
        """
        :param configuration: representer configuration class
        """
        self.__mapped_attr_cache = {}
        self.__config = configuration

    def get_config_option(self, name):
        return self.__config.get_option(name)

    def set_config_option(self, name, value):
        self.__config.set_option(name, value)

    def get_mapped_attributes(self, mapped_class, info=None):
        if not mapped_class in self.__mapped_attr_cache:
            self._collect_mapped_attributes(mapped_class)
        attrs = self.__mapped_attr_cache[mapped_class]
        if not info is None:
            copied_attrs = deepcopy(attrs)
            for name, map_options in info.iteritems():
                attr = copied_attrs[name]
                for opt_name, opt_value in map_options.iteritems():
                    setattr(attr, opt_name, opt_value)
            result = copied_attrs
        else:
            result = attrs
        return result

    def _collect_mapped_attributes(self, mapped_class):
        mapped_attrs = OrderedDict()
        attrs = get_resource_class_attributes(mapped_class)
        for attr in attrs.values():
            map_options = self.__config.get_mapping(attr.name)
            mapped_attr = MappedAttribute(attr.name,
                                          attr.kind,
                                          attr.value_type,
                                          entity_name=attr.entity_name,
                                          **map_options)
            mapped_attrs[attr.name] = mapped_attr
        self.__mapped_attr_cache[mapped_class] = mapped_attrs


class MemberAttributeMapper(_AttributeMapper):
    pass


class CollectionAttributeMapper(_AttributeMapper):
    pass


class LinkAttributeMapper(_AttributeMapper):
    pass

