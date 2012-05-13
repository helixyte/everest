"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Apr 26, 2012.
"""

__docformat__ = 'reStructuredText en'
__all__ = ['ResourceKinds',
           ]


class ResourceKinds(object):
    """
    Static container for resource kind constants.

    We have two kinds of resource:
        MEMBER :
            a member resource
        COLLECTION :
            a collection resource
    """
    MEMBER = 'MEMBER'
    COLLECTION = 'COLLECTION'
