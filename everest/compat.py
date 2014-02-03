"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 18, 2013.
"""
from csv import DictReader
from csv import reader

from pyramid.compat import PY3
from pyramid.compat import binary_type


__docformat__ = 'reStructuredText en'
__all__ = ['csv_reader',
           'izip',
           'open_text',
           'parse_qsl',
           'BytesIO',
           'CsvDictReader',
           ]


# pylint: disable=E0611
if PY3:
    izip = zip
else:
    from itertools import izip

if PY3:
    from urllib import parse
    parse_qsl = parse.parse_qsl
else:
    import urlparse

    parse_qsl = urlparse.parse_qsl


if PY3:
    from io import BytesIO
else:
    from StringIO import StringIO as BytesIO


if PY3:
    def open_text(filename):
        return open(filename, 'w', newline='')
else:
    def open_text(filename):
        return open(filename, 'wb')


if PY3:
    csv_reader = reader
    CsvDictReader = DictReader
else:
    from csv import excel
    from pyramid.compat import text_type


    class UnicodeReader(object):
        """
        A CSV reader that ensures that byte strings are read as unicode under
        Python 2.7.
        """
        def __init__(self, f, dialect=excel, **kwargs):
            self.reader = reader(f, dialect=dialect, **kwargs)

        def next(self):
            row = next(self.reader)
            return [text_type(cell, 'utf-8')
                    if isinstance(cell, binary_type) else cell
                    for cell in row]

        __next__ = next

        @property
        def line_num(self):
            return self.reader.line_num

        def __iter__(self):
            return self


    class UnicodeDictReader(DictReader):
        """
        A CSV dict reader that ensures that byte strings are read as unicode
        under Python 2.7.
        """
        def __init__(self, f, fieldnames=None, restkey=None, restval=None,
                     dialect="excel", *args, **kw):
            DictReader.__init__(self, f, fieldnames=fieldnames,
                                restkey=restkey, restval=restval,
                                dialect=dialect, *args, **kw)
            # Replace the reader with our unicode-enabled reader.
            self.reader = UnicodeReader(f, dialect=dialect, *args, **kw)


    csv_reader = UnicodeReader
    CsvDictReader = UnicodeDictReader

# pylint: enable=E0611
