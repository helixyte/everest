"""

This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jan 31, 2013.
"""
from everest.repositories.utils import commit_veto
from everest.testing import Pep8CompliantTestCase
from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPRedirection

__docformat__ = 'reStructuredText en'
__all__ = ['RepositoriesUtilsTestCase',
           ]


class RepositoriesUtilsTestCase(Pep8CompliantTestCase):
    def test_commit_veto(self):
        rsp1 = DummyResponse(HTTPOk().status, dict())
        self.assert_false(commit_veto(None, rsp1))
        rsp2 = DummyResponse(HTTPRedirection().status, dict())
        self.assert_true(commit_veto(None, rsp2))
        rsp3 = DummyResponse(HTTPRedirection().status, {'x-tm':'commit'})
        self.assert_false(commit_veto(None, rsp3))


class DummyResponse(object):
    def __init__(self, status, headers):
        self.status = status
        self.headers = headers
