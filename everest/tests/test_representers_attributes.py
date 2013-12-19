"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Oct 20, 2013.
"""
from everest.representers.attributes import MappedAttribute
from everest.representers.attributes import MappedAttributeKey
from everest.representers.config import IGNORE_OPTION
from everest.resources.descriptors import terminal_attribute
from everest.testing import Pep8CompliantTestCase
from everest.tests.complete_app.resources import MyEntityChildMember
from everest.tests.complete_app.resources import MyEntityMember

__docformat__ = 'reStructuredText en'
__all__ = ['AttributeKeyTestCase',
           ]


class MappedAttributeTestCase(Pep8CompliantTestCase):
    def test_invalid_kind(self):
        attr = terminal_attribute(str, 'foo')
        attr.kind = 'INVALID'
        mp_attr = MappedAttribute(attr, options={IGNORE_OPTION:None})
        key = MappedAttributeKey(())
        self.assert_raises(ValueError, mp_attr.should_ignore, key)


class AttributeKeyTestCase(Pep8CompliantTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_rpr.zcml'

    def set_up(self):
        Pep8CompliantTestCase.set_up(self)
        self.data = {('children',) : True,
                     ('children', 'children') : True}

    def test_iteration(self):
        key = MappedAttributeKey((MyEntityMember.children,
                                    MyEntityChildMember.children))
        self.assert_true(next(iter(key)) is MyEntityMember.children)
        self.assert_true(key[1] is MyEntityChildMember.children)
        self.assert_equal(len(key), 2)

    def test_attribute_key_pop(self):
        key = MappedAttributeKey((MyEntityMember.children,))
        attr = key.pop()
        self.assert_equal(attr.resource_attr, 'children')
        self.assert_raises(KeyError, self.data.__getitem__, key)

    def test_attribute_key_append(self):
        key = MappedAttributeKey((MyEntityMember.children,))
        key.append(MyEntityChildMember.children)
        self.assert_true(self.data[key] is True)

    def test_add(self):
        key = MappedAttributeKey((MyEntityMember.children,)) \
              + (MyEntityChildMember.children,)
        self.assert_true(self.data[key] is True)


