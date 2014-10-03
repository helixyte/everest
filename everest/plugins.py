"""

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 1, 2014.
"""
from pkg_resources import iter_entry_points

from zope.interface import Interface # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['IPluginManager',
           'PluginManager',
           ]


class IPluginManager(Interface):
    """
    Marker interface for the plugin manager utility.
    """


class PluginManager(object):
    """
    Simple plugin manager for everest applications.
    """
    def __init__(self, config):
        self.__config = config

    def load_all(self, group):
        """
        Loads all plugins advertising entry points with the given group name.
        The specified plugin needs to be a callable that accepts the everest
        configurator as single argument.
        """
        for ep in iter_entry_points(group=group):
            plugin = ep.load()
            plugin(self.__config)
