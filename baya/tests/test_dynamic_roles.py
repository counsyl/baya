from mock import MagicMock
from mock import patch

from unittest import TestCase

from ..dynamic_roles import DjangoRequestGroupFormatter


class TestDjangoRequestGroupFormatter(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestDjangoRequestGroupFormatter, self).__init__(*args, **kwargs)
        self.formatter = DjangoRequestGroupFormatter("%s_admin", "group")

    def build_mock_request(self, request_group):
        """Build a mock request.

        Args:
            request_group: The group that the user is requesting access to.
        """
        request = MagicMock()
        request.resolver_match.kwargs = {}
        request.GET = {}
        request.GET['group'] = request_group
        return request

    def test_returns_set(self):
        """The formatter should return a set of groups."""
        roles = self.formatter(self.build_mock_request('mygroup'))
        self.assertEqual(type(roles), set)
        self.assertEqual(len(roles), 1)
        self.assertEqual(roles.pop(), "mygroup_admin")

    def test_query_param(self):
        request = self.build_mock_request('mygroup')
        roles = self.formatter(request)
        self.assertEqual(roles, {'mygroup_admin'})

    def test_reverse_kwarg(self):
        request = self.build_mock_request('mygroup')
        request.GET = {}
        request.resolver_match.kwargs = {'group': 'mygroup'}
        roles = self.formatter(request)
        self.assertEqual(roles, {'mygroup_admin'})

    def test_query_param_collision(self):
        """The URL kwarg should take precedence over the query parameter."""
        request = self.build_mock_request('mygroup')
        request.resolver_match.kwargs = {'group': 'kwarg_group'}
        with patch('baya.dynamic_roles.logger') as mock_logger:
            roles = self.formatter(request)
            self.assertEqual(mock_logger.warning.call_count, 1)
        self.assertEqual(roles, {'kwarg_group_admin'})

    def test_str(self):
        st = str(self.formatter)
        self.assertIn("%s_admin", st)
        self.assertIn("group", st)

    def test_repr(self):
        re = repr(self.formatter)
        self.assertIn(self.formatter.__class__.__name__, re)
