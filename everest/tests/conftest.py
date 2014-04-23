"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 17, 2014.
"""
import glob
import os
import shutil

from pyramid.testing import setUp as set_up_testing
from pyramid.testing import tearDown as tear_down_testing
from pyramid.threadlocal import get_current_registry
import pytest

from everest.configuration import Configurator
from everest.tests import simple_app as package


__docformat__ = 'reStructuredText en'
__all__ = ['simple_config',
           ]


@pytest.fixture
def simple_config(request):
    set_up_testing()
    reg = get_current_registry()
    config = Configurator(registry=reg, package=package)
    config.setup_registry()
    request.addfinalizer(tear_down_testing)
    return config


@pytest.fixture
def data_dir(request):
    pkg_name = getattr(request.cls, 'package_name', None)
    return os.path.join(os.path.dirname(__file__), pkg_name.split('.')[-1],
                        'data')


@pytest.yield_fixture
def resource_repo_with_data(data_dir, resource_repo): # pylint: disable=W0621
    with CopyDataFilesContextManager(data_dir):
        yield resource_repo


class CopyDataFilesContextManager(object):
    def __init__(self, data_directory):
        self.__data_dir = data_directory

    def __enter__(self):
        orig_data_dir = os.path.join(self.__data_dir, 'original')
        for fn in glob.glob1(orig_data_dir, "*.csv"):
            shutil.copy(os.path.join(orig_data_dir, fn), self.__data_dir)
        return self.__data_dir

    def __exit__(self, ext_type, value, tb):
        for fn in glob.glob1(self.__data_dir, '*.csv'):
            os.unlink(os.path.join(self.__data_dir, fn))
