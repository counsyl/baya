from mock import MagicMock
from unittest import TestCase

from ..dynamic_roles import DjangoRequestGroupFormatter
from ..membership import DynamicRolesNode as dg
from ..membership import RolesNode as g
from ..membership import ValueNode
from ..visitors import ExpressionWriter
from ..visitors import PermissionChecker


class TestPermissionChecker(TestCase):
    def setUp(self):
        self.a = g('A')
        self.b = g('B')
        self.c = g('C')
        self.s_admin = dg(DjangoRequestGroupFormatter('%s_admin', 'group'))

    def mock_request(self, request_group):
        """Build a mock request (for self.s_admin).

        Args:
            request_group: The group that the user is requesting access to.
        """
        request = MagicMock()
        request.resolver_match.kwargs = {}
        request.GET = {}
        request.GET['group'] = request_group
        return request

    def _has_permissions(self, node, roles, **kwargs):
        return PermissionChecker(roles).visit(node, **kwargs)

    def test_set_membership_single(self):
        self.assertTrue(self._has_permissions(self.a, ['A']))
        self.assertFalse(self._has_permissions(self.a, ['B']))

    def test_and(self):
        and_node = self.a & self.b
        self.assertTrue(self._has_permissions(and_node, ['A', 'B']))
        self.assertFalse(self._has_permissions(and_node, ['A']))
        self.assertFalse(self._has_permissions(and_node, ['B']))

    def test_and_dynamic(self):
        """Ensure the group permissions are using the requested group."""
        and_node = self.a & self.s_admin
        self.assertTrue(self._has_permissions(
            and_node, ['A', 'a_admin'], request=self.mock_request('A')))
        self.assertFalse(self._has_permissions(
            and_node, ['A', 'a_admin'], request=self.mock_request('B')))

    def test_or(self):
        or_node = self.a | self.b
        self.assertTrue(self._has_permissions(or_node, ['A', 'B']))
        self.assertTrue(self._has_permissions(or_node, ['A']))
        self.assertTrue(self._has_permissions(or_node, ['B']))
        self.assertTrue(self._has_permissions(or_node, ['A', 'B', 'C']))

    def test_xor(self):
        xor_node = self.a ^ self.b
        self.assertFalse(self._has_permissions(xor_node, ['A', 'B']))
        self.assertTrue(self._has_permissions(xor_node, ['A']))
        self.assertTrue(self._has_permissions(xor_node, ['B']))

    def test_not(self):
        not_node = ~self.a
        self.assertFalse(self._has_permissions(not_node, ['A', 'B']))
        self.assertFalse(self._has_permissions(not_node, ['A']))
        self.assertTrue(self._has_permissions(not_node, ['B']))
        self.assertFalse(self._has_permissions(not_node, ['A', 'B', 'C']))
        self.assertTrue(self._has_permissions(not_node, ['B', 'C']))

    def test_and_or_and(self):
        node = (self.a & self.b) | (self.c & self.s_admin)
        req = self.mock_request('a')
        self.assertFalse(self._has_permissions(node, ['A'], request=req))
        self.assertFalse(self._has_permissions(node, ['B'], request=req))
        self.assertFalse(self._has_permissions(node, ['C'], request=req))
        self.assertFalse(
            self._has_permissions(node, ['a_admin'], request=req))
        self.assertTrue(self._has_permissions(node, ['A', 'B'], request=req))
        self.assertTrue(
            self._has_permissions(node, ['a_admin', 'C'], request=req))
        self.assertFalse(self._has_permissions(node, ['A', 'C'], request=req))
        self.assertFalse(
            self._has_permissions(node, ['B', 'a_admin'], request=req))

    def test_and_xor_not_and(self):
        """What a ridiculous membership requirement."""
        node = (self.a & self.b) ^ ~(self.c | self.s_admin)
        req = self.mock_request('A')
        self.assertTrue(self._has_permissions(node, ['A'], request=req))
        self.assertTrue(self._has_permissions(node, ['B'], request=req))
        self.assertFalse(self._has_permissions(node, ['C'], request=req))
        self.assertFalse(self._has_permissions(node, ['a_admin'], request=req))
        self.assertFalse(self._has_permissions(node, ['A', 'B'], request=req))
        self.assertFalse(
            self._has_permissions(node, ['a_admin', 'C'], request=req))
        self.assertFalse(self._has_permissions(node, ['A', 'C'], request=req))
        self.assertFalse(
            self._has_permissions(node, ['B', 'a_admin'], request=req))
        self.assertTrue(self._has_permissions(
            node, ['A', 'B', 'a_admin'], request=req))
        self.assertTrue(self._has_permissions(
            node, ['A', 'B', 'C'], request=req))
        self.assertTrue(self._has_permissions(
            node, ['A', 'B', 'C', 'a_admin'], request=req))

    def test_value_node(self):
        node1 = ValueNode(True)
        node2 = ~ValueNode(False)
        self.assertTrue(self._has_permissions(node1, ['A']))
        self.assertTrue(self._has_permissions(node2, ['A']))
        self.assertTrue(self._has_permissions(node1, ['']))
        self.assertTrue(self._has_permissions(node2, ['']))
        self.assertTrue(self._has_permissions(node1, ['A', 'F']))
        self.assertTrue(self._has_permissions(node2, ['A', 'F']))
        node1 = ValueNode(False)
        node2 = ~ValueNode(True)
        self.assertFalse(self._has_permissions(node1, ['A']))
        self.assertFalse(self._has_permissions(node2, ['A']))
        self.assertFalse(self._has_permissions(node1, ['']))
        self.assertFalse(self._has_permissions(node2, ['']))
        self.assertFalse(self._has_permissions(node1, ['A', 'F']))
        self.assertFalse(self._has_permissions(node2, ['A', 'F']))

    def test_member_and_value_node(self):
        node = ValueNode(True) | g('A')
        self.assertTrue(self._has_permissions(node, ['A']))
        self.assertTrue(self._has_permissions(node, ['']))
        self.assertTrue(self._has_permissions(node, ['A', 'F']))
        node = ValueNode(True) & g('A')
        self.assertTrue(self._has_permissions(node, ['A']))
        self.assertFalse(self._has_permissions(node, ['']))
        self.assertTrue(self._has_permissions(node, ['A', 'F']))
        node = ValueNode(False) | g('A')
        self.assertTrue(self._has_permissions(node, ['A']))
        self.assertFalse(self._has_permissions(node, ['']))
        self.assertTrue(self._has_permissions(node, ['A', 'F']))
        node = ValueNode(False) & g('A')
        self.assertFalse(self._has_permissions(node, ['A']))
        self.assertFalse(self._has_permissions(node, ['']))
        self.assertFalse(self._has_permissions(node, ['A', 'F']))


class TestExpressionWriter(TestCase):
    def setUp(self):
        self.writer = ExpressionWriter()

    def test_operator_precedence(self):
        node = g('A') ^ g('B') | g('C') ^ g('D')
        self.assertEquals('{a} ^ {b} | {c} ^ {d}', self.writer.visit(node),
                          repr(node))
        node = ~(g('A') & g('B')) ^ (g('C') | g('D') & g('E'))
        self.assertEquals('~{a, b} ^ ({c} | {d, e})', self.writer.visit(node),
                          repr(node))

    def test_unary(self):
        node = ~~g('A')
        self.assertEquals('~~{a}', self.writer.visit(node), repr(node))
        node = ~(g('A') ^ g('B'))
        self.assertEquals('~({a} ^ {b})', self.writer.visit(node), repr(node))

    def test_value_node(self):
        node = ~ValueNode(True)
        self.assertEquals('~True', self.writer.visit(node))
        node = g('A') & ValueNode(False)
        self.assertEquals('{a} & False', self.writer.visit(node))
        node = ~node
        self.assertEquals('~({a} & False)', self.writer.visit(node))
