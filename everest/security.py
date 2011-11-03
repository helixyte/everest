"""
This file is part of the everest project. 
See LICENSE.txt for licensing, AUTHORS.txt for contributor information.

Created on Jun 22, 2010.
"""

__docformat__ = 'reStructuredText en'
__all__ = ['remote_user_auth_policy_callback',
           ]


def remote_user_auth_policy_callback(userid, request): # pylint: disable=W0613
    groups = None
    if userid is not None:
        groups = []
    return groups
