import functools
from unittest.mock import patch
from unittest.mock import sentinel
from types import FunctionType

import django
from django.conf import settings
if django.VERSION[:2] < (4, 0):
    from django.conf.urls import include
else:
    from django.urls import include
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.test.utils import override_settings
from django.views.generic import ListView

from . import nested_urls2
from .test_base import LDAPGroupAuthTestBase
from ..dynamic_roles import DjangoRequestGroupFormatter
from ..membership import RolesNode as g
from ..membership import DynamicRolesNode as dg
from ..permissions import Gate
from ..permissions import requires
from ..permissions import DENY_ALL
from ..visitors import PermissionChecker
from ..utils import has_permission

A = g('a')
AA = g('aa')
AAA = g('aaa')
B = g('b')


class TestGate(LDAPGroupAuthTestBase):
    def setUp(self):
        super(TestGate, self).setUp()
        self.has_all = self.login('has_all')
        self.request_has_all = self.mock_get_request(self.has_all)
        self.has_aaa = self.login('has_aaa')
        self.request_has_aaa = self.mock_get_request(self.has_aaa)

    def _has_permissions(self, node, roles):
        return PermissionChecker(roles).visit(node)

    def test_case_insensitive(self):
        """Groups should be case insensitive."""
        self.assertEqual(g('A'), g('a'))
        self.assertTrue(self._has_permissions(g('A'), ['A']))
        self.assertTrue(self._has_permissions(g('A'), ['a']))
        self.assertTrue(self._has_permissions(g('a'), ['A']))
        self.assertTrue(self._has_permissions(g('a'), ['a']))

    def _test_perms(self, gate, has_all_perm, has_aaa_perm, method=None):
        if method == 'get':
            perm = 'has_get_permission'
        elif method == 'post':
            perm = 'has_post_permission'
        else:
            perm = 'has_any_permission'
        self.assertEqual(getattr(gate, perm)(self.request_has_all),
                         has_all_perm)
        self.assertEqual(getattr(gate, perm)(self.request_has_aaa),
                         has_aaa_perm)

    def test_no_permissions(self):
        """If no permissions declared, always allow."""
        gate = Gate()
        self._test_perms(gate, True, True, 'get')
        self._test_perms(gate, True, True, 'post')
        self._test_perms(gate, True, True)

    def test_simple_and(self):
        gate = Gate()
        gate.get_requires &= A
        gate.post_requires &= A
        self._test_perms(gate, True, False, 'get')
        self._test_perms(gate, True, False, 'post')
        self._test_perms(gate, True, False)

        gate.get_requires &= AAA
        gate.post_requires &= AAA
        self._test_perms(gate, True, False, 'get')
        self._test_perms(gate, True, False, 'post')
        self._test_perms(gate, True, False)

    def test_true_node(self):
        """
        Default x_requires is TrueNode(), so or-ing with it is always True.
        """
        gate = Gate()
        gate.get_requires |= g('nothing')
        gate.post_requires |= g('nothing')
        self._test_perms(gate, True, True, 'get')
        self._test_perms(gate, True, True, 'post')
        self._test_perms(gate, True, True)

    def test_simple_or(self):
        gate = Gate(get_requires=A, post_requires=A)
        self._test_perms(gate, True, False, 'get')
        self._test_perms(gate, True, False, 'post')
        self._test_perms(gate, True, False)
        gate.get_requires |= AAA
        self._test_perms(gate, True, True, 'get')
        self._test_perms(gate, True, False, 'post')
        self._test_perms(gate, True, True)
        gate.get_requires &= B
        gate.post_requires &= B
        self._test_perms(gate, True, False, 'get')
        self._test_perms(gate, True, False, 'post')
        self._test_perms(gate, True, False)

    def test_post_requires(self):
        """Ensure the post_requires doesn't collide with get_requires."""
        gate = Gate(post_requires=A)
        self._test_perms(gate, True, True, 'get')
        self._test_perms(gate, True, False, 'post')
        self._test_perms(gate, True, True)
        gate.post_requires |= AAA
        self._test_perms(gate, True, True, 'get')
        self._test_perms(gate, True, True, 'post')
        self._test_perms(gate, True, True)

    def test_get_requires(self):
        """Ensure the get_requires doesn't collide with post_requires."""
        gate = Gate(get_requires=A)
        self._test_perms(gate, True, False, 'get')
        self._test_perms(gate, True, True, 'post')
        self._test_perms(gate, True, True)
        gate.get_requires |= AAA
        self._test_perms(gate, True, True, 'get')
        self._test_perms(gate, True, True, 'post')
        self._test_perms(gate, True, True)

    def test_all_requires(self):
        gate = Gate(A)
        self._test_perms(gate, True, False, 'get')
        self._test_perms(gate, True, False, 'post')
        self._test_perms(gate, True, False)

    def test_all_and_post_requires(self):
        gate = Gate(AAA, post_requires=A)
        self._test_perms(gate, True, True, 'get')
        self._test_perms(gate, True, False, 'post')
        self._test_perms(gate, True, True)

    def test_all_and_get_and_post_requires(self):
        gate = Gate(AAA, get_requires=AAA, post_requires=A)
        self._test_perms(gate, True, True, 'get')
        self._test_perms(gate, True, False, 'post')
        self._test_perms(gate, True, True)
        self.assertFalse(gate.get_requires is gate.post_requires)

    def test_redirect(self):
        g1 = Gate()
        self.assertEqual(g1.login_url, settings.BAYA_LOGIN_URL)
        g2 = Gate(login_url=None)
        self.assertEqual(g2.login_url, settings.BAYA_LOGIN_URL)
        custom_login = "/testlogin/"
        g3 = Gate(login_url=custom_login)
        self.assertEqual(g3.login_url, custom_login)
        self.assertEqual(str((g3 + g2).login_url),
                         str(custom_login))
        self.assertEqual((g2 + g3).login_url, custom_login)
        with override_settings(BAYA_LOGIN_URL="/testlogin/"):
            g4 = Gate()
            self.assertEqual(g4.login_url, "/testlogin/")
        with override_settings(BAYA_LOGIN_URL=None):
            g5 = Gate()
            self.assertEqual(g5.login_url, "/login/")

    def test_lazy_login_url(self):
        lazy_login_url = reverse_lazy('lazy_login')
        gate = Gate(login_url=lazy_login_url)
        self.assertEqual(gate.login_url, lazy_login_url)
        self.assertEqual(str(gate.login_url), '/lazy_login/')

    def test_non_existent_group(self):
        """If you require a non-existent group, then nobody can authorize."""
        gate = Gate(g('nonexistent'))
        self._test_perms(gate, False, False, 'get')
        self._test_perms(gate, False, False, 'post')
        self._test_perms(gate, False, False)


