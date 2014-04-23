"""
CSV representers.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on May 19, 2011.
"""
from __future__ import absolute_import # Makes the import below absolute

from collections import OrderedDict
from csv import Dialect
from csv import QUOTE_NONNUMERIC
from csv import register_dialect
from csv import writer
import datetime
from itertools import product

from pyramid.compat import NativeIO
from pyramid.compat import PY3
from pyramid.compat import binary_type
from pyramid.compat import bytes_
from pyramid.compat import iteritems_
from pyramid.compat import string_types
from pyramid.compat import text_
from pyramid.compat import text_type

from everest.compat import CsvDictReader
from everest.constants import RESOURCE_ATTRIBUTE_KINDS
from everest.constants import RESOURCE_KINDS
from everest.mime import CsvMime
from everest.representers.attributes import MappedAttributeKey
from everest.representers.base import MappingResourceRepresenter
from everest.representers.base import RepresentationGenerator
from everest.representers.base import RepresentationParser
from everest.representers.config import RepresenterConfiguration
from everest.representers.converters import BooleanConverter
from everest.representers.converters import ConverterRegistry
from everest.representers.converters import DateTimeConverter
from everest.representers.converters import NoOpConverter
from everest.representers.dataelements import SimpleCollectionDataElement
from everest.representers.dataelements import SimpleLinkedDataElement
from everest.representers.dataelements import SimpleMemberDataElement
from everest.representers.interfaces import IRepresentationConverter
from everest.representers.mapping import SimpleMappingRegistry
from everest.representers.traversal import DataElementTreeTraverser
from everest.representers.traversal import ResourceDataVisitor
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import is_resource_url
from everest.resources.utils import provides_member_resource
from zope.interface import provider # pylint: disable=E0611,F0401


__docformat__ = 'reStructuredText en'
__all__ = ['CsvCollectionDataElement',
           'CsvConverterRegistry',
           'CsvData',
           'CsvDataElementTreeVisitor',
           'CsvIntConverter',
           'CsvLinkedDataElement',
           'CsvMappingRegistry',
           'CsvMemberDataElement',
           'CsvRepresentationGenerator',
           'CsvRepresentationParser',
           'CsvRepresenterConfiguration',
           'CsvResourceRepresenter',
           ]


class _DefaultCsvDialect(Dialect): # ignore no __init__ pylint: disable=W0232
    """
    Default dialect to use when exporting resources to CSV.
    """
    delimiter = ','
    quotechar = '"'
    doublequote = True
    skipinitialspace = False
    lineterminator = '\n'
    quoting = QUOTE_NONNUMERIC
register_dialect('export', _DefaultCsvDialect)
register_dialect('import', _DefaultCsvDialect)


class CsvConverterRegistry(ConverterRegistry):
    pass


@provider(IRepresentationConverter)
class CsvIntConverter(object):
    """
    Specialized converter coping with the CSV reader's unfortunate habit
    to convert integers to floats upon reading.
    """

    @classmethod
    def from_representation(cls, value):
        if isinstance(value, float):
            value = int(value)
        return value

    @classmethod
    def to_representation(cls, value):
        return value


if not PY3: # pragma: no cover
    @provider(IRepresentationConverter)
    class CsvTextConverter(object):

        @classmethod
        def from_representation(cls, value):
            return text_(value, encoding='utf-8')

        @classmethod
        def to_representation(cls, value):
            return bytes_(value, encoding='utf-8')

    CsvConverterRegistry.register(text_type, CsvTextConverter)
else: # pragma: no cover
    @provider(IRepresentationConverter)
    class CsvBytesConverter(object):

        @classmethod
        def from_representation(cls, value):
            return bytes_(value, encoding='utf-8')

        @classmethod
        def to_representation(cls, value):
            return text_(value, encoding='utf-8')

    CsvConverterRegistry.register(binary_type, CsvBytesConverter)


CsvConverterRegistry.register(datetime.datetime, DateTimeConverter)
CsvConverterRegistry.register(bool, BooleanConverter)
CsvConverterRegistry.register(int, CsvIntConverter)
CsvConverterRegistry.register(float, NoOpConverter)


