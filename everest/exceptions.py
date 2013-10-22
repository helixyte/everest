"""
Custom exceptions.

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 13, 2010.
"""
__docformat__ = 'reStructuredText en'
__all__ = ['MultipleResultsException',
           'NoResultsException',
           'UnsupportedOperationException',
           ]


class UnsupportedOperationException(Exception):
    """
    Raise this to indicate that the requested operation is not supported.
    """


class NoResultsException(Exception):
    """
    Raised when no result was found when at least one was expected.
    """


class MultipleResultsException(Exception):
    """
    Raised when more than one item was found where at most one was expected. 
    """

