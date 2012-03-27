"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Resource attribute handling classes.

Created on June 8, 2011.
"""

from everest.resources.attributes import get_resource_class_attributes
from everest.utils import OrderedDict

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
        cache = self.__mapped_attr_cache
        self._collect_mapped_attributes(cache, mapped_class, info)
        return cache[mapped_class]

    def _collect_mapped_attributes(self, cache, mapped_class, info):
        if info is None:
            info = {}
        else:
            # Discard the cache if we have dynamic mapping info.
            cache.pop(mapped_class, None)
        mapped_attrs = OrderedDict()
        attrs = get_resource_class_attributes(mapped_class)
        for attr in attrs.values():
            map_options = self.__config.get_mapping(attr.name)
#            if attr.kind == ResourceAttributeKinds.COLLECTION \
#               and map_options['ignore'] is None:
#                # By default, ignore if attribute references root collection.
#                map_options['ignore'] = not attr.is_nested
            # Apply custom settings for this attribute.
            runtime_map_options = info.get(attr.name, {})
            map_options.update(runtime_map_options)
            mapped_attr = MappedAttribute(attr.name,
                                          attr.kind,
                                          attr.value_type,
                                          entity_name=attr.entity_name,
                                          **map_options)
            mapped_attrs[attr.name] = mapped_attr
        cache[mapped_class] = mapped_attrs


class MemberAttributeMapper(_AttributeMapper):
    pass


class CollectionAttributeMapper(_AttributeMapper):
    pass


class LinkAttributeMapper(_AttributeMapper):
    pass

