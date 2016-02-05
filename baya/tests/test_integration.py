from distutils.version import StrictVersion

from django import get_version as get_django_version
from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from baya.tests.test_base import LDAPGroupAuthTestBase
from baya.tests.models import Blag
from baya.tests.models import PhotoBlagEntry
from baya.tests.submod.models import Comment


OK = 200
MOVED = 302
DENIED = 403
NOT_FOUND = 404


class _IntegrationBase(LDAPGroupAuthTestBase):
    """Make actual Django requests to make sure everything functions.

    We can't use the RequestFactory because the access control is at the
    URL level, and the RF doesn't go through that.
    """
    def get_client(self, username=None, password='password'):
        client = self.client
        if username:
            self.assertTrue(
                client.login(username=username, password=password))
        return client

    def _get_and_assert_access(
            self, url_name, username, target_status_code,
            reverse_args=[], reverse_kwargs={}, message=''):
        client = self.get_client(username)
        url = reverse(url_name, args=reverse_args, kwargs=reverse_kwargs)
        response = client.get(url)
        self.assertEqual(
            response.status_code,
            target_status_code,
            '%s != %s, %s' % (response.status_code, target_status_code,
                              message))
        return response


class TestIntegration(_IntegrationBase):
    def _test_login_redirect(
            self, url_name, username, target_status_code, login_url='login'):
        client = self.get_client()
        url = reverse(url_name)
        response = client.get(url)
        self.assertRedirects(
            response, "%s?next=%s" % (reverse(login_url), url))
        login_response = client.post(
            response['Location'],
            {'username': username, 'password': 'password'})
        self.assertRedirects(
            login_response, url, target_status_code=target_status_code)
        client.logout()

    def test_login_redirect(self):
        self._test_login_redirect('index', 'has_a', OK)
        self._test_login_redirect('index', 'has_aa', OK)
        self._test_login_redirect('index', 'has_aaa', DENIED)
        self._test_login_redirect('index', 'has_b', DENIED)

    def test_lazy_login_url_redirect(self):
        self._test_login_redirect(
            'lazy_login_my_view', 'has_a', OK, login_url='lazy_login')

    def test_verbs(self):
        """Test GET, HEAD, PUT, POST, PATCH, OPTIONS."""
        def _has_method(client, method):
            verb = getattr(client, method)
            response = verb(url)
            self.assertEqual(
                response.status_code, OK,
                "Error %s: %s not allowed" % (response.status_code, method))

        def _has_not_method(client, method):
            verb = getattr(client, method)
            response = verb(url)
            self.assertEqual(
                response.status_code, DENIED,
                "Error %s: %s allowed" % (response.status_code, method))

        url = reverse('my_view')

        client = self.get_client('has_a')
        GET_METHODS = ['get', 'head', 'options']
        POST_METHODS = ['put', 'post', 'delete']
        for method in (GET_METHODS + POST_METHODS):
            _has_method(client, method)

        client = self.get_client('has_aa')
        for method in GET_METHODS:
            _has_method(client, method)
        for method in POST_METHODS:
            _has_not_method(client, method)

        client = self.get_client('has_aaa')
        for method in (GET_METHODS + POST_METHODS):
            _has_not_method(client, method)

    def test_index(self):
        blag = Blag.objects.create(name="my blag")
        response = self._get_and_assert_access('index', 'has_all', OK)
        self.assertContains(response, blag.name)

    def test_my_view_str(self):
        """Test a decorated view method works when resolved by string path."""
        self._get_and_assert_access('my_view_str', 'has_all', OK)
        self._get_and_assert_access('my_view_str', 'has_aaa', DENIED)
        self._get_and_assert_access('my_view_str', 'has_b', DENIED)

    def test_my_view(self):
        """Ensure a decorated view method works."""
        self._get_and_assert_access('my_view', 'has_all', OK)
        self._get_and_assert_access('my_view', 'has_aa', OK)
        self._get_and_assert_access('my_view', 'has_aaa', DENIED)
        self._get_and_assert_access('my_view', 'has_b', DENIED)

    @override_settings(BAYA_ALLOW_ALL=True)
    def test_allow_all(self):
        """Ensure a decorated view method works."""
        self._get_and_assert_access('my_view', 'has_all', OK)
        self._get_and_assert_access('my_view', 'has_aa', OK)
        self._get_and_assert_access('my_view', 'has_aaa', OK)
        self._get_and_assert_access('my_view', 'has_b', OK)

    def test_my_undecorated_view(self):
        """Ensure url decoration works on an undecorated view method."""
        self._get_and_assert_access('my_undecorated_view', 'has_all', OK)
        self._get_and_assert_access('my_undecorated_view', 'has_aaa', DENIED)
        self._get_and_assert_access('my_undecorated_view', 'has_b', DENIED)

    def test_nested_my_view(self):
        """
        Decorating an entire include should work and check all permissions.
        """
        self._get_and_assert_access('nested1_my_view', 'has_all', OK)
        self._get_and_assert_access('nested1_my_view', 'has_a', OK)
        self._get_and_assert_access('nested1_my_view', 'has_aa', OK)
        self._get_and_assert_access('nested1_my_view', 'has_aaa', DENIED)
        self._get_and_assert_access('nested1_my_view', 'has_b', DENIED)

    def test_nested_namespaced_my_view(self):
        """
        Decorating an entire include should work and check all permissions.
        """
        self._get_and_assert_access(
            'nested-ns:nested1_my_view', 'has_all', OK)
        self._get_and_assert_access(
            'nested-ns:nested1_my_view', 'has_a', OK)
        self._get_and_assert_access(
            'nested-ns:nested1_my_view', 'has_aa', OK)
        self._get_and_assert_access(
            'nested-ns:nested1_my_view', 'has_aaa', DENIED)
        self._get_and_assert_access(
            'nested-ns:nested1_my_view', 'has_b', DENIED)

    def test_nested_my_undecorated_view(self):
        self._get_and_assert_access(
            'nested1_my_undecorated_view', 'has_all', OK)
        self._get_and_assert_access(
            'nested1_my_undecorated_view', 'has_a', OK)
        self._get_and_assert_access(
            'nested1_my_undecorated_view', 'has_aa', OK)
        self._get_and_assert_access(
            'nested1_my_undecorated_view', 'has_aaa', DENIED)

    def test_nested_nested_my_view(self):
        self._get_and_assert_access('nested_nested_my_view', 'has_all', OK)
        self._get_and_assert_access('nested_nested_my_view', 'has_a', OK)
        self._get_and_assert_access('nested_nested_my_view', 'has_aa', OK)
        self._get_and_assert_access('nested_nested_my_view', 'has_aaa', DENIED)
        self._get_and_assert_access('nested_nested_my_view', 'has_b', DENIED)

    def test_nested_nested_my_undecorated_view(self):
        self._get_and_assert_access(
            'nested_nested_my_undecorated_view', 'has_all', OK)
        self._get_and_assert_access(
            'nested_nested_my_undecorated_view', 'has_a', OK)
        self._get_and_assert_access(
            'nested_nested_my_undecorated_view', 'has_aa', DENIED)
        self._get_and_assert_access(
            'nested_nested_my_undecorated_view', 'has_aaa', DENIED)
        self._get_and_assert_access(
            'nested_nested_my_undecorated_view', 'has_b', DENIED)

    def test_query_param(self):
        self._get_and_assert_access(
            'query_param_view', 'has_b', DENIED, reverse_kwargs={'name': 'a'})
        self._get_and_assert_access(
            'query_param_view', 'has_a', OK, reverse_kwargs={'name': 'a'})
        self._get_and_assert_access(
            'query_param_view', 'has_aa', DENIED, reverse_kwargs={'name': 'a'})
        self._get_and_assert_access(
            'query_param_view', 'has_aa', OK, reverse_kwargs={'name': 'aa'})


