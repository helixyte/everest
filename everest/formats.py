"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 24, 2011.
"""

from everest.interfaces import (IJsonRequest,
                               IAtomRequest,
                               IXmlRequest,
                               ICsvRequest)

__docformat__ = "reStructuredText en"
__all__ = ['JSON_FORMAT',
           'ATOM_FORMAT',
           'XML_FORMAT',
           'CSV_FORMAT',
           'FORMAT_REQUEST',
           ]

JSON_FORMAT = 'json'
ATOM_FORMAT = 'atom'
XML_FORMAT = 'xml'
CSV_FORMAT = 'csv'

FORMAT_REQUEST = {JSON_FORMAT: IJsonRequest,
                  ATOM_FORMAT: IAtomRequest,
                  XML_FORMAT: IXmlRequest,
                  CSV_FORMAT: ICsvRequest,
                  }
