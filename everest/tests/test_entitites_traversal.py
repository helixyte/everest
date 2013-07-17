"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 12, 2013.
"""
from everest.entities.attributes import get_domain_class_attribute
from everest.entities.base import Entity
from everest.entities.traversal import DomainTreeTraverser
from everest.entities.traversal import SourceTargetDomainTraverser
from everest.entities.utils import get_root_aggregate
from everest.repositories.memory.cache import EntityCacheMap
from everest.testing import EntityTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.testing import create_entity
from mock import MagicMock
from mock import call

__docformat__ = 'reStructuredText en'
__all__ = ['DomainTreeTraverserTestCase',
           'SourceTargetDomainTraverserTestCase',
           ]


class DomainTreeTraverserTestCase(EntityTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_traverse_with_entity(self):
        mock_vst = MagicMock()
        ent = create_entity()
        trv = DomainTreeTraverser(ent)
        trv.run(mock_vst)
        self.assert_equal(mock_vst.mock_calls[-1],
                          call.visit_entity([], None, ent))

    def test_traverse_with_aggregate(self):
        mock_vst = MagicMock()
        ent = create_entity()
        attr = get_domain_class_attribute(ent, 'children')
        rel = attr.make_relationship(ent)
        agg = get_root_aggregate(IMyEntity).make_relationship_aggregate(rel)
        trv = DomainTreeTraverser(agg)
        trv.run(mock_vst)
        self.assert_equal(mock_vst.mock_calls[-1],
                          call.visit_aggregate([], None, agg))

    def test_dispatch_illegal_attr(self):
        mock_vst = MagicMock()
        ent = create_entity()
        trv = DomainTreeTraverser(ent)
        term_attr = get_domain_class_attribute(MyEntity, 'number')
        self.assert_raises(ValueError, trv._dispatch, [], # pylint: disable=W0212
                           term_attr, ent, mock_vst)
        self.assert_equal(mock_vst.mock_calls, [])

    def test_run_with_illegal_root_object_fails(self):
        illegal = object()
        trv = DomainTreeTraverser(illegal)
        self.assert_raises(ValueError, trv.run, illegal)


class SourceTargetDomainTraverserTestCase(EntityTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'

    def test_traverse_with_create(self):
        mock_vst = MagicMock()
        ent = create_entity(entity_id=None)
        session = EntityCacheMap()
        trv = SourceTargetDomainTraverser(session, ent, None)
        trv.run(mock_vst)
        parent_attr = get_domain_class_attribute(MyEntity, 'parent')
        children_attr = get_domain_class_attribute(MyEntity, 'children')
        grandchildren_attr = get_domain_class_attribute(MyEntityChild,
                                                        'children')
        # Check the visiting sequence and args (depth first).
        for idx, (meth_name, attr) \
            in enumerate([('visit_one', parent_attr),
                          ('visit_one', grandchildren_attr),
                          ('visit_many', grandchildren_attr),
                          ('visit_one', children_attr),
                          ('visit_many', children_attr),
                          ]):
            meth_call = mock_vst.method_calls[idx]
            self.assert_equal(meth_call[0], meth_name)
            self.assert_equal(meth_call[1][1], attr)
            if meth_name == 'visit_one':
                self.assert_true(isinstance(meth_call[1][2], Entity))
            else:
                self.assert_true(isinstance(meth_call[1][2], list))
            self.assert_is_none(meth_call[1][3])

        #
#        self.assert_true(ent in session)
#        self.assert_true(ent.parent in session)
#        self.assert_true(ent.children[0] in session)
#        self.assert_true(ent.children[0].children[0] in session)
