"""

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 1, 2014.
"""
import os
import sys

from pkg_resources import resource_filename # pylint: disable=E0611
import pkg_resources
import pytest


__docformat__ = 'reStructuredText en'
__all__ = ['TestPlugin',
           ]


@pytest.fixture(scope='class')
def prepare_plugin_path(request):
    plugin_path = os.path.join(os.path.dirname(__file__), 'plugin')
    sys.path.append(plugin_path)
    pkg_resources.working_set.add_entry(plugin_path)
    def cleanup():
        sys.path.remove(plugin_path)
        # Try to restore the original state of the working set.
        # FIXME: This relies on undocumented attributes of the WorkingSet
        #        class and may break in the future.
        pkg_resources.working_set.entries.remove(plugin_path)
        del pkg_resources.working_set.entry_keys[plugin_path]
        del pkg_resources.working_set.by_key['everest-myplugin']
    request.addfinalizer(cleanup)


@pytest.mark.usefixtures('prepare_plugin_path')
class TestPlugin(object):
    package_name = 'everest.tests.complete_app'
    ini_file_path = resource_filename('everest.tests.complete_app',
                                      'complete_app.ini')
    app_name = 'complete_app'

    def test_view(self, app_creator):
        from everest_myplugin.interfaces import IMyEntityGrandparent # pylint:disable=F0401
        from everest_myplugin.entities import MyEntityGrandparent # pylint:disable=F0401
        get_utility = app_creator.config.get_registered_utility
        assert get_utility(IMyEntityGrandparent, 'entity-class') is \
               MyEntityGrandparent
