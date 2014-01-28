"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 14, 2012.
"""
from everest.resources.staging import create_staging_collection
from everest.resources.utils import get_registered_collection_resources
from everest.resources.utils import get_resource_class_for_relation
from everest.resources.utils import get_resource_url
from everest.resources.utils import provides_collection_resource
from everest.resources.utils import provides_member_resource
from everest.resources.utils import provides_resource
from everest.testing import ResourceTestCase
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.resources import MyEntityMember
from everest.tests.complete_app.testing import create_collection
from everest.tests.complete_app.testing import create_entity


__docformat__ = 'reStructuredText en'
__all__ = ['ResourcesUtilsTestCase',
           ]


class ResourcesUtilsTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_get_resource_url(self):
        coll = create_collection()
        url = get_resource_url(coll)
        self.assert_not_equal(url.find('/my-entities'), -1)

    def test_provides_resource(self):
        coll = create_collection()
        mb = next(iter(coll))
        self.assert_true(provides_member_resource(type(mb)))
        self.assert_true(provides_member_resource(mb))
        self.assert_false(provides_member_resource(coll))
        self.assert_true(provides_resource(type(mb)))
        self.assert_true(provides_resource(mb))
        self.assert_true(provides_collection_resource(type(coll)))
        self.assert_true(provides_collection_resource(coll))
        self.assert_false(provides_collection_resource(mb))
        self.assert_true(provides_resource(type(coll)))
        self.assert_true(provides_resource(coll))
        self.assert_false(provides_resource(mb.get_entity()))

    def test_get_registered_collection_resources(self):
        colls = get_registered_collection_resources()
        self.assert_equal(len(colls), 4)

    def test_get_resource_from_relation(self):
        rel = MyEntityMember.relation
        self.assert_equal(get_resource_class_for_relation(rel),
                          MyEntityMember)

    def test_new_stage_collection(self):
        ent = create_entity(entity_id=2, entity_text='too2')
        mb = MyEntityMember.create_from_entity(ent)
        nscoll = create_staging_collection(IMyEntity)
        self.assert_equal(len(nscoll), 0)
        nscoll.add(mb)
        self.assert_equal(len(nscoll), 1)