class TestAdminIntegration(_IntegrationBase):
    def test_admin_view_uses_baya(self):
        # Default django admin_view returns a 200, not a 403
        client = self.get_client('has_nothing')
        url = reverse('admin:index')
        response = client.get(url)
        self.assertEqual(response.status_code, 403)
        # Ensure that baya_requires was set on the request
        self.assertTrue(hasattr(response.context['request'], 'baya_requires'))
        # And that it's in the 403 template
        self.assertIn(
            "<b>{aaa} &amp; True | {aa} &amp; True | {aa} | {b}</b>",
            response.content)

    def test_index(self):
        for url, reverse_kwargs in [
                ('admin:index', {}),
                ('admin:app_list', {'app_label': 'tests'})]:
            response = self._get_and_assert_access(
                url, 'has_all', OK, reverse_kwargs=reverse_kwargs)
            self.assertContains(response, 'Blags')
            self.assertContains(response, 'Entries')
            if 'index' in url:
                self.assertContains(response, 'Comments')
            else:
                self.assertNotContains(response, 'Comments')

            response = self._get_and_assert_access(
                url, 'has_aaa', OK, reverse_kwargs=reverse_kwargs)
            self.assertContains(response, 'Blags')
            self.assertNotContains(response, 'Entries')
            self.assertNotContains(response, 'Comments')

            if 'index' in url:
                # B just sees an empty admin page, following the normal
                # django behavior
                response = self._get_and_assert_access(
                    url, 'has_b', OK, reverse_kwargs=reverse_kwargs,
                    message=url)
                self.assertNotContains(response, 'Blags')
                self.assertNotContains(response, 'Entries')
                self.assertContains(response, 'Comments')
            else:
                # In django <1.7 B gets a 404 for app_list.
                # In django >=1.7 B get sa 403, like you'd expect
                if StrictVersion('1.7.0') <= StrictVersion(
                        get_django_version()):
                    expected_status = DENIED
                else:
                    expected_status = NOT_FOUND
                response = self._get_and_assert_access(
                    url, 'has_b', expected_status,
                    reverse_kwargs=reverse_kwargs,
                    message=url)

    def _get_form_data(self):
        return {
            'blagentry_set-TOTAL_FORMS': u'3',  # 3 extra forms for inlines
            'blagentry_set-INITIAL_FORMS': u'0',
            'blagentry_set-MAX_NUM_FORMS': u'',
            'photoblagentry_set-TOTAL_FORMS': u'3',
            'photoblagentry_set-INITIAL_FORMS': u'0',
            'photoblagentry_set-MAX_NUM_FORMS': u'',
        }

    def test_add(self):
        response = self._get_and_assert_access(
            'admin:tests_blag_add', 'has_all', OK)
        # aaa can't access the 'add' page
        self._get_and_assert_access(
            'admin:tests_blag_add', 'has_aaa', DENIED)

        add_url = reverse('admin:tests_blag_add')
        changelist_url = reverse('admin:tests_blag_changelist')

        blag_count = Blag.objects.count()
        client = self.get_client('has_all')
        data = self._get_form_data()
        data.update({'name': 'has_all blag'})
        response = client.post(add_url, data)
        self.assertRedirects(response, changelist_url)
        self.assertEqual(Blag.objects.count(), blag_count + 1)
        # And the POST is rejected too
        client = self.get_client('has_aaa')
        response = client.post(add_url, {'name': 'has_aaa blag'})
        self.assertEqual(response.status_code, DENIED)
        self.assertEqual(Blag.objects.count(), blag_count + 1)

    def test_changelist_view(self):
        self._get_and_assert_access(
            'admin:tests_blag_changelist', 'has_all', OK)
        # AAA can view the changelist
        self._get_and_assert_access(
            'admin:tests_blag_changelist', 'has_aaa', OK)
        self._get_and_assert_access(
            'admin:tests_blag_changelist', 'has_b', DENIED)

    def test_read_not_update(self):
        self._get_and_assert_access(
            'admin:submod_comment_changelist', 'has_b', OK)
        comment = Comment.objects.create(body="abc")
        args = [comment.id]
        self._get_and_assert_access(
            'admin:submod_comment_change', 'has_b', OK, reverse_args=args)
        # But B can't actually change anything
        change_url = reverse('admin:submod_comment_change', args=args)
        client = self.get_client('has_b')
        response = client.post(
            change_url, {'id': '%s' % comment.id, 'body': 'syke'})
        self.assertEqual(response.status_code, DENIED)

    def test_changelist_post(self):
        changelist_url = reverse('admin:tests_blag_changelist')
        blag = Blag.objects.create(name="blagonet")
        blag_count = Blag.objects.count()
        delete_kwargs = {
            'action': ['delete_selected'],
            'select_across': ['0'],
            '_selected_action': ['%s' % blag.id],
            'index': ['0'],
            'post': ['yes'],
        }

        # But AAA can't actually change anything
        client = self.get_client('has_aaa')
        response = client.post(changelist_url, delete_kwargs)
        self.assertEqual(response.status_code, DENIED)
        self.assertEqual(Blag.objects.count(), blag_count)

        client = self.get_client('has_all')
        response = client.post(changelist_url, delete_kwargs)
        self.assertRedirects(response, changelist_url)
        self.assertEqual(Blag.objects.count(), blag_count - 1)

    def test_change_view(self):
        blag = Blag.objects.create(name="blagonet")
        args = [blag.id]

        self._get_and_assert_access(
            'admin:tests_blag_change', 'has_all', OK, reverse_args=args)
        # AAA Can view this page...
        self._get_and_assert_access(
            'admin:tests_blag_change', 'has_aaa', OK, reverse_args=args)
        self._get_and_assert_access(
            'admin:tests_blag_change', 'has_b', DENIED, reverse_args=args)

    def test_change_post(self):
        blag = Blag.objects.create(name="blagonet")
        change_url = reverse('admin:tests_blag_change', args=[blag.id])
        changelist_url = reverse('admin:tests_blag_changelist')

        client = self.get_client('has_all')
        data = self._get_form_data()
        data.update({
            'id': '%s' % blag.id,
            'name': 'new name',
        })
        response = client.post(change_url, data)
        self.assertRedirects(response, changelist_url)
        self.assertEqual(Blag.objects.get(id=blag.id).name, 'new name')

        # ...but AAA Cannot actually change anything
        client = self.get_client('has_aaa')
        response = client.post(
            change_url, {'id': '%s' % blag.id, 'name': 'newer name'})
        self.assertEqual(response.status_code, DENIED)

    def test_delete_view(self):
        blag = Blag.objects.create(name="blagonet")
        args = [blag.id]

        self._get_and_assert_access(
            'admin:tests_blag_delete', 'has_all', OK, reverse_args=args)
        # AAA Can view this page...
        self._get_and_assert_access(
            'admin:tests_blag_delete', 'has_aaa', DENIED, reverse_args=args)
        self._get_and_assert_access(
            'admin:tests_blag_delete', 'has_b', DENIED, reverse_args=args)

    def test_delete_post(self):
        blag = Blag.objects.create(name="blagonet")
        delete_url = reverse('admin:tests_blag_delete', args=[blag.id])
        changelist_url = reverse('admin:tests_blag_changelist')

        data = self._get_form_data()
        data.update({
            'id': '%s' % blag.id,
        })
        # ...but AAA Cannot actually change anything
        client = self.get_client('has_aaa')
        response = client.post(delete_url, data)
        self.assertEqual(response.status_code, DENIED)

        client = self.get_client('has_all')
        response = client.post(delete_url, data)
        self.assertRedirects(response, changelist_url)
        self.assertEqual(Blag.objects.count(), 0)

    def test_inner_url(self):
        """Should be able to decorate urls in ModelAdmin.get_urls()."""
        blag1 = Blag.objects.create(name='blag one')
        blag2 = Blag.objects.create(name='blag two')
        response = self._get_and_assert_access('admin:list', 'has_all', OK)
        self.assertContains(response, blag1.name)
        self.assertContains(response, blag2.name)
        self._get_and_assert_access('admin:list', 'has_aaa', DENIED)
        self._get_and_assert_access('admin:list', 'has_b', DENIED)