class TestDeniedReason(LDAPGroupAuthTestBase):
    def test_not_logged_in(self):
        gate = Gate()
        request = self.mock_get_request()
        data = gate.get_permissions_required_data(request)
        self.assertEqual(data['requires_groups'], g())
        self.assertEqual(data['requires_groups_str'], "{}")
        self.assertEqual(data['user_groups'], [])
        self.assertEqual(data['user_groups_str'], "{}")

    def test_insufficient_permissions(self):
        gate = Gate(AA | A)
        request = self.mock_get_request(self.login('has_aaa'))
        data = gate.get_permissions_required_data(request)
        self.assertEqual(data['requires_groups'], AA | A)
        self.assertEqual(data['requires_groups_str'], "{aa} | {a}")
        self.assertEqual(data['user_groups'], ['aaa'])
        self.assertEqual(data['user_groups_str'], "{aaa}")


class MyListView(ListView):
    pass


@requires(B, get=AAA, post=AA)
def my_view(request):
    return HttpResponse('my_view response')


def undecorated_view(request):
    return HttpResponse('undecorated_view response')


class TestRequires(LDAPGroupAuthTestBase):
    def test_str(self):
        """If given a string, convert to a PermissionNode."""
        req = requires('a')
        self.assertEqual(req.gate.get_requires, A)
        req = requires(['a', 'b'])
        self.assertEqual(req.gate.get_requires, A & B)
        req = requires('a, b')
        self.assertEqual(req.gate.get_requires, A & B)

    def test_no_denied_not_logged_in(self):
        """A user can access unprotected views when not logged in."""
        call = requires(post=AA)(undecorated_view)
        self.assert_has_get_permission(None, call)
        # The test for POSTing as a non-logged-in user is covered in
        # test_redirect
        self.assert_has_get_permission(self.login('has_b'), call)
        self.assert_no_post_permission(self.login('has_b'), call)
        self.assert_has_permission(self.login('has_a'), call)

    def test_no_collision(self):
        """Multiple requires calls in different URLs shouldn't interact."""
        call1 = requires(AA)(undecorated_view)
        call2 = requires(B)(undecorated_view)
        self.assertFalse(hasattr(undecorated_view, '_gate'))
        self.assertNotEqual(call1._gate, call2._gate)

        self.assert_no_permission(self.login('has_aaa'), call1)
        self.assert_no_permission(self.login('has_b'), call1)
        self.assert_has_permission(self.login('has_aa'), call1)
        self.assert_has_permission(self.login('has_all'), call1)

        self.assert_no_permission(self.login('has_aaa'), call2)
        self.assert_no_permission(self.login('has_aa'), call2)
        self.assert_has_permission(self.login('has_b'), call2)
        self.assert_has_permission(self.login('has_all'), call2)

    def test_url_wrapping_syntax(self):
        """Test the syntax for decorating a url pattern."""
        decorated = requires(get=AA, post=g('nobody'))(undecorated_view)
        self.assertTrue(hasattr(decorated, '_gate'))
        self.assertTrue(isinstance(decorated._gate, Gate))
        self.assertEqual(type(decorated), FunctionType)
        self.assertEqual(decorated._gate.get_requires, AA)
        self.assert_has_get_permission(self.login('has_aa'), decorated)
        self.assert_has_get_permission(self.login('has_all'), decorated)
        self.assert_no_get_permission(self.login('has_aaa'), decorated)
        self.assert_no_post_permission(self.login('has_aa'), decorated)
        self.assert_no_post_permission(self.login('has_aaa'), decorated)
        self.assert_no_post_permission(self.login('has_all'), decorated)

    def test_method_view_has_gate(self):
        """Test decorating a regular method view."""
        self.assertTrue(hasattr(my_view, '_gate'))
        self.assertTrue(isinstance(my_view._gate, Gate))
        self.assertEqual(type(my_view), FunctionType)
        exclude = requires(g('nobody'))(my_view)
        self.assert_has_get_permission(self.login('has_all'), my_view)
        self.assert_no_get_permission(self.login('has_all'), exclude)
        self.assert_has_post_permission(self.login('has_all'), my_view)
        self.assert_no_post_permission(self.login('has_all'), exclude)

        self.assert_no_get_permission(self.login('has_aaa'), my_view)
        self.assert_no_get_permission(self.login('has_aaa'), exclude)
        self.assert_no_post_permission(self.login('has_aaa'), my_view)
        self.assert_no_post_permission(self.login('has_aaa'), exclude)

        self.assert_no_get_permission(self.login('has_aa'), my_view)
        self.assert_no_get_permission(self.login('has_aa'), exclude)
        self.assert_no_post_permission(self.login('has_aa'), my_view)
        self.assert_no_post_permission(self.login('has_aa'), exclude)

    def test_class_view_fails(self):
        """Test decorating a CBV."""
        self.assertRaises(TypeError, requires(A), MyListView)

    def test_class_view_as_view_method(self):
        """Ensure that the as_view() method can be decorated."""
        view = MyListView.as_view()
        decorated1 = requires(g('one'))(view)
        decorated2 = requires(g('two'))(view)
        self.assertFalse(decorated1 is view)
        self.assertTrue(hasattr(decorated1, '_gate'))
        self.assertNotEqual(decorated1._gate, decorated2._gate)

    def test_functools_partial(self):
        """Test that a functools.partial is able to be decorated."""
        def pseudoview(request, foo):
            pass

        view = functools.partial(pseudoview, foo=1)
        functools.update_wrapper(view, pseudoview)

        decorated1 = requires(g('one'))(view)
        decorated2 = requires(g('two'))(view)
        self.assertFalse(decorated1 is view)
        self.assertTrue(hasattr(decorated1, '_gate'))
        self.assertNotEqual(decorated1._gate, decorated2._gate)

    def test_multiple(self):
        # B is anded with the others
        decorated1 = requires(B, get=AAA, post=AA)(undecorated_view)
        self.assertEqual(decorated1._gate.post_requires, B & AA)
        self.assert_no_get_permission(self.login('has_b'), decorated1)
        self.assert_no_post_permission(self.login('has_b'), decorated1)
        self.assert_no_get_permission(self.login('has_aaa'), decorated1)
        self.assert_no_post_permission(self.login('has_aaa'), decorated1)
        self.assert_has_get_permission(self.login('has_all'), decorated1)
        self.assert_has_post_permission(self.login('has_all'), decorated1)

        decorated2 = requires(get=(AAA | B), post=(AA | B))(
            undecorated_view)
        self.assertEqual(decorated2._gate.get_requires, AAA | B)
        self.assertEqual(decorated2._gate.post_requires, AA | B)

        decorated2 = requires(A, get=(AAA | B), post=(AA | B))(
            undecorated_view)
        self.assertEqual(decorated2._gate.get_requires, A & (AAA | B))
        self.assertEqual(decorated2._gate.post_requires, A & (AA | B))

    def test_chaining(self):
        decorated1 = requires(A)(undecorated_view)
        decorated2 = requires(B)(decorated1)
        self.assertNotEqual(decorated1._gate, decorated2._gate)
        self.assert_has_permission(self.login('has_a'), decorated1)
        self.assert_no_permission(self.login('has_a'), decorated2)
        # B doesn't have access to either, because decorated1 still requires A
        self.assert_no_permission(self.login('has_b'), decorated1)
        self.assert_no_permission(self.login('has_b'), decorated2)
        # But has_all does have access because it has both A and B
        self.assert_has_permission(self.login('has_all'), decorated2)

    def test_chain_user_has_permission(self):
        decorated1 = requires(A)(undecorated_view)
        decorated2 = requires(B)(decorated1)
        for perm in ['get', 'post', 'any']:
            self.assertTrue(
                has_permission(decorated1, self.login('has_a'), perm))
            self.assertFalse(
                has_permission(decorated2, self.login('has_a'), perm))
            self.assertFalse(
                has_permission(decorated1, self.login('has_b'), perm))
            self.assertFalse(
                has_permission(decorated2, self.login('has_b'), perm))
            self.assertTrue(
                has_permission(decorated1, self.login('has_a_b'), perm))
            self.assertTrue(
                has_permission(decorated2, self.login('has_a_b'), perm))

    def test_redirect(self):
        url = "url"
        decorated = requires(B, get=AAA, post=AA)(undecorated_view)
        self.assertEqual(decorated._gate.login_url, settings.LOGIN_URL)
        decorated = requires(B, login_url=url, get=AAA, post=AA)(
            undecorated_view)
        self.assertEqual(decorated._gate.login_url, url)

        with patch('django.contrib.auth.views.redirect_to_login',
                   return_value=sentinel) as do_redirect:
            request = self.mock_get_request()
            redirect = decorated(request)
            do_redirect.assert_called_once_with(request.get_full_path(), url)
        self.assertIs(redirect, sentinel)

    def test_str_view_path(self):
        """Test decorating a string path to a view throws an exception."""
        self.assertRaises(
            TypeError, requires(A), 'baya.tests.views.my_view')

    def test_include(self):
        """Make sure requires(A)(include(my_app.urls)) works."""
        decorated_include = requires(A)(include(nested_urls2))
        for pattern in decorated_include[0].urlpatterns:
            [cell] = [cell for cell in pattern.resolve.__closure__
                      if isinstance(cell.cell_contents, requires)]
            requirer = cell.cell_contents
            self.assertTrue(
                PermissionChecker(['a']).visit(requirer.gate.get_requires))
            self.assertTrue(
                PermissionChecker(['a']).visit(requirer.gate.post_requires))

    def test_deny_all(self):
        def _no_perms(method):
            self.assert_no_get_permission(self.login('has_all'), method)
            self.assert_no_post_permission(self.login('has_all'), method)

        call = requires(DENY_ALL)(undecorated_view)
        _no_perms(call)

        call = requires(AA & DENY_ALL)(undecorated_view)
        _no_perms(call)

        call = requires(AA | DENY_ALL)(undecorated_view)
        self.assert_has_get_permission(self.login('has_all'), call)
        self.assert_has_post_permission(self.login('has_all'), call)


