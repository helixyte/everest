"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 25, 2012.
"""
from everest.representers.interfaces import IRepresentationConverter
from rfc3339 import rfc3339
from zope.interface import implements # pylint: disable=E0611,F0401
import datetime
import iso8601

__docformat__ = 'reStructuredText en'
__all__ = ['BooleanConverter',
           'ConverterRegistry',
           'DateTimeConverter',
           'SimpleConverterRegistry',
           ]


class ConverterRegistry(object):
    __converters = None

    @classmethod
    def register(cls, value_type, converter_class):
        if cls.__converters is None: # Lazy initialization.
            cls.__converters = {}
        if value_type in cls.__converters:
            raise ValueError('For the "%s" data type, a converter has '
                             'already been registered (%s).'
                             % (value_type, cls.__converters[value_type]))
        cls.__converters[value_type] = converter_class

    @classmethod
    def convert_from_representation(cls, representation_value, value_type):
        if cls.__converters is None: # Lazy initialization.
            cls.__converters = {}
        cnv = cls.__converters.get(value_type)
        if not cnv is None:
            value = cnv.from_representation(representation_value)
        else:
            if not representation_value is None:
                # Try the value type's constructor.
                value = value_type(representation_value)
            else:
                value = None
        return value

    @classmethod
    def convert_to_representation(cls, value, value_type):
        if cls.__converters is None: # Lazy initialization.
            cls.__converters = {}
        cnv = cls.__converters.get(value_type)
        representation_value = value
        if not cnv is None:
            representation_value = cnv.to_representation(value)
        elif not isinstance(value, basestring):
            representation_value = str(value) # FIXME: use unicode?
        return representation_value


class SimpleConverterRegistry(ConverterRegistry):
    pass


class DateTimeConverter(object):
    implements(IRepresentationConverter)

    @classmethod
    def from_representation(cls, value):
        if value is None:
            py_val = None
        else:
            py_val = iso8601.parse_date(value)
        return py_val

    @classmethod
    def to_representation(cls, value):
        return rfc3339(value)


class BooleanConverter(object):
    implements(IRepresentationConverter)

    @classmethod
    def from_representation(cls, value):
        if value is None:
            py_val = None
        else:
            py_val = False if value == 'false' else True
        return py_val

    @classmethod
    def to_representation(cls, value):
        return str(value).lower()


SimpleConverterRegistry.register(datetime.datetime, DateTimeConverter)
SimpleConverterRegistry.register(bool, BooleanConverter)


