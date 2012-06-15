"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 7, 2012.
"""
from everest.representers.converters import ConverterRegistry
from everest.representers.converters import SimpleConverterRegistry
from everest.representers.interfaces import IRepresentationConverter
from everest.testing import Pep8CompliantTestCase
from zope.interface import classProvides as class_provides # pylint: disable=E0611,F0401

__docformat__ = 'reStructuredText en'
__all__ = ['RepresenterConverterTestCase',
           ]


class RepresenterConverterTestCase(Pep8CompliantTestCase):
    def test_registry(self):
        with self.assert_raises(ValueError) as cm:
            SimpleConverterRegistry.register(bool, MyConverter)
        self.assert_true(cm.exception.message.startswith('For %s' % bool))
        with self.assert_raises(ValueError) as cm:
            SimpleConverterRegistry.register(MyNumberType, MyInvalidConverter)
        self.assert_true(cm.exception.message.startswith('Converter class'))

    def test_default_converter(self):
        self.assert_equal(
                MyConverterRegistry.convert_from_representation('0', int), 0)
        setattr(MyConverterRegistry, '_ConverterRegistry__converters', None)
        self.assert_equal(
                MyConverterRegistry.convert_to_representation(0, int), '0')
        setattr(MyConverterRegistry, '_ConverterRegistry__converters', None)

    def test_bool_converter(self):
        self.assert_true(
            SimpleConverterRegistry.convert_from_representation('true', bool)
            is True)
        self.assert_true(
            SimpleConverterRegistry.convert_from_representation(None, bool)
            is None)
        self.assert_equal(
            SimpleConverterRegistry.convert_to_representation(True, bool),
            'true')


class MyNumberType(int):
    pass


class MyInvalidConverter(object):
    pass


class MyConverter(object):
    class_provides(IRepresentationConverter)

    @classmethod
    def convert_from_representation(cls, representation_value,
                                    value_type): # pylint: disable=W0613
        return representation_value

    @classmethod
    def convert_to_representation(cls, value,
                                  value_type): # pylint: disable=W0613
        return value


class MyConverterRegistry(ConverterRegistry):
    pass
