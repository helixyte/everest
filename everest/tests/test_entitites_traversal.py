"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 12, 2013.
"""
from everest.constants import RELATION_OPERATIONS
from everest.entities.attributes import get_domain_class_attribute
from everest.entities.base import Entity
from everest.entities.traversal import DomainDataTraversalProxy
from everest.testing import EntityTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.testing import create_entity
from everest.traversal import SourceTargetDataTreeTraverser
from mock import MagicMock

__docformat__ = 'reStructuredText en'
__all__ = ['SourceTargetDataTraverserTestCase',
           ]


class SourceTargetDataTraverserTestCase(EntityTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_traverse_with_add(self):
        mock_vst = MagicMock()
        ent = create_entity(entity_id=None)
        trv = SourceTargetDataTreeTraverser.make_traverser(
                                                    ent,
                                                    RELATION_OPERATIONS.ADD,
                                                    None)
        trv.run(mock_vst)
        parent_attr = get_domain_class_attribute(MyEntity, 'parent')
        children_attr = get_domain_class_attribute(MyEntity, 'children')
        grandchildren_attr = get_domain_class_attribute(MyEntityChild,
                                                        'children')
        # Check the visiting sequence and args (depth first).
        for idx, (meth_name, attr) \
            in enumerate([('visit', parent_attr),
                          ('visit', grandchildren_attr),
                          ('visit', children_attr),
                          ]):
            meth_call = mock_vst.method_calls[idx + 1]
            self.assert_equal(meth_call[0], meth_name)
            self.assert_equal(meth_call[1][1], attr)
            prx = meth_call[1][2]
            self.assert_true(isinstance(prx, DomainDataTraversalProxy))
            self.assert_true(isinstance(prx.get_entity(), Entity))
            self.assert_is_none(meth_call[1][3])

        #
#        session = EntityCacheMap()
#        self.assert_true(ent in session)
#        self.assert_true(ent.parent in session)
#        self.assert_true(ent.children[0] in session)
#        self.assert_true(ent.children[0].children[0] in session)
