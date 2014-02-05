"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 31, 2014.
"""
from everest.querying.refsparser import parse_refs
from everest.representers.config import IGNORE_OPTION
from everest.representers.config import WRITE_AS_LINK_OPTION
from everest.testing import TestCaseWithConfiguration

__docformat__ = 'reStructuredText en'
__all__ = ['LinksParserTestCase',
           ]


class LinksParserTestCase(TestCaseWithConfiguration):
    def test_one_link(self):
        data = [('foo:URL', [(('foo',), {WRITE_AS_LINK_OPTION:True,
                                         IGNORE_OPTION:False})
                             ]
                 ),
                ('foo:INLINE', [(('foo',), {WRITE_AS_LINK_OPTION:False,
                                            IGNORE_OPTION:False})
                                ]
                 ),
                ('foo:OFF', [(('foo',), {IGNORE_OPTION:True})
                             ]
                 ),
                ('foo.bar:URL', [(('foo',), {WRITE_AS_LINK_OPTION:False,
                                             IGNORE_OPTION:False}),
                                 (('foo', 'bar'), {WRITE_AS_LINK_OPTION:True,
                                                   IGNORE_OPTION:False})
                                 ]
                 )
                ]
        for (expr, expected) in data:
            result = parse_refs(expr)
            self.assert_true(isinstance(result, dict))
            for item in expected:
                (key, opts) = item
                self.assert_true(key in result)
                self.assert_equal(result[key], opts)
