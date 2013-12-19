"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 21, 2011.
"""

from everest.testing import EverestIni
from everest.testing import Pep8CompliantTestCase
from shutil import rmtree
from tempfile import mkdtemp
from tempfile import mktemp
from everest.compat import open_text

__docformat__ = 'reStructuredText en'
__all__ = []


INI = """\
[DEFAULT]
db_server = my_db_server
db_port = 5432
db_user = my_db_user
db_password = pwd123
db_name = my_db_name

[app:mysimple_app]
db_string = postgresql://%(db_user)s:%(db_password)s@%(db_server)s:%(db_port)s/%(db_name)s
db_echo = false
"""

class TestingTestCase(Pep8CompliantTestCase):
    ini_section_name = 'app:mysimple_app'

    def set_up(self):
        self.__testdir = mkdtemp()
        fn = mktemp(suffix="ini", dir=self.__testdir)
        ini_file = open_text(fn)
        ini_file.write(INI)
        ini_file.close()
        self.ini_file_path = fn

    def tear_down(self):
        rmtree(self.__testdir)

    def test_ini_file_read(self):
        ini = EverestIni(self.ini_file_path)
        ini_marker = self.ini_section_name
        db_string = ini.get_setting(ini_marker, 'db_string')
        self.assert_equal(
                db_string,
                'postgresql://my_db_user:pwd123@my_db_server:5432/my_db_name')
