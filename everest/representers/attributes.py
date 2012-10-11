"""
Mapped resource attributes.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on June 8, 2011.
"""
from everest.representers.config import IGNORE_ON_READ_OPTION
from everest.representers.config import IGNORE_ON_WRITE_OPTION
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import REPR_NAME_OPTION
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.descriptors import CARDINALITY

__docformat__ = 'reStructuredText en'
__all__ = ['AttributeKey',
           'MappedAttribute',
           ]


class AttributeKey(object):
    """
    Value object used as a key during resource data tree traversal.
    
    Each key consists of a tuple of attribute strings that uniquely 
    determine a node's position in the resource data tree.
    """
    def __init__(self, data):
        self.__data = tuple(data)
        self.offset = 0

    def __hash__(self):
        return hash(self.__data)

    def __eq__(self, other):
        return self.__data == tuple(other)

    def __getitem__(self, index):
        return self.__data.__getitem__(index)

    def __len__(self):
        return len(self.__data)

    def __add__(self, other):
        return AttributeKey(self.__data + tuple(other))

    def __str__(self):
        return 'AttributeKey(%s, %d)' % (self.__data, self.offset)


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
            options[REPR_NAME_OPTION] = attr.name
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

    def should_ignore(self, ignore_option_name, attribute_key):
        """
        Checks if the given attribute key should be ignored for the given
        ignore option name.
        
        Rules for ignoring attributes:
         * always ignore when IGNORE_ON_XXX_OPTION is set to True;
         * always include when IGNORE_ON_XXX_OPTION is set to False;
         * also ignore member attributes when the length of the attribute
           key is > 0 or the cardinality is not MANYTOONE (this avoids
           traversing circular attribute definitions such as parent ->
           children -> parent);
         * also ignore collection attributes when the cardinality is 
           not MANYTOMANY.
           
        :ignore_option_name: configuration option name (IGNORE_ON_READ_OPTION
          or IGNORE_ON_WRITE_OPTION).
        :param attribute_key: :class:`AttributeKey` instance.
        """
        option_value = self.options.get(ignore_option_name)
        do_ignore = option_value
        if option_value is None:
            if self.kind == ResourceAttributeKinds.MEMBER:
                depth = len(attribute_key) + 1 - attribute_key.offset
                do_ignore = depth > 1 \
                            or self.cardinality != CARDINALITY.MANYTOONE
            elif self.kind == ResourceAttributeKinds.COLLECTION:
                do_ignore = self.cardinality != CARDINALITY.MANYTOMANY
        return do_ignore

    @property
    def name(self):
        return self.__attr.name

    @property
    def kind(self):
        return self.__attr.kind

    @property
    def value_type(self):
        return self.__attr.value_type

    @property
    def entity_name(self):
        return self.__attr.entity_name

    @property
    def cardinality(self):
        return self.__attr.cardinality

    def __getattr__(self, attr_name):
        # Make options available as attributes.
        if attr_name in self.options:
            return self.options.get(attr_name)
        else:
            raise AttributeError(attr_name)

    def __str__(self):
        return '%s(%s -> %s, type %s)' % \
               (self.__class__.__name__, self.name, self.repr_name, self.kind)
