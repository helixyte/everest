"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 3, 2011.
"""

from everest.exceptions import NotAnEmailAddress
from everest.utils import check_email

__docformat__ = 'reStructuredText en'
__all__ = ['validate_email',
           ]


def validate_email(value):
    if not check_email(value):
        raise NotAnEmailAddress(value) # not std exc cls pylint: disable=W0710
    return True