class TestRequiresDynamic(LDAPGroupAuthTestBase):
    def test_dynamic_str(self):
        dynamic_group = dg(DjangoRequestGroupFormatter("%s_admin", 'group'))
        decorated1 = requires(dynamic_group)(undecorated_view)

        self.assert_no_permission(
            self.login('has_a'), decorated1, {'group': 'A'})
        self.assert_no_permission(
            self.login('has_b'), decorated1, {'group': 'A'})
        self.assert_has_permission(
            self.login('has_all'), decorated1, {'group': 'A'})

    def test_dynamic_and_regular(self):
        dynamic_group = dg(DjangoRequestGroupFormatter("%s_admin", 'group'))
        regular_group = AA
        decorated1 = requires(dynamic_group & regular_group)(undecorated_view)

        self.assert_no_permission(
            self.login('has_a'), decorated1, {'group': 'A'})
        self.assert_no_permission(
            self.login('has_aa'), decorated1, {'group': 'A'})
        self.assert_no_permission(
            self.login('has_b'), decorated1, {'group': 'A'})
        self.assert_has_permission(
            self.login('has_all'), decorated1, {'group': 'A'})

    def test_dynamic_self_and_not_self(self):
        dynamic_group = dg(DjangoRequestGroupFormatter("%s_admin", 'group'))
        # No user will have access to A & ~A
        decorated = requires(dynamic_group & ~dynamic_group)(undecorated_view)
        self.assert_no_permission(
            self.login('has_a'), decorated, {'group': 'A'})
        self.assert_no_permission(
            self.login('has_all'), decorated, {'group': 'A'})

    def test_dynamic_or_regular(self):
        dynamic_group = dg(DjangoRequestGroupFormatter("%s_admin", 'group'))
        regular_group = AA
        decorated1 = requires(dynamic_group | regular_group)(undecorated_view)

        self.assert_has_permission(
            self.login('has_a'), decorated1, {'group': 'A'})
        self.assert_has_permission(
            self.login('has_aa'), decorated1, {'group': 'A'})
        self.assert_no_permission(
            self.login('has_b'), decorated1, {'group': 'A'})
        self.assert_has_permission(
            self.login('has_all'), decorated1, {'group': 'A'})
