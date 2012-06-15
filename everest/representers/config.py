"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 8, 2012.
"""
from collections import defaultdict

__docformat__ = 'reStructuredText en'
__all__ = ['RepresenterConfiguration',
           ]

# Configuration option name declarations.

_MAPPING_CONFIG_OPTION = 'mapping'
VALID_CONFIG_OPTIONS = []

IGNORE_OPTION = 'ignore' # deprecated
IGNORE_ON_READ_OPTION = 'ignore_on_read'
IGNORE_ON_WRITE_OPTION = 'ignore_on_write'
WRITE_AS_LINK_OPTION = 'write_as_link'
REPR_NAME_OPTION = 'repr_name'
VALID_MAPPING_OPTIONS = [IGNORE_ON_READ_OPTION,
                         IGNORE_ON_WRITE_OPTION,
                         WRITE_AS_LINK_OPTION,
                         REPR_NAME_OPTION,
                         ]


class RepresenterConfiguration(object):
    """
    Class maintaining representer configuration options.

    At present, this can also be used as base class for containers declaring 
    representer configuration data as static class attributes. However, this
    usage is discouraged and should be replaced with the new ZCML based
    declaration syntax.

    Representer configuration objects maintain two kinds of configuration
    data:
    
    1) Generic options. These can be any key:value pairs. Derived 
       classes need to declare valid options in the 
       :cvar:`_default_config_options` class variable. 
    
    2) Mapping options. These are kept in a dictionary mapping the mapped
       attribute name to a dictionary of mapping options. Valid mapping 
       option name for a given attribute are:

       repr_name :
         The name to use for this attribute in the representation.
       write_as_link :
         Write this mapped attribute as a link rather than as a full
         representation.
       ignore_on_read:
         Ignore this attribute when reading a representation.
       ignore_on_write:
         Ignore this attribute when writing a representation.
       ignore :
         Ignore this attribute when creating a representation. This is short
         for setting both ignore_on_read and ignore_on_write
            
       Derived classes may add more allowed mapping options; those must be 
       declared in the :cvar:`_default_mapping_options` class variable.
    """

    #: Default configuration option names (immutable).
    _default_config_options = {}
    #: Default mapping option names (immutable).
    _default_mapping_options = {IGNORE_ON_READ_OPTION:None,
                                IGNORE_ON_WRITE_OPTION:None,
                                WRITE_AS_LINK_OPTION:None,
                                REPR_NAME_OPTION:None}

    def __init__(self, options=None, mapping_options=None):
        # {generic config option name : option value}
        self.__options = self._default_config_options.copy()
        # {attr key : { attr name : {{option name : option value}}}
        self.__mapping_options = defaultdict(self._default_config_options.copy)
        self.__update(options, mapping_options)

    def copy(self):
        """
        Return a copy of this configuration.
        """
        return self.__class__(options=self.__options,
                              mapping_options=self.__mapping_options)

    def update(self, configuration):
        """
        Update this configuration with the given other configuration. Only
        not-None values will be overridden.
        """
        self.__update(configuration.get_options(),
                      configuration.get_mapping_options())

    def get_option(self, name):
        """
        Returns the value for the specified generic configuration option.

        :returns: configuration option value or `None`, if the option was not
          set.
        """
        self.__validate_option_name(name)
        return self.__options.get(name, None)

    def set_option(self, name, value):
        """
        Sets the specified generic configuration option to the given value.
        """
        self.__validate_option_name(name)
        self.__options[name] = value

    def get_options(self):
        """
        Returns a copy of the generic configuration options.
        """
        return self.__options.copy()

    def set_mapping_option(self, attribute_key, option_name, option_value):
        self.__validate_mapping_option_name(option_name)
        mp_options = self.__mapping_options.setdefault(attribute_key, {})
        mp_options[option_name] = option_value

    def get_mapping_option(self, attribute_key, option_name):
        self.__validate_mapping_option_name(option_name)
        return self.__mapping_options[attribute_key].get(option_name)

    def get_mapping_options(self, attribute_key=None):
        """
        Returns a copy of the mapping options for the given attribute name
        or a copy of all mapping options, if no attribute name is provided.
        All options that were not explicitly configured are given a default
        value of `None`.

        :param tuple attribute_key: tuple specifying an attribute path.
        :returns: mapping options dictionary (including default `None` values)
        """
        if attribute_key is None:
            opts = defaultdict(self._default_mapping_options.copy)
            for attr, mp_options in self.__mapping_options.iteritems():
                opts[attr].update(mp_options)
        else:
            opts = self._default_mapping_options.copy()
            attr_opts = self.__mapping_options[attribute_key]
            opts.update(attr_opts)
        return opts

    def __update(self, opts, mp_opts):
        if not opts is None:
            for option_name, option_value in opts.iteritems():
                if not option_value is None:
                    self.set_option(option_name, option_value)
        if not mp_opts is None:
            for attr_name, attr_mp_options in mp_opts.iteritems():
                for mp_opt_name, mp_opt_value in attr_mp_options.iteritems():
                    if not mp_opt_value is None:
                        self.set_mapping_option(attr_name,
                                                mp_opt_name, mp_opt_value)

    def __validate_option_name(self, name):
        if not (name in self._default_config_options.keys()
                or name == _MAPPING_CONFIG_OPTION):
            raise ValueError('Invalid configuration option name "%s" for '
                             '%s representer.' %
                             (name, self.__class__.__name__))

    def __validate_mapping_option_name(self, name):
        if not (name in self._default_mapping_options.keys()
                or name == IGNORE_OPTION):
            raise ValueError('Invalid mapping option name "%s" '
                             'for %s representer.'
                             % (name, self.__class__.__name__))
