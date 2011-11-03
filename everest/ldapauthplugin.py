"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Jul 7, 2011.
"""

from repoze.who.interfaces import IAuthenticator # pylint: disable=E0611,F0401
from threading import Lock
from zope.interface import implements # pylint: disable=E0611,F0401
import ldap

__docformat__ = 'reStructuredText en'
__all__ = ['LDAPAuthPlugin',
           'make_plugin',
           ]


class LDAPAuthPlugin(object):
    """
    LDAP authentication plugin
    """

    implements(IAuthenticator)

    def __init__(self, ldapconn, ldapbase):
        """Constructor

        :param ldap_conn: An LDAP connection.
        :type ldap_conn: :class:`ldap.ldapobject.SimpleLDAPObject`
        :param ldap_base: The base for the Distinguished Name
        :type ldap_base: str
        """
        self.ldapconn = ldapconn
        self.ldapbase = ldapbase
        self._lock = Lock()

    def authenticate(self, environ, identity): # pylint: disable=W0613
        """Return the username.

        :return: The username, if the credentials are valid.
        :rtype: str or None
        """
        if not ('login' in identity and 'password' in identity):
            return None
        self._lock.acquire()
        try:
            results = self.ldapconn.search_s(self.ldapbase,
                                              ldap.SCOPE_SUBTREE,
                                              '(uid=%s)' % identity['login'])
            if len(results) != 1 or len(identity['password']) == 0:
                # LDAP NOT Authenticated - WRONG USERNAME or EMPTY PASSWORD
                return None
            dn = results[0][0]
            try:
                self.ldapconn.simple_bind_s(dn, identity['password'])
            except ldap.INVALID_CREDENTIALS:
                # LDAP NOT Authenticated - WRONG PASSWORD
                return None
            # LDAP Authenticated
            return identity['login']
        finally:
            self._lock.release()


def make_plugin(ldapuri, ldapbase):
    ldapconn = ldap.initialize(ldapuri)
    plugin = LDAPAuthPlugin(ldapconn, ldapbase)
    return plugin
