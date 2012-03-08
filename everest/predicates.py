"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jun 22, 2010.
"""

from everest.views.static import public_view
from pyramid.settings import get_settings
import os

__docformat__ = 'reStructuredText en'
__all__ = ['public_path_exists',
           ]


def public_path_exists(context, request): # pylint: disable=W0613
    settings = get_settings()
    public_dir = settings[public_view.PUBLIC_DIR]
    file_path = os.path.join(public_dir, request.path[1:])
    return os.path.exists(file_path)
