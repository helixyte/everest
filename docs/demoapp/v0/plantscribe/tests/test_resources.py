"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 9, 2012.
"""

from StringIO import StringIO
from everest.resources.io import dump_resource
from everest.resources.utils import get_root_collection
from everest.testing import ResourceTestCase
from everest.utils import get_repository_manager
from pkg_resources import resource_filename # pylint: disable=E0611
from plantscribe.interfaces import ICustomer
from plantscribe.interfaces import IProject
from plantscribe.interfaces import ISpecies
from plantscribe.resources.customer import CustomerMember
from plantscribe.resources.incidence import IncidenceMember
from plantscribe.resources.project import ProjectMember
from plantscribe.resources.site import SiteMember
from plantscribe.resources.species import SpeciesMember
import os
from everest.repository import REPOSITORIES
from everest.mime import CsvMime
from everest.resources.utils import get_collection_class
from plantscribe.interfaces import IIncidence
from plantscribe.interfaces import ISite

__docformat__ = 'reStructuredText en'
__all__ = ['PlantScribeResourcesFsTestCase',
           'PlantScribeResourcesOrmTestCase',
           ]


class _PlantScribeResourcesBaseTestCase(ResourceTestCase):
    package_name = 'plantscribe.tests'
    ini_section_name = 'app:plantscribe'
    def test_get_customer(self):
        coll = get_root_collection(ICustomer)
        self.assert_equal(len(coll), 2)
        mb = coll.get('smith-peter')
        self.assert_true(isinstance(mb, CustomerMember))
        self.assert_equal(mb.first_name, 'Peter')
        self.assert_equal(mb.last_name, 'Smith')
        self.assert_equal(len(mb.projects), 2)

    def test_get_project(self):
        coll = get_root_collection(IProject)
        self.assert_equal(len(coll), 2)
        mb = coll.get('pond')
        self.assert_true(isinstance(mb, ProjectMember))
        self.assert_equal(mb.name, 'Pond')
        self.assert_true(isinstance(mb.customer, CustomerMember))

    def test_get_species(self):
        coll = get_root_collection(ISpecies)
        self.assert_equal(len(coll), 6)
        mb = coll.get('caltha-palustris--l.')
        self.assert_true(isinstance(mb, SpeciesMember))
        self.assert_equal(mb.species_name, 'palustris')
        self.assert_equal(mb.genus_name, 'Caltha')
        self.assert_equal(mb.author, 'L.')

    def test_get_nested(self):
        coll = get_root_collection(IProject)
        mb = coll.get('pond')
        self.assert_equal(len(mb.sites), 2)
        site_mb = mb.sites.get('open-water')
        self.assert_true(isinstance(site_mb, SiteMember))
        incidence_mb = site_mb.incidences.get('utricularia-vulgaris--l.')
        self.assert_true(isinstance(incidence_mb, IncidenceMember))

    def test_dump(self):
        prjs = get_root_collection(IProject)
        prj = prjs.get('pond')
        stream = StringIO('w')
        dump_resource(prj, stream)
        self.assert_true(len(stream.getvalue()) > 0)


class PlantScribeResourcesFsTestCase(_PlantScribeResourcesBaseTestCase):
    ini_file_path = resource_filename('plantscribe.tests',
                                      'plantscribe_fs.ini')


class PlantScribeResourcesOrmTestCase(_PlantScribeResourcesBaseTestCase):
    ini_file_path = resource_filename('plantscribe.tests',
                                      'plantscribe_orm.ini')

    def set_up(self):
        _PlantScribeResourcesBaseTestCase.set_up(self)
        #
        repo_mgr = get_repository_manager()
        repo = repo_mgr.get(REPOSITORIES.ORM)
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        for coll_name, coll_cls in \
                (('customer', get_collection_class(ICustomer)),
                 ('project', get_collection_class(IProject)),
                 ('site', get_collection_class(ISite)),
                 ('species', get_collection_class(ISpecies)),
                 ('incidence', get_collection_class(IIncidence)),
                 ):
            url = 'file://%s' % os.path.join(data_dir,
                                             '%s-collection.csv' % coll_name)
            repo.load_representation(coll_cls, url,
                                     content_type=CsvMime, resolve_urls=True)
