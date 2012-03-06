"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Mar 2, 2012.
"""

from everest.representers.base import LazyAttributeLoaderProxy
from everest.representers.base import LazyUrlLoader
from everest.resources.utils import get_root_collection
from everest.testing import ResourceTestCase
from everest.tests.testapp_db.entities import MyEntity
from everest.tests.testapp_db.interfaces import IMyEntity
from everest.tests.testapp_db.resources import MyEntityParentMember
from everest.url import url_to_resource
from everest.tests.testapp_db.interfaces import IMyEntityParent
from everest.tests.testapp_db.entities import MyEntityParent

__docformat__ = 'reStructuredText en'
__all__ = ['LazyAttribteLoaderProxyTestCase',
           ]


class LazyAttribteLoaderProxyTestCase(ResourceTestCase):
    package_name = 'everest.tests.testapp_db'
    config_file_name = 'configure_no_orm.zcml'

    def test_lazy_loading(self):
        loader = LazyUrlLoader('http://localhost/my-entity-parents/0',
                               url_to_resource)
        my_entity = LazyAttributeLoaderProxy.create(MyEntity,
                                                    dict(id=0,
                                                         parent=loader))
        self.assert_true(isinstance(my_entity, LazyAttributeLoaderProxy))
        coll = get_root_collection(IMyEntity)
        mb = coll.create_member(my_entity)
        del my_entity
        # When the dynamically loaded parent is not found, the parent attribute
        # will be None; once it is in the root collection, resolving works.
        self.assert_is_none(mb.parent)
        my_parent = MyEntityParent(id=0)
        coll = get_root_collection(IMyEntityParent)
        coll.create_member(my_parent)
        self.assert_true(isinstance(mb.parent, MyEntityParentMember))
        self.assert_true(isinstance(mb.parent.get_entity(),
                                    MyEntityParent))
        # The entity class reverts back to MyEntity once loading completed
        # successfully.
        self.assert_false(isinstance(mb.parent.get_entity(),
                                     LazyAttributeLoaderProxy))
