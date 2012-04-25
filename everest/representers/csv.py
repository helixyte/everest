"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

CSV representers.

Created on May 19, 2011.
"""

from __future__ import absolute_import # Makes the import below absolute
from collections import OrderedDict
from csv import Dialect
from csv import QUOTE_NONNUMERIC
from csv import reader
from csv import register_dialect
from csv import writer
from everest.mime import CsvMime
from everest.representers.base import RepresenterConfiguration
from everest.representers.base import ResourceRepresenter
from everest.representers.dataelements import SimpleCollectionDataElement
from everest.representers.dataelements import SimpleDataElementRegistry
from everest.representers.dataelements import SimpleLinkedDataElement
from everest.representers.dataelements import SimpleMemberDataElement
from everest.representers.generators import DataElementGenerator
from everest.representers.generators import RepresentationGenerator
from everest.representers.parsers import DataElementParser
from everest.representers.parsers import RepresentationParser
from everest.representers.utils import get_data_element_registry
from everest.resources.attributes import ResourceAttributeKinds
from everest.resources.utils import get_member_class
from everest.resources.utils import is_resource_url
from everest.resources.utils import provides_member_resource

__docformat__ = 'reStructuredText en'
__all__ = ['CsvCollectionDataElement',
           'CsvDataElementRegistry',
           'CsvLinkedDataElement',
           'CsvMemberDataElement',
           'CsvRepresentationGenerator'
           'CsvRepresentationParser',
           'CsvRepresenterConfiguration',
           'CsvResourceRepresenter',
           'resource_adapter',
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

    Handles linked resources and nested member and collection resources.
    """
    class __CsvData(object):
        def __init__(self):
            self.__data = []
            self.__fields = []
            self.__field_indices = OrderedDict()

        @property
        def header(self):
            return self.__field_indices.keys()

        def __setitem__(self, key, value):
            row_index, field = key
            if not field in self.__fields:
                self.__field_indices[field] = len(self.__fields)
                self.__fields.append(field)
            num_rows = len(self.__data)
            if row_index > (num_rows - 1):
                if num_rows - row_index - 1 > 0:
                    raise ValueError('Can not auto-append beyond the last '
                                     'data row.')
                self.__data.append(dict())
            field_index = self.__field_indices[field]
            self.__data[row_index][field_index] = value

        def __getitem__(self, key):
            row_index, field = key
            field_index = self.__field_indices[field]
            return self.__data[row_index][field_index]

        def __iter__(self):
            last_row_data = {}
            for row_data in self.__data:
                row_values = []
                for field_index in self.__field_indices.values():
                    cell_value = row_data.get(field_index)
                    if cell_value is None:
                        cell_value = last_row_data.get(field_index)
                        row_data[field_index] = cell_value
                    row_values.append(cell_value)
                yield row_values
                last_row_data = row_data

        def __len__(self):
            return len(self.__data)

    def __init__(self, stream, resource_class):
        RepresentationGenerator.__init__(self, stream, resource_class)
        self.__is_header_written = False

    def run(self, data_element):
        csv_writer = writer(self._stream, dialect=self.get_option('dialect'))
        is_member_rpr = provides_member_resource(self._resource_class)
        rows_data = self.__CsvData()
        if is_member_rpr:
            mb_data_els = [data_element]
        else:
            mb_data_els = data_element.get_members()
        for mb_data_el in mb_data_els:
            self.__process_data(mb_data_el, rows_data, len(rows_data), None)
        csv_writer.writerow(rows_data.header)
        for row_data in rows_data:
            csv_writer.writerow(row_data)

    def __process_data(self, data_el, rows_data, row_index, prefix):
        has_found_collection = False
        attrs = data_el.mapper.get_mapped_attributes(data_el.mapped_class)
        for attr in attrs.values():
            attr_name_str = self.__encode(attr.representation_name)
            if not prefix is None:
                attr_name_str = "%s.%s" % (prefix, attr_name_str)
            key = (row_index, attr_name_str)
            if attr.kind == ResourceAttributeKinds.TERMINAL:
                value = data_el.get_terminal(attr)
                rows_data[key] = value
            else:
                value = data_el.get_nested(attr)
                if value is None:
                    rows_data[key] = None
                elif isinstance(value, CsvLinkedDataElement):
                    rows_data[key] = self.__encode(value.get_url())
#                    raise ValueError('CSV representations must encode nested '
#                                     'resources as a link.')
                elif attr.kind == ResourceAttributeKinds.MEMBER:
                    self.__process_data(value, rows_data,
                                        row_index, attr_name_str)
                elif attr.kind == ResourceAttributeKinds.COLLECTION:
                    if not has_found_collection:
                        has_found_collection = True
                    else:
                        raise ValueError('In CSV representations, all but '
                                         'one collection attribute must be '
                                         'represented as links.')
                    for mb_cnt, mb_data_el in enumerate(value.get_members()):
                        self.__process_data(mb_data_el, rows_data,
                                            row_index + mb_cnt, attr_name_str)

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

    def _make_data_element_parser(self, resolve_urls=True):
        return DataElementParser(resolve_urls=resolve_urls)

    def _make_data_element_generator(self):
        return DataElementGenerator(self._data_element_registry)


# Adapter creating representers from resource instances.
resource_adapter = CsvResourceRepresenter.create_from_resource


class CsvMemberDataElement(SimpleMemberDataElement):
    pass


class CsvCollectionDataElement(SimpleCollectionDataElement):
    pass


class CsvLinkedDataElement(SimpleLinkedDataElement):
    pass


class CsvRepresenterConfiguration(RepresenterConfiguration):
    pass


class CsvDataElementRegistry(SimpleDataElementRegistry):
    """
    Registry for CSV data element classes.
    """
    member_data_element_base_class = CsvMemberDataElement
    collection_data_element_base_class = CsvCollectionDataElement
    linked_data_element_base_class = CsvLinkedDataElement
    configuration_class = CsvRepresenterConfiguration
