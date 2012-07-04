"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 13, 2010.
"""
__docformat__ = 'reStructuredText en'
__all__ = ['DuplicateError',
           'UnsupportedOperationException',
           ]


class UnsupportedOperationException(Exception):
    """
    Raise this to indicate that the requested operation is not supported.
    """


class DuplicateException(Exception):
    """
    Raised when more than one item was found where one was expected. 
    """