class CsvRepresentationParser(RepresentationParser):
    """
    Parser for CSV representations.

    The tabular structure of the CSV format makes it difficult to transport
    nested (tree-like) data structures with it. The simplest way to solve
    this problem is to resort to links (URLs) for specifying nested resources
    which implies that the referenced resources have to be created in
    advance.

    Since it is quite a common use case to create a resource and its
    immediate children from one representation (i.e., in a single REST call),
    the CSV parser also supports explicit specification of nested member
    attributes through separate CSV fields and specification of nested
    collection member attributes through separate
    CSV fields and multiple rows (i.e., each row is specifying a member in
    the nested collection while all other field values remain unchanged).
    Nested collection members are allocated to their enclosing member either
    by the member ID (if specified in a column named "id") or by the
    combined values of all remaining fields (sorted by field name).

    :note: The CSV column (field) names have to be mapped uniquely to
      (nested) attribute representation names.
    :note: Polymorphic nested resources may not be mapped correctly.
    """
    class _CollectionData(object):
        def __init__(self, collection_class, attributes, attribute_key):
            self.collection_class = collection_class
            self.attribute_key = attribute_key
            self.__attribute_names = \
                        set([attr.repr_name for attr in attributes])
            self.__data = {}

        def has(self, key):
            return key in self.__data

        def get(self, key):
            return self.__data.get(key)

        def set(self, key, collection_data_element):
            self.__data[key] = collection_data_element

        def make_key(self, row_data):
            if "id" in row_data.keys():
                key = row_data['id']
            else:
                # FIXME: This needs testing.
                key = tuple([val for (key, val) in sorted(row_data.items()) # pragma: no cover
                             if not key in self.__attribute_names])
            return key

    def __init__(self, stream, resource_class, mapping):
        RepresentationParser.__init__(self, stream, resource_class, mapping)
        # Helper object for collecting member data for a nested collection.
        self.__coll_data = None
        # List of field names and copy of row data (first row only).
        self.__first_row_field_names = None
        self.__first_row_data = None
        # Flag indicating state "in first row".
        self.__is_first_row = True
        # Key used to detect repeating rows for nested collection members.
        self.__row_data_key = None

    def run(self):
        csv_rdr = CsvDictReader(self._stream,
                                dialect=self.get_option('dialect'))
        is_member_rpr = provides_member_resource(self._resource_class)
        if is_member_rpr:
            coll_data_el = None
        else:
            coll_data_el = self._mapping.create_data_element()
        for row_data in csv_rdr:
            if self.__is_first_row:
                self.__first_row_field_names = set(csv_rdr.fieldnames)
                self.__first_row_data = row_data.copy()
            if not self.__coll_data is None:
                # We need to generate the row data key now because we
                # get attribute values destructively from the row_data.
                self.__row_data_key = self.__coll_data.make_key(row_data)
            mb_data_el = self.__process_row(row_data, self._resource_class,
                                            MappedAttributeKey(()))
            if self.__is_first_row:
                self.__is_first_row = False
                if len(self.__first_row_field_names) > 0:
                    raise ValueError('Invalid field name(s): %s'
                                     % ','.join(self.__first_row_field_names))
            if None in row_data.keys():
                raise ValueError('Invalid row length.')
            if not coll_data_el is None:
                # The member data element will be None for all but the first
                # member of nested collection resources.
                if not mb_data_el is None:
                    coll_data_el.add_member(mb_data_el)
        if is_member_rpr:
            result_data_el = mb_data_el
        else:
            result_data_el = coll_data_el
        return result_data_el

    def __process_row(self, row_data, mapped_class, attribute_key):
        is_repeating_row = len(attribute_key) == 0 \
                           and not self.__coll_data is None \
                           and self.__coll_data.has(self.__row_data_key)
        if is_repeating_row:
            self.__process_row(row_data,
                               self.__coll_data.collection_class,
                               self.__coll_data.attribute_key)
            new_data_el = None
        else:
            mb_cls = get_member_class(mapped_class)
            new_data_el = \
                    self._mapping.create_data_element(mapped_class=mb_cls)
            for attr in self._mapping.terminal_attribute_iterator(
                                                mapped_class, attribute_key):
                self.__process_attr(attr, attribute_key, new_data_el,
                                    row_data)
            for attr in self._mapping.nonterminal_attribute_iterator(
                                                mapped_class, attribute_key):
                self.__process_attr(attr, attribute_key, new_data_el,
                                    row_data)
            if not self.__coll_data is None \
               and mapped_class == self.__coll_data.collection_class:
                if not self.__coll_data.has(self.__row_data_key):
                    coll_data_el = \
                        self._mapping.create_data_element(mapped_class=
                                                                mapped_class)
                    self.__coll_data.set(self.__row_data_key, coll_data_el)
                else:
                    coll_data_el = self.__coll_data.get(self.__row_data_key)
                coll_data_el.add_member(new_data_el)
                new_data_el = coll_data_el
        return new_data_el

    def __process_attr(self, attribute, attribute_key, data_el, row_data):
        try:
            attribute_value = row_data.pop(attribute.repr_name)
        except KeyError:
            attribute_value = None
            has_attribute = False
        else:
            has_attribute = True
        # In the first row, we check for extra field names by removing all
        # fields we found from the set of all field names.
        if self.__is_first_row:
            self.__first_row_field_names.discard(attribute.repr_name)
        if attribute.should_ignore(attribute_key):
            if not attribute_value in (None, ''):
                raise ValueError('Value for attribute "%s" found '
                                 'which is configured to be ignored.'
                                 % attribute.repr_name)
        else:
            if attribute.kind == RESOURCE_ATTRIBUTE_KINDS.TERMINAL:
                if not attribute_value is None:
                    data_el.set_terminal_converted(attribute, attribute_value)
            else:
                # FIXME: It is peculiar to treat the empty string as None
                #        here. However, this seems to be the way the csv
                #        module does it.
                if not attribute_value in (None, ''):
                    link_data_el = \
                            self.__process_link(attribute_value, attribute)
                    data_el.set_nested(attribute, link_data_el)
                elif not has_attribute and len(row_data) > 0:
                    nested_attr_key = attribute_key + (attribute,)
                    # We recursively look for nested resource attributes in
                    # other fields.
                    if attribute.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
                        # For polymorphic classes, this lookup will only work
                        # if a representer (and a mapping) was initialized
                        # for each derived class.
                        nested_rc_cls = get_member_class(attribute.value_type)
                    else: # collection attribute.
                        nested_rc_cls = \
                                    get_collection_class(attribute.value_type)
                        if self.__coll_data is None:
                            self.__coll_data = \
                                self.__make_collection_data(nested_rc_cls,
                                                            nested_attr_key)
                            if self.__is_first_row:
                                self.__row_data_key = \
                                    self.__coll_data.make_key(
                                                        self.__first_row_data)
                        elif self.__coll_data.collection_class \
                                                         != nested_rc_cls:
                            raise ValueError('All but one nested collection '
                                             'resource attributes have to '
                                             'be provided as links.')
                    nested_data_el = \
                        self.__process_row(row_data, nested_rc_cls,
                                           nested_attr_key)
                    if attribute.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
                        if len(nested_data_el.data) > 0:
                            data_el.set_nested(attribute, nested_data_el)
                    elif len(nested_data_el) > 0:
                        data_el.set_nested(attribute, nested_data_el)

    def __make_collection_data(self, collection_class, attribute_key):
        attrs = self._mapping.attribute_iterator(collection_class,
                                                 attribute_key)
        return self._CollectionData(collection_class, attrs, attribute_key)

    def __is_link(self, value):
        return isinstance(value, string_types) and is_resource_url(value)

    def __process_link(self, link, attr):
        if not self.__is_link(link):
            raise ValueError('Value for nested attribute "%s" '
                             'is not a link.' % attr.repr_name)
        if attr.kind == RESOURCE_ATTRIBUTE_KINDS.MEMBER:
            kind = RESOURCE_KINDS.MEMBER
            rc_cls = get_member_class(attr.value_type)
        else:
            kind = RESOURCE_KINDS.COLLECTION
            rc_cls = get_collection_class(attr.value_type)
        return self._mapping.create_linked_data_element(link,
                                                        kind,
                                                        relation=
                                                            rc_cls.relation,
                                                        title=rc_cls.title)