class TestAdminInlineIntegration(_IntegrationBase):
    def _get_form_data(self):
        return {
            'blagentry_set-TOTAL_FORMS': u'3',  # 3 extra forms for inlines
            'blagentry_set-INITIAL_FORMS': u'0',
            'blagentry_set-MAX_NUM_FORMS': u'',
            'photoblagentry_set-TOTAL_FORMS': u'3',
            'photoblagentry_set-INITIAL_FORMS': u'0',
            'photoblagentry_set-MAX_NUM_FORMS': u'',
        }

    def test_add(self):
        blag = Blag.objects.create(name="blagonet")
        PhotoBlagEntry.objects.all().delete()
        self.assertEqual(PhotoBlagEntry.objects.all().count(), 0)
        change_url = reverse('admin:tests_blag_change', args=[blag.id])
        changelist_url = reverse('admin:tests_blag_changelist')

        data = self._get_form_data()
        data.update({
            'name': blag.name,
            'photoblagentry_set-0-blag': '%s' % blag.id,
            'photoblagentry_set-0-title': 'my title',
        })
        # B has no permissions
        client = self.get_client('has_b')
        response = client.post(change_url, data)
        self.assertEqual(response.status_code, 403)

        # A succeedes
        client = self.get_client('has_a')
        response = client.post(change_url, data)
        self.assertRedirects(response, changelist_url)
        self.assertEqual(
            Blag.objects.get(id=blag.id).photoblagentry_set.count(), 1)
        self.assertEqual(PhotoBlagEntry.objects.all().count(), 1)

    def test_change(self):
        blag = Blag.objects.create(name="blagonet")
        entry = PhotoBlagEntry.objects.create(
            blag=blag, title="a title")

        change_url = reverse('admin:tests_blag_change', args=[blag.id])
        changelist_url = reverse('admin:tests_blag_changelist')
        self.assertEqual(
            Blag.objects.get(id=blag.id).photoblagentry_set.count(), 1)

        data = self._get_form_data()
        data.update({
            'name': blag.name,
            'photoblagentry_set-TOTAL_FORMS': u'4',
            'photoblagentry_set-INITIAL_FORMS': u'1',
            'photoblagentry_set-0-id': '%s' % entry.id,
            'photoblagentry_set-0-blag': '%s' % blag.id,
            'photoblagentry_set-0-title': 'my new title',
        })
        # B has no permissions
        client = self.get_client('has_b')
        response = client.post(change_url, data)
        self.assertEqual(response.status_code, 403)

        # A successfully alters the entry
        client = self.get_client('has_a')
        self.assertContains(client.get(change_url), entry.title)
        response = client.post(change_url, data)
        self.assertRedirects(response, changelist_url)
        self.assertEqual(
            Blag.objects.get(id=blag.id).photoblagentry_set.count(), 1)
        self.assertEqual(PhotoBlagEntry.objects.all().count(), 1)
        self.assertEqual(PhotoBlagEntry.objects.get().title, 'my new title')

    def test_delete(self):
        blag = Blag.objects.create(name="blagonet")
        entry = PhotoBlagEntry.objects.create(
            blag=blag, title="a title")

        change_url = reverse('admin:tests_blag_change', args=[blag.id])
        changelist_url = reverse('admin:tests_blag_changelist')

        data = self._get_form_data()
        data.update({
            'name': blag.name,
            'photoblagentry_set-TOTAL_FORMS': u'4',
            'photoblagentry_set-INITIAL_FORMS': u'1',
            'photoblagentry_set-0-id': '%s' % entry.id,
            'photoblagentry_set-0-blag': '%s' % blag.id,
            'photoblagentry_set-0-title': entry.title,
            'photoblagentry_set-0-DELETE': 'on',
        })

        # B has no permissions
        client = self.get_client('has_b')
        response = client.post(change_url, data)
        self.assertEqual(response.status_code, 403)

        # A successfully deletes the entry
        client = self.get_client('has_a')
        response = client.post(change_url, data)
        self.assertRedirects(response, changelist_url)
        self.assertEqual(
            Blag.objects.get(id=blag.id).photoblagentry_set.count(), 0)
        self.assertEqual(PhotoBlagEntry.objects.all().count(), 0)
