"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Dec 18, 2013.
"""
__docformat__ = 'reStructuredText en'
__all__ = ['csv_reader',
           'csv_writer',
           'izip',
           'open_text',
           'parse_qsl',
           'BytesIO',
           'CsvDictReader',
           'CsvDictWriter'
           ]

from csv import DictReader
from csv import DictWriter
from csv import reader
from csv import writer

from pyramid.compat import PY3


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
    csv_writer = writer
    CsvDictWriter = DictWriter
else:
    from csv import excel

    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')


    class UnicodeReader(object):
        def __init__(self, f, dialect=excel, **kwargs):
            self.reader = reader(utf_8_encoder(f), dialect=dialect, **kwargs)

        def next(self):
            row = self.reader.next()
            return [unicode(cell, 'utf-8')
                    if isinstance(cell, basestring) else cell
                    for cell in row]

        @property
        def line_num(self):
            return self.reader.line_num

        def __iter__(self):
            return self


    class UnicodeDictReader(DictReader):
        def __init__(self, f, fieldnames=None, restkey=None, restval=None,
                     dialect="excel", *args, **kw):
            DictReader.__init__(self, f, fieldnames=fieldnames,
                                restkey=restkey, restval=restval,
                                dialect=dialect, *args, **kw)
            # Replace the reader with our unicode-enabled reader.
            self.reader = UnicodeReader(f, dialect=dialect, *args, **kw)


    class UnicodeWriter(object):
        def __init__(self, f, dialect=excel, **kwds):
            self.writer = writer(f, dialect=dialect, **kwds)

        def writerow(self, row):
            self.writer.writerow([cell.encode("utf-8")
                                  if isinstance(cell, basestring) else cell
                                  for cell in row])


    class UnicodeDictWriter(DictWriter):
        def __init__(self, f, fieldnames, restval="", extrasaction="raise",
                     dialect="excel", encoding='utf-8', *args, **kw):
            DictWriter.__init__(self, f, fieldnames, restval=restval,
                                extrasaction=extrasaction, dialect=dialect,
                                *args, **kw)
            # Replace the writer with our UnicodeWriter.
            self.writer = UnicodeWriter(f, dialect=dialect, encoding=encoding,
                                        *args, **kw)

    csv_reader = UnicodeReader
    CsvDictReader = UnicodeDictReader
    csv_writer = UnicodeWriter
    CsvDictWriter = UnicodeDictWriter

# pylint: enable=E0611