#class CsvRepresentationParser(RepresentationParser):
#    """
#    Parser converting CSV representations of resources into a data element.
#
#    :note: Nested resources have to be provided as links (i.e., there is no
#           support for recursive data element tree building).
#    """
#
#    def run(self):
#        mp_reg = get_mapping_registry(CsvMime)
#        is_member_rpr = provides_member_resource(self._resource_class)
#        if is_member_rpr:
#            member_cls = self._resource_class
#            result_data_el = None
#        else:
#            # Collection resource: Create a wrapping collection data element.
#            member_cls = get_member_class(self._resource_class)
#            coll_mp = mp_reg.find_or_create_mapping(self._resource_class)
#            coll_data_el = coll_mp.create_data_element()
#            result_data_el = coll_data_el
#        mb_mp = mp_reg.find_or_create_mapping(member_cls)
#        csv_rdr = reader(self._stream, self.get_option('dialect'))
#        attrs = mb_mp.get_attribute_map()
#        header = None
#        for row in csv_rdr:
#            mb_data_el = mb_mp.create_data_element()
#            if header is None:
#                # Check if the header is valid.
#                attr_names = attrs.keys()
#                header = row
#                for attr in header:
#                    if not attr in attr_names:
#                        raise ValueError('Invalid field "%s" in CSV input '
#                                         'detected.' % attr)
#                continue
#            if len(row) != len(header):
#                raise ValueError("Invalid row length (found: %s, expected: "
#                                 "%s)." % (len(row), len(header)))
#            for csv_attr, value in zip(header, row):
#                if value == '':
#                    value = None
#                attr = attrs[csv_attr]
#                if is_resource_url(value):
#                    link = CsvLinkedDataElement.create(value, attr.kind)
#                    mb_data_el.set_nested(attr, link)
#                else:
#                    mb_data_el.set_terminal_converted(attr, value)
#            if is_member_rpr:
#                result_data_el = mb_data_el
#            else:
#                coll_data_el.add_member(mb_data_el)
#        return result_data_el


