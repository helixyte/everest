"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 7, 2012.
"""
from copy import deepcopy
from everest.representers.converters import ConverterRegistry
from everest.representers.converters import SimpleConverterRegistry
from everest.representers.interfaces import IRepresentationConverter
from everest.rfc3339 import rfc3339
from everest.testing import Pep8CompliantTestCase
from iso8601.iso8601 import parse_date
from pytz import timezone
from zope.interface import provider # pylint: disable=E0611,F0401
import datetime

__docformat__ = 'reStructuredText en'
__all__ = ['RepresenterConverterTestCase',
           ]


class RepresenterConverterTestCase(Pep8CompliantTestCase):
    def test_registry(self):
        with self.assert_raises(ValueError) as cm:
            SimpleConverterRegistry.register(bool, MyConverter)
        self.assert_true(str(cm.exception).startswith('For %s' % bool))
        with self.assert_raises(ValueError) as cm:
            SimpleConverterRegistry.register(MyNumberType, MyInvalidConverter)
        self.assert_true(str(cm.exception).startswith('Converter class'))

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

    def test_datetime_converter(self):
        utc = timezone('UTC')
        ldt = datetime.datetime(2012, 8, 29, 16, 20, 0, tzinfo=utc)
        ldt_rpr = rfc3339(ldt, use_system_timezone=False)
        self.assert_equal(
            SimpleConverterRegistry.convert_from_representation(
                                                        ldt_rpr,
                                                        datetime.datetime),
            ldt)
        self.assert_equal(
            SimpleConverterRegistry.convert_to_representation(ldt,
                                                        datetime.datetime),
            ldt_rpr)

    def test_parse_date_fix(self):
        d = parse_date('2012-06-13 11:06:47+02:00')
        d_copy = deepcopy(d)
        self.assert_equal(d, d_copy)


class MyNumberType(int):
    pass


class MyInvalidConverter(object):
    pass


@provider(IRepresentationConverter)
class MyConverter(object):
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
