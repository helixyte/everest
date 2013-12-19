"""
Mapped resource attributes.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on June 8, 2011.
"""
from everest.compat import izip
from everest.constants import CARDINALITIES
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import REPR_NAME_OPTION
from everest.resources.interfaces import IResourceAttribute
from zope.interface import implementer # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['MappedAttribute',
           'MappedAttributeKey',
           ]


class MappedAttributeKey(object):
    """
    Value object used as a key during resource data tree traversal.

    Each key consists of a tuple of mapped attributes that uniquely
    determine a node's position in the resource data tree.
    """
    def __init__(self, attributes):
        self.attributes = list(attributes)
        self.names = self._make_names(attributes)

    def append(self, attribute):
        self.attributes.append(attribute)
        self.names = self.names + self._make_names((attribute,))

    def pop(self):
        attr = self.attributes.pop()
        self.names = self.names[:-1]
        return attr

    def __hash__(self):
        return hash(self.names)

    def __eq__(self, other):
        return all((left == right for (left, right)
                    in izip(self.names, other)))

    def __getitem__(self, index):
        return self.attributes.__getitem__(index)

    def __len__(self):
        return len(self.attributes)

    def __add__(self, other):
        return self.__class__(self.attributes + list(other))

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, '.'.join(self.names))

    def _make_names(self, attributes):
        return tuple([attr.resource_attr for attr in attributes])


@implementer(IResourceAttribute)
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
        self.options = options
        #
        self.__attr = attr

    def clone(self, options=None):
        if options is None:
            options = {}
        new_options = self.options.copy()
        new_options.update(options)
        return MappedAttribute(self.__attr, options=new_options)

    def should_ignore(self, attribute_key):
        """
        Checks if this attribute should be ignored for the given attribute
        key.

        Rules for ignoring attributes:
         * always ignore when IGNORE_OPTION is set to True;
         * always include when IGNORE_OPTION is set to False;
         * also ignore member attributes when the length of the attribute
           key is > 0;
         * also ignore collection attributes when the cardinality is
           not MANYTOMANY.

        :param attribute_key: mapped attribute key.
        """
        ignore_attr_value = getattr(self, IGNORE_OPTION)
        if ignore_attr_value is None:
            # If an IGNORE option was not set, we decide based on the "net"
            # nestedness of the attribute (distance to the nearest parent
            # attribute that was set to IGNORE=False).
            depth = len(attribute_key.attributes)
            offset = -1
            for offset, key_attr in enumerate(attribute_key.attributes):
                key_ignore_attr_value = getattr(key_attr, IGNORE_OPTION)
                if not key_ignore_attr_value is False:
                    break
            net_depth = depth + 1 - (offset + 1)
            if self.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
                do_ignore = net_depth > 1
            elif self.kind == RESOURCE_ATTRIBUTE_KINDS.COLLECTION:
                do_ignore = self.cardinality != CARDINALITIES.MANYTOMANY
            elif self.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                do_ignore = False
            else:
                raise ValueError('Invalid resource attribute kind "%s".'
                                 % self.kind)
        else:
            do_ignore = ignore_attr_value
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