class CsvData(object):
    def __init__(self, data=None):
        if data is None:
            data = {}
        self.fields = []
        self.data = []
        for attr_name, value in iteritems_(data):
            if not isinstance(value, CsvData):
                self.fields.append(attr_name)
                if len(self.data) == 0:
                    self.data.append([value])
                else:
                    for row in self.data:
                        row.append(value)
            else:
                self.expand(value)

    def expand(self, other):
        if len(self.data) == 0:
            self.data = other.data
        else:
            new_data = []
            for self_row, other_row in list(product(self.data, other.data)):
                new_data.append(self_row + other_row)
            self.data = new_data
        self.fields = self.fields + other.fields

    def append(self, other):
        if len(self.data) == 0:
            self.data = other.data
            self.fields = other.fields
        else:
            for row in other.data:
                self.data.append(row)

    def __len__(self):
        return len(self.data)


class CsvDataElementTreeVisitor(ResourceDataVisitor):
    def __init__(self, encoding):
        ResourceDataVisitor.__init__(self)
        self.__encoding = encoding
        self.__csv_data = None

    def visit_member(self, attribute_key, attribute, member_node, member_data,
                     is_link_node, parent_data, index=None):
        if is_link_node:
            new_field_name = self.__get_field_name(attribute_key.names[:-1],
                                                   attribute)
            mb_data = CsvData({new_field_name: member_node.get_url()})
        else:
            rpr_mb_data = OrderedDict()
            for attr, value in iteritems_(member_data):
                new_field_name = self.__get_field_name(attribute_key.names,
                                                       attr)
                rpr_mb_data[new_field_name] = self.__encode(value)
            mb_data = CsvData(rpr_mb_data)
        if not index is None:
            # Collection member. Store in parent data with index as key.
            parent_data[index] = mb_data
        elif len(attribute_key) == 0:
            # Top level - store as CSV data..
            self.__csv_data = mb_data
        else:
            # Nested member. Store in parent data with attribute as key.
            parent_data[attribute] = mb_data

    def visit_collection(self, attribute_key, attribute, collection_node,
                         collection_data, is_link_node, parent_data):
        if is_link_node:
            new_field_name = self.__get_field_name(attribute_key.names[:-1],
                                                   attribute)
            coll_data = CsvData({new_field_name:collection_node.get_url()})
        else:
            coll_data = CsvData()
            for item in sorted(collection_data.items()):
                mb_data = item[1]
                coll_data.append(mb_data)
        if len(attribute_key) == 0:
            self.__csv_data = coll_data
        else:
            parent_data[attribute] = coll_data

    @property
    def csv_data(self):
        return self.__csv_data

    def __get_field_name(self, attribute_names, attribute):
        if attribute.name != attribute.repr_name:
            field_name = attribute.repr_name
        else:
            field_name = '.'.join(attribute_names + (attribute.name,))
        return field_name # self.__encode(field_name)

    def __encode(self, item):
        if not PY3 and isinstance(item, text_type): # pragma: no cover
            item = item.encode(self.__encoding)
        return item


