"""
Converters resource attribute value <-> representation string.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 25, 2012.
"""
import datetime

import iso8601
from iso8601.iso8601 import FixedOffset
from pyramid.compat import string_types

from everest.representers.interfaces import IRepresentationConverter
from everest.rfc3339 import rfc3339
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
from zope.interface import provider # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['BooleanConverter',
           'ConverterRegistry',
           'DateTimeConverter',
           'NoOpConverter',
           'SimpleConverterRegistry',
           ]


# FIXME: Monkey-patching FixedOffset to fix problem with deepcopy
#        See http://code.google.com/p/pyiso8601/issues/detail?id=20
def _reduce(self):
    hrs, secs = \
        divmod(self._FixedOffset__offset.seconds, 3600) # pylint: disable=W0212
    mins = int(secs / 60)
    return (self.__class__,
            (hrs, mins, self._FixedOffset__name), {}) # pylint: disable=W0212
FixedOffset.__reduce__ = _reduce
del FixedOffset
del _reduce


class ConverterRegistry(object):
    __converters = None

    @classmethod
    def register(cls, value_type, converter_class):
        if cls.__converters is None: # Lazy initialization.
            cls.__converters = {}
        if value_type in cls.__converters:
            raise ValueError('For %s, a converter has already been '
                             'registered (%s).'
                             % (value_type, cls.__converters[value_type]))
        if not IRepresentationConverter in provided_by(converter_class):
            raise ValueError('Converter class must provide '
                             'IRepresenterConverter.')
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
        if not cnv is None and not value is None:
            representation_value = cnv.to_representation(value)
        elif not isinstance(value, string_types) and not value is None:
            representation_value = str(value) # FIXME: use unicode?
        return representation_value


class SimpleConverterRegistry(ConverterRegistry):
    pass


@provider(IRepresentationConverter)
class DateTimeConverter(object):
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


SimpleConverterRegistry.register(datetime.datetime, DateTimeConverter)


@provider(IRepresentationConverter)
class BooleanConverter(object):
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


SimpleConverterRegistry.register(bool, BooleanConverter)


@provider(IRepresentationConverter)
class NoOpConverter(object):
    @classmethod
    def from_representation(cls, value):
        return value

    @classmethod
    def to_representation(cls, value):
        return value
