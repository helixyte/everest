"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 14, 2011.
"""
from everest.entities.utils import slug_from_string
from everest.testing import Pep8CompliantTestCase

__docformat__ = 'reStructuredText en'
__all__ = ['SlugTestCase',
           ]


class SlugTestCase(Pep8CompliantTestCase):

    def test_basic(self):
        str_input = 'spaces with_underscore AND CAPS'
        str_as_slug = 'spaces-with-underscore-and-caps'
        slug = slug_from_string(str_input)
        self.assert_equal(slug, str_as_slug)