class CsvRepresentationGenerator(RepresentationGenerator):
    """
    A generator converting data elements into CSV representations.

    :note: ``None`` values in terminal attributes are represented as the empty
           string (this is the default behavior of the CSV writer from the
           standard library).
    :note: Nested member and collection resources are handled by adding
           more columns (member attributes) and rows (collection members)
           dynamically. By default, column names for nested member attributes
           are built as dot-concatenation of the corresponding attribute key.
    """
    def run(self, data_element):
        # We also emit None values to make sure every data row has the same
        # number of fields.
        trv = DataElementTreeTraverser(data_element, self._mapping,
                                       ignore_none_values=False)
        vst = CsvDataElementTreeVisitor(self.get_option('encoding'))
        trv.run(vst)
        csv_data = vst.csv_data
        if len(csv_data) > 0:
            wrt = writer(self._stream, dialect=self.get_option('dialect'))
            wrt.writerow(csv_data.fields)
            for row_data in csv_data.data:
                wrt.writerow(row_data)


class CsvResourceRepresenter(MappingResourceRepresenter):
    """
    Resource representer implementation for CSV.
    """
    content_type = CsvMime
    #: The CSV dialect to use for exporting CSV data.
    CSV_EXPORT_DIALECT = 'export'
    #: The CSV dialect to use for importing CSV data.
    CSV_IMPORT_DIALECT = 'import'

    @classmethod
    def make_mapping_registry(cls):
        return CsvMappingRegistry()

    if not PY3:
        # Under 2.x, the CSV writer and reader operates on byte streams, so
        # we have to override a few methods here.
        def to_bytes(self, obj, encoding=None):
            stream = NativeIO()
            self.to_stream(obj, stream)
            return stream.getvalue()

        def from_bytes(self, bytes_representation, resource=None):
            stream = NativeIO(bytes_representation)
            return self.from_stream(stream, resource=resource)

        def from_string(self, string_representation, resource=None):
            buf = bytes_(string_representation, encoding=self.encoding)
            stream = NativeIO(buf)
            return self.from_stream(stream, resource=resource)

    def _make_representation_parser(self, stream, resource_class, mapping):
        parser = CsvRepresentationParser(stream, resource_class, mapping)
        parser.set_option('dialect', self.CSV_IMPORT_DIALECT)
        parser.set_option('encoding', self.encoding)
        return parser

    def _make_representation_generator(self, stream, resource_class, mapping):
        generator = CsvRepresentationGenerator(stream, resource_class, mapping)
        generator.set_option('dialect', self.CSV_EXPORT_DIALECT)
        generator.set_option('encoding', self.encoding)
        return generator


class CsvMemberDataElement(SimpleMemberDataElement):
    converter_registry = CsvConverterRegistry


class CsvCollectionDataElement(SimpleCollectionDataElement):
    pass


class CsvLinkedDataElement(SimpleLinkedDataElement):
    pass


class CsvRepresenterConfiguration(RepresenterConfiguration):
    pass


class CsvMappingRegistry(SimpleMappingRegistry):
    """
    Registry for CSV mappings.
    """
    member_data_element_base_class = CsvMemberDataElement
    collection_data_element_base_class = CsvCollectionDataElement
    linked_data_element_base_class = CsvLinkedDataElement
    configuration_class = CsvRepresenterConfiguration
