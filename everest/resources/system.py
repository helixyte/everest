"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 22, 2011.
"""

from everest.resources.base import Member
from everest.resources.descriptors import terminal_attribute

__docformat__ = 'reStructuredText en'
__all__ = ['MessageMember',
           ]


class MessageMember(Member):
    relation = 'message'

    text = terminal_attribute(str, 'text')
