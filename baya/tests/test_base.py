from mock import MagicMock

from django_auth_ldap import backend
from django.contrib.auth.models import Group
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from . import directory
from ..mock_ldap_helpers import mock_ldap_setup


class LDAPGroupAuthTestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mockldap = mock_ldap_setup(
            ldap_dc='dc=test',
            extra_users=directory.test_users,
            group_lineage=directory.group_lineage)

    @classmethod
    def tearDownClass(cls):
        del cls.mockldap

    def setUp(self):
        self.mockldap.start()
        self.ldapobj = self.mockldap['ldap://localhost']

        self.backend = backend.LDAPBackend()
        self.backend.ldap  # Force global configuration

    def tearDown(self):
        self.mockldap.stop()
        del self.ldapobj

    def login(self, username):
        return self.backend.authenticate(
            self.mock_get_request(), username=username, password='password')

    def _build_mock_request(self, user=None, get=None, post=None):
        request = MagicMock()
        if user:
            request.user = user
            request.user.__dict__['is_authenticated'] = True
        else:
            request.user = AnonymousUser()
        request.GET = {}
        request.POST = {}
        request.resolver_match.kwargs = {}
        if get is not None:
            request.GET.update(get)
        if post is not None:
            request.POST.update(post)
        return request

    def mock_get_request(self, *args, **kwargs):
        request = self._build_mock_request(*args, **kwargs)
        request.method = 'GET'
        return request

    def mock_post_request(self, *args, **kwargs):
        request = self._build_mock_request(*args, **kwargs)
        request.method = 'POST'
        return request

    def assert_no_get_permission(self, user, view, get=None):
        request = self.mock_get_request(user, get=get)
        self.assertRaises(PermissionDenied, view, request)

    def assert_no_post_permission(self, user, view, get=None, post=None):
        request = self.mock_post_request(user, get=get, post=post)
        self.assertRaises(PermissionDenied, view, request)

    def assert_no_permission(self, user, view, get=None, post=None):
        self.assert_no_get_permission(user, view, get)
        self.assert_no_post_permission(user, view, get, post)

    def assert_has_get_permission(self, user, view, get=None):
        request = self.mock_get_request(user, get=get)
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def assert_has_post_permission(self, user, view, get=None, post=None):
        request = self.mock_post_request(user, get=get, post=post)
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def assert_has_permission(self, user, view, get=None, post=None):
        self.assert_has_get_permission(user, view, get)
        self.assert_has_post_permission(user, view, get, post)


class TestSetup(LDAPGroupAuthTestBase):
    def test_has_all_groups(self):
        """Verify that mockldap & django-auth-ldap are both working.

        Just checking that the has_all user gets all of the groups it's
        suppsosed to get.
        """
        group_count = Group.objects.count()
        self.login('has_all')
        group_count_2 = Group.objects.count()
        self.assertGreater(group_count_2, group_count)
        self.assertEqual(group_count_2 - group_count, 6)
