"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Jul 5, 2011.
"""

from everest.resources.interfaces import IResource
from everest.url import url_to_resource
from pyparsing import ParseException
from zope.interface import providedBy as provided_by # pylint: disable=E0611,F0401
import logging

__docformat__ = 'reStructuredText en'
__all__ = ['FilterDirector',
           'FilterBuilder',
           'SpecificationFilterBuilder',
           ]


class FilterDirector(object):
    """
    """

    __builder = None
    __parser = None
    __errors = None
    __logger = logging.getLogger(__name__)

    def __init__(self, parser, builder):
        self.__parser = parser
        self.__builder = builder
        self.__errors = []

    def construct(self, query):
        try:
            self.__logger.debug('Query received: %s' % query)
            result = self.__parser(query)
        except ParseException, e:
            # TODO: create better error messages # pylint: disable=W0511
            self.__errors.append('Query parameters have errors. %s' % e)
        else:
            self.__process_criteria(result.criteria)

    def has_errors(self):
        return len(self.__errors) > 0

    def get_errors(self):
        return self.__errors[:]

    def _format_identifier(self, string):
        return string.replace('-', '_')

    def __process_criteria(self, criteria):
        for crit in criteria:
            name, oper, values = crit
            if len(values) > 0: # criteria with no values are ignored
                name = self._format_identifier(name)
                oper = self._format_identifier(oper)
                values = self.__prepare_values(values)
                command = getattr(self.__builder, 'build_%s' % oper)
                command(name, values)

    def __prepare_values(self, values):
        prepared = []
        for v in values:
            if self.__is_empty_string(v):
                continue
            elif self.__is_url(v):
                v = url_to_resource(''.join(v))
            if not v in prepared:
                prepared.append(v)
        return prepared

    def __is_url(self, v):
        return isinstance(v, basestring) and v.startswith('http://')

    def __is_empty_string(self, v):
        return isinstance(v, basestring) and len(v) == 0


class FilterBuilder(object):
    """
    Abstract base class for all Filter Builders

    Based on the Builder Design Pattern
    """

    def build_equal_to(self, attr_name, attr_values):
        """
        """
        pass

    def build_not_equal_to(self, attr_name, attr_values):
        """
        """
        pass

    def build_starts_with(self, attr_name, attr_values):
        """
        """
        pass

    def build_not_starts_with(self, attr_name, attr_values):
        """
        """
        pass

    def build_ends_with(self, attr_name, attr_values):
        """
        """
        pass

    def build_not_ends_with(self, attr_name, attr_values):
        """
        """
        pass

    def build_contains(self, attr_name, attr_values):
        """
        """
        pass

    def build_not_contains(self, attr_name, attr_values):
        """
        """
        pass

    def build_less_than_or_equal_to(self, attr_name, attr_values):
        """
        """
        pass

    def build_less_than(self, attr_name, attr_values):
        """
        """
        pass

    def build_greater_than_or_equal_to(self, attr_name, attr_values):
        """
        """
        pass

    def build_greater_than(self, attr_name, attr_values):
        """
        """
        pass

    def build_in_range(self, attr_name, attr_values):
        """
        """
        pass

    def build_not_in_range(self, attr_name, attr_values):
        """
        """
        pass


class SpecificationFilterBuilder(FilterBuilder):
    """
    Concrete builder that creates a specification
    """

    __specification = None
    __factory = None

    def __init__(self, factory):
        FilterBuilder.__init__(self)
        self.__factory = factory

    def build_equal_to(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_equal_to(attr_name, attr_values)
            )

    def build_not_equal_to(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_equal_to(attr_name, attr_values).not_()
            )

    def build_starts_with(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_starts_with(attr_name, attr_values)
            )

    def build_not_starts_with(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_starts_with(attr_name, attr_values).not_()
            )

    def build_ends_with(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_ends_with(attr_name, attr_values)
            )

    def build_not_ends_with(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_ends_with(attr_name, attr_values).not_()
            )

    def build_contains(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_contains(attr_name, attr_values)
            )

    def build_not_contains(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_contains(attr_name, attr_values).not_()
            )

    def build_less_than_or_equal_to(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_less_than_or_equal_to(attr_name, attr_values)
            )

    def build_less_than(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_less_than(attr_name, attr_values)
            )

    def build_greater_than_or_equal_to(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_greater_than_or_equal_to(attr_name, attr_values)
            )

    def build_greater_than(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_greater_than(attr_name, attr_values)
            )

    def build_in_range(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_in_range(attr_name, attr_values)
            )

    def build_not_in_range(self, attr_name, attr_values):
        self.__append_spec(
            self.__build_in_range(attr_name, attr_values).not_()
            )

    def get_specification(self):
        return self.__specification

    def __build_equal_to(self, attr_name, attr_values):
        if len(attr_values) > 1:
            spec = self.__factory.create_contained(attr_name, attr_values)
        else:
            spec = self.__build_spec(self.__factory.create_equal_to,
                                     attr_name, attr_values)
        return spec

    def __build_starts_with(self, attr_name, attr_values):
        spec = self.__build_spec(self.__factory.create_starts_with,
                                 attr_name, attr_values)
        return spec

    def __build_ends_with(self, attr_name, attr_values):
        spec = self.__build_spec(self.__factory.create_ends_with,
                                 attr_name, attr_values)
        return spec

    def __build_contains(self, attr_name, attr_values):
        spec = self.__build_spec(self.__factory.create_contains,
                                 attr_name, attr_values)
        return spec

    def __build_less_than_or_equal_to(self, attr_name, attr_values):
        values = [max(attr_values)]
        spec = self.__build_spec(self.__factory.create_less_than_or_equal_to,
                                 attr_name, values)
        return spec

    def __build_less_than(self, attr_name, attr_values):
        values = [max(attr_values)]
        spec = self.__build_spec(self.__factory.create_less_than,
                                 attr_name, values)
        return spec

    def __build_greater_than_or_equal_to(self, attr_name, attr_values):
        values = [min(attr_values)]
        spec = self.__build_spec(self.__factory.create_greater_than_or_equal_to,
                                 attr_name, values)
        return spec

    def __build_greater_than(self, attr_name, attr_values):
        values = [min(attr_values)]
        spec = self.__build_spec(self.__factory.create_greater_than,
                                 attr_name, values)
        return spec

    def __build_in_range(self, attr_name, attr_values):
        spec = self.__build_spec(self.__factory.create_in_range,
                                 attr_name, attr_values)
        return spec

    def __append_spec(self, new_specification):
        if self.__specification is None:
            self.__specification = new_specification
        else:
            self.__specification = \
                self.__factory.create_conjunction(self.__specification,
                                                  new_specification)

    def __build_spec(self, constructor, attr_name, attr_values):
        spec = None
        spec_list = []
        for value in attr_values:
            if self.__is_iterable(value):
                args = value
            else:
                args = [value]
            spec_list.append(constructor(attr_name, *args)) # * pylint: disable=W0142
        if len(spec_list) > 1:
            spec = reduce(self.__factory.create_disjunction, spec_list)
        else:
            spec = spec_list[0]
        return spec

    def __is_iterable(self, value):
        # TODO: Fix this ugly hack # pylint: disable=W0511
        return hasattr(value, '__iter__') \
            and not IResource in provided_by(value)
