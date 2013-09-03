"""
Mapped resource attributes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on June 8, 2011.
"""
from everest.constants import CARDINALITIES
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.representers.config import IGNORE_ON_READ_OPTION
from everest.representers.config import IGNORE_ON_WRITE_OPTION
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import REPR_NAME_OPTION
from itertools import izip

__docformat__ = 'reStructuredText en'
__all__ = ['AttributeKey',
           'MappedAttribute',
           ]


class AttributeKey(object):
    """
    Value object used as a key during resource data tree traversal.

    Each key consists of a tuple of mapped attributes that uniquely
    determine a node's position in the resource data tree.
    """
    def __init__(self, data):
        self.__data = list(data)
        self.names = self._make_names(data)

    def append(self, item):
        self.__data.append(item)
        self.names = self.names + self._make_names((item,))

    def pop(self):
        attr = self.__data.pop()
        self.names = self.names[:-1]
        return attr

    def __hash__(self):
        return hash(self.names)

    def __eq__(self, other):
        return all((left == right for (left, right)
                    in izip(self.names, other)))

    def __getitem__(self, index):
        return self.__data.__getitem__(index)

    def __len__(self):
        return len(self.__data)

    def __add__(self, other):
        return self.__class__(self.__data + list(other))

    def __str__(self):
        return 'AttributeKey(%s)' % '.'.join(self.names)

    def _make_names(self, data):
        raise NotImplementedError('Abstract method.')


class MappedAttributeKey(AttributeKey):
    def __init__(self, data):
        AttributeKey.__init__(self, data)
        self.offset = 0

    def _make_names(self, data):
        return tuple([attr.resource_attr for attr in data])

    def __str__(self):
        return 'MappedAttributeKey(%s, %d)' % ('.'.join(self.names),
                                               self.offset)


class ResourceAttributeKey(AttributeKey):
    def _make_names(self, data):
        return tuple([attr.resource_attr for attr in data])


class DomainAttributeKey(AttributeKey):
    def _make_names(self, data):
        return tuple([attr.entity_attr for attr in data])


class MappedAttribute(object):
    """
    Represents an attribute mapped from a class into a representation.

    Wraps a (read-only) resource attribute and mapping options which can be
    configured dynamically.
    """
    def __init__(self, attr, options=None):
        """
        :param attr: Resource attribute.
        """
        # Check given options.
        if options is None:
            options = {}
        # Make sure we have a valid representation name.
        if options.get(REPR_NAME_OPTION) is None:
            options[REPR_NAME_OPTION] = attr.resource_attr
        # Process the "ignore" option..
        do_ignore = options.get(IGNORE_OPTION)
        if not do_ignore is None:
            # The IGNORE option always overrides settings for IGNORE_ON_XXX.
            options[IGNORE_ON_READ_OPTION] = do_ignore
            options[IGNORE_ON_WRITE_OPTION] = do_ignore
        self.options = options
        #
        self.__attr = attr

    def clone(self, options=None):
        if options is None:
            options = {}
        new_options = self.options.copy()
        new_options.update(options)
        return MappedAttribute(self.__attr, options=new_options)

    def should_ignore(self, ignore_option, attribute_key):
        """
        Checks if the given attribute key should be ignored for the given
        ignore option name.

        Rules for ignoring attributes:
         * always ignore when IGNORE_ON_XXX_OPTION is set to True;
         * always include when IGNORE_ON_XXX_OPTION is set to False;
         * also ignore member attributes when the length of the attribute
           key is > 0;
         * also ignore collection attributes when the cardinality is
           not MANYTOMANY.

        :ignore_option: configuration option value.
        :param attribute_key: :class:`AttributeKey` instance.
        """
        do_ignore = ignore_option
        if ignore_option is None:
            if self.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
                depth = len(attribute_key) + 1 - attribute_key.offset
                do_ignore = depth > 1
            elif self.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION:
                do_ignore = self.cardinality != CARDINALITIES.MANYTOMANY
        return do_ignore

    @property
    def name(self):
        return self.__attr.resource_attr

    @property
    def kind(self):
        return self.__attr.kind

    @property
    def value_type(self):
        return self.__attr.attr_type

    @property
    def entity_name(self):
        return self.__attr.entity_attr

    @property
    def cardinality(self):
        return getattr(self.__attr, 'cardinality', None)

    @property
    def resource_attribute(self):
        return self.__attr

    def __getattr__(self, attr_name):
        if attr_name in self.options:
            # Make options available as attributes.
            attr_value = self.options.get(attr_name)
        else:
            # Fall back on underlying descriptor attributes.
            attr_value = getattr(self.__attr, attr_name)
        return attr_value

    def __str__(self):
        return '%s %s %s->%s' % \
               (self.__attr.attr_type.__name__, self.__attr.kind,
                self.__attr.resource_attr, self.options[REPR_NAME_OPTION])
