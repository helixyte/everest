"""
Constants for the repositories package.

This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 25, 2013.
"""

__docformat__ = 'reStructuredText en'
__all__ = ['REPOSITORY_DOMAINS',
           'REPOSITORY_TYPES',
           ]


class REPOSITORY_TYPES(object):
    MEMORY = 'MEMORY'
    RDB = 'RDB'
    FILE_SYSTEM = 'FILE_SYSTEM'
    NO_SQL = 'NO_SQL'


class REPOSITORY_DOMAINS(object):
    ROOT = 'ROOT'
    SYSTEM = 'SYSTEM'
