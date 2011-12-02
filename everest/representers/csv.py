"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

CSV representers.

Created on May 19, 2011.
"""

from __future__ import absolute_import # Makes the import below absolute
from csv import Dialect
from csv import QUOTE_NONNUMERIC
from csv import reader
from csv import register_dialect
from csv import writer
from everest.mime import CsvMime
from everest.representers.base import DataElementGenerator
from everest.representers.base import DataElementParser
from everest.representers.base import RepresentationGenerator
from everest.representers.base import RepresentationParser
from everest.representers.base import RepresenterConfiguration
from everest.representers.base import ResourceRepresenter
from everest.representers.base import SimpleDataElement
from everest.representers.base import SimpleDataElementRegistry
from everest.representers.base import SimpleLinkedDataElement
from everest.representers.utils import get_data_element_registry
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.utils import get_member_class
from everest.resources.utils import is_resource_url
from everest.resources.utils import provides_member_resource

__docformat__ = 'reStructuredText en'
__all__ = ['CsvDataElement',
           'CsvDataElementRegistry',
           'CsvLinkedDataElement',
           'CsvRepresentationGenerator'
           'CsvRepresentationParser',
           'CsvRepresenterConfiguration',
           'CsvResourceRepresenter',
           ]


class _DefaultDialect(Dialect): # ignore no __init__ pylint: disable=W0232
    """
    Default dialect to use when exporting resources to CSV.
    """
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\n'
    quoting = QUOTE_NONNUMERIC
register_dialect('default', _DefaultDialect)


class CsvRepresentationParser(RepresentationParser):

    def run(self):
        csv_reader = reader(self._stream, self.get_option('dialect'))
        is_member_rpr = provides_member_resource(self._resource_class)
        if is_member_rpr:
            member_cls = self._resource_class
            result_data_el = None
        else:
            # Collection resource: Create a wrapping collection data element.
            member_cls = get_member_class(self._resource_class)
            coll_de_fac = self.__lookup_de_class(self._resource_class).create
            coll_data_el = coll_de_fac()
            result_data_el = coll_data_el
        de_cls = self.__lookup_de_class(member_cls)
        member_de_fac = de_cls.create
        attrs = de_cls.mapper.get_mapped_attributes(member_cls)
        header = None
        for row in csv_reader:
            member_data_el = member_de_fac()
            if header is None:
                # Check if the header is valid.
                attr_names = attrs.keys()
                header = row
                for attr in header:
                    if not attr in attr_names:
                        raise ValueError('Invalid field "%s" in CSV input '
                                         'detected.' % attr)
                continue
            if len(row) != len(header):
                raise ValueError("Invalid row length (found: %s, expected: "
                                 "%s)." % (len(row), len(header)))
            for csv_attr, value in zip(header, row):
                attr = attrs[csv_attr]
                if is_resource_url(value):
                    # Resources are *always* links.
                    link = \
                       CsvLinkedDataElement.create(member_data_el.mapped_class,
                                                   value)
                    member_data_el.set_nested(attr, link)
                else:
                    # Treat everything else as a terminal.
                    member_data_el.set_terminal(attr, value)
            if is_member_rpr:
                result_data_el = member_data_el
            else:
                coll_data_el.add_member(member_data_el)
        return result_data_el

    def __lookup_de_class(self, rc_class):
        de_reg = get_data_element_registry(CsvMime)
        return de_reg.get_data_element_class(rc_class)


class CsvRepresentationGenerator(RepresentationGenerator):
    """
    A CSV writer for resource data.

    Handles linked resources and referenced member resources.
    """

    def __init__(self, stream, resource_class):
        RepresentationGenerator.__init__(self, stream, resource_class)
        self.__is_header_written = False

    def run(self, data_element):
        csv_writer = writer(self._stream, dialect=self.get_option('dialect'))
        is_member_rpr = provides_member_resource(self._resource_class)
        if is_member_rpr:
            rows_data = [self.__process_data(data_element)]
        else:
            rows_data = [self.__process_data(data_el)
                         for data_el in data_element.get_members()]
        for row_data in rows_data:
            if not self.__is_header_written:
                csv_writer.writerow(row_data.keys())
                self.__is_header_written = True
            csv_writer.writerow(row_data.values())

    def __process_data(self, data_el):
        row_data = {}
        attrs = data_el.mapper.get_mapped_attributes(data_el.mapped_class)
        for attr in attrs.values():
            attr_name_str = self.__encode(attr.representation_name)
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                value = data_el.get_terminal(attr)
                row_data[attr_name_str] = value
            else:
                value = data_el.get_nested(attr)
                if value is None:
                    continue
                if not isinstance(value, CsvLinkedDataElement):
                    raise ValueError('CSV representations must encode nested '
                                     'resources as link.')
                row_data[attr_name_str] = self.__encode(value.get_url())
        return row_data

    def __encode(self, item):
        encoding = self.get_option('encoding')
        return isinstance(item, unicode) and item.encode(encoding) or item



class CsvResourceRepresenter(ResourceRepresenter):

    content_type = CsvMime

    #: The CSV dialect to use for reading and writing CSV data.
    CSV_DIALECT = 'default'
    #: The encoding to use for reading and writing CSV data.
    ENCODING = 'utf-8'

    @classmethod
    def make_data_element_registry(cls):
        return CsvDataElementRegistry()

    def _make_representation_parser(self, stream, resource_class, **config):
        parser = CsvRepresentationParser(stream, resource_class)
        parser.set_option('dialect', self.CSV_DIALECT)
        parser.configure(**config)
        return parser

    def _make_representation_generator(self, stream, resource_class, **config):
        generator = CsvRepresentationGenerator(stream, resource_class)
        generator.set_option('dialect', self.CSV_DIALECT)
        generator.set_option('encoding', self.ENCODING)
        generator.configure(**config)
        return generator

    def _make_data_element_parser(self):
        return DataElementParser()

    def _make_data_element_generator(self):
        return DataElementGenerator(self._data_element_registry)


# Adapter creating representers from resource instances.
resource_adapter = CsvResourceRepresenter.create_from_resource


class CsvDataElement(SimpleDataElement):
    pass


class CsvLinkedDataElement(SimpleLinkedDataElement):
    pass


class CsvRepresenterConfiguration(RepresenterConfiguration):
    pass


class CsvDataElementRegistry(SimpleDataElementRegistry):
    """
    Registry for CSV data element classes.
    """
    data_element_class = CsvDataElement
    linked_data_element_class = CsvLinkedDataElement
    configuration_class = CsvRepresenterConfiguration
