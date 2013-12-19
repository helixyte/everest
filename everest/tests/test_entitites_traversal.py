"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 12, 2013.
"""
from everest.constants import RELATION_OPERATIONS
from everest.entities.attributes import get_domain_class_attribute
from everest.entities.base import Entity
from everest.entities.traversal import AruVisitor
from everest.entities.traversal import DomainDataTraversalProxy
from everest.repositories.memory.cache import EntityCacheMap
from everest.resources.staging import StagingAggregate
from everest.resources.staging import create_staging_collection
from everest.testing import EntityTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.interfaces import IMyEntity
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
                                                    ent, None,
                                                    RELATION_OPERATIONS.ADD)
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

    def test_make_traverser_invalid_params(self):
        ent0 = create_entity(entity_id=None)
        ent1 = create_entity(entity_id=None)
        self.assert_raises(ValueError,
                           SourceTargetDataTreeTraverser.make_traverser,
                           ent0, ent1,
                           RELATION_OPERATIONS.ADD)
        self.assert_raises(ValueError,
                           SourceTargetDataTreeTraverser.make_traverser,
                           ent1, ent0,
                           RELATION_OPERATIONS.REMOVE)
        self.assert_raises(ValueError,
                           SourceTargetDataTreeTraverser.make_traverser,
                           ent0, None,
                           RELATION_OPERATIONS.UPDATE,
                           accessor=None)

    def test_make_traverser_update(self):
        ent0 = create_entity(entity_id=0)
        ent1 = create_entity(entity_id=None)
        agg = create_staging_collection(IMyEntity).get_aggregate()
        agg.add(ent0)
        agg.add(ent1)
        ent01 = create_entity(entity_id=0)
        ent11 = create_entity(entity_id=None)
        # With many as source and one as target.
        with self.assert_raises(ValueError) as cm:
            SourceTargetDataTreeTraverser.make_traverser(
                                                [ent01, ent1], ent0,
                                                RELATION_OPERATIONS.UPDATE,
                                                accessor=agg)
        self.assert_true(
                cm.exception.args[0].endswith('or both not be sequences.'))
        # Without target.
        trv = SourceTargetDataTreeTraverser.make_traverser(
                                                [ent01, ent11], None,
                                                RELATION_OPERATIONS.UPDATE,
                                                accessor=agg)
        self.assert_is_not_none(getattr(trv, '_tgt_prx'))

    def test_traverse_with_remove_sequence(self):
        ent0 = create_entity(entity_id=0)
        ent1 = create_entity(entity_id=None)
        cache = EntityCacheMap()
        agg = StagingAggregate(MyEntity, cache=cache)
        agg.add(ent0)
        agg.add(ent1)
        trv = SourceTargetDataTreeTraverser.make_traverser(
                                                None, [ent0, ent1],
                                                RELATION_OPERATIONS.REMOVE)
        vst = AruVisitor(MyEntity, remove_callback=cache.remove)
        trv.run(vst)
        self.assert_equal(len(list(iter(agg))), 0)
