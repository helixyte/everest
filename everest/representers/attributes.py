"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Resource attribute handling classes.

Created on June 8, 2011.
"""
from everest.representers.config import IGNORE_ON_READ_OPTION
from everest.representers.config import IGNORE_ON_WRITE_OPTION
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import REPR_NAME_OPTION

__docformat__ = 'reStructuredText en'
__all__ = ['CollectionAttributeMapper',
           'LinkAttributeMapper',
           'MappedAttribute',
           'MemberAttributeMapper',
           ]


class MappedAttribute(object):
    """
    Represents an attribute mapped from a class into a representation.

    Wraps a (read-only) resource attribute and mapping options which can be
    configured dynamically.
    """
    def __init__(self, attr, options=None):
        """
        :param attr: The attribute name.
        :type attr: :class:`
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
