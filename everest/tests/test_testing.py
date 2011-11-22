"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 21, 2011.
"""

from everest.testing import Pep8CompliantTestCase
from everest.testing import TestApp
from shutil import rmtree
from tempfile import mkdtemp
from tempfile import mktemp

__docformat__ = 'reStructuredText en'
__all__ = []


INI = """\
[DEFAULT]
db_server = my_db_server
db_port = 5432
db_user = my_db_user
db_password = pwd123
db_name = my_db_name

[app:mytestapp]
db_string = postgresql://%(db_user)s:%(db_password)s@%(db_server)s:%(db_port)s/%(db_name)s
db_echo = false
"""

class MyTestApp(TestApp):
    app_name = 'mytestapp'
    package_name = 'everest.tests.testapp'


class TestingTestCase(Pep8CompliantTestCase):
    __testdir = None

    test_app_cls = MyTestApp

    def set_up(self):
        self.__testdir = mkdtemp()
        fn = mktemp(suffix="ini", dir=self.__testdir)
        ini_file = open(fn, 'wb')
        ini_file.write(INI)
        ini_file.close()
        MyTestApp.app_ini_file_path = fn

    def tear_down(self):
        rmtree(self.__testdir)

    def test_ini_file_read(self):
        ini_parser = self.test_app_cls.read_ini_file()
        ini_marker = 'app:%s' % self.test_app_cls.app_name
        db_string = ini_parser.get(ini_marker, 'db_string')
        self.assert_equal(
                db_string,
                'postgresql://my_db_user:pwd123@my_db_server:5432/my_db_name')
