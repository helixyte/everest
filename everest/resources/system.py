"""
System resources.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Nov 22, 2011.
"""
from everest.resources.base import Member
from everest.resources.descriptors import terminal_attribute
import datetime

__docformat__ = 'reStructuredText en'
__all__ = ['UserMessageMember',
           ]


class UserMessageMember(Member):
    relation = 'message'

    text = terminal_attribute(str, 'text')
    guid = terminal_attribute(str, 'guid')
    time_stamp = terminal_attribute(datetime.datetime, 'time_stamp')
