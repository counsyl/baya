"""
Visitor pattern for walking through a BaseNode AST.
"""

from collections import namedtuple

from .membership import AndNode
from .membership import OperatorNode
from .membership import OrNode
from .membership import RolesNode
from .membership import ValueNode
from .membership import XorNode


VisitedNode = namedtuple('VisitedNode', ['node', 'value'])


class NodeVisitor(object):

    def visit(self, node, **kwargs):
        """
        Visitor method dispatcher based on node type or operator node arity.

        Input: BaseNode
        """
        if isinstance(node, RolesNode):
            return self._visit_roles_node(node, **kwargs)

        if isinstance(node, ValueNode):
            return self._visit_value_node(node, **kwargs)

        if isinstance(node, OperatorNode):
            return self._visit_operator_node(node, **kwargs)

        raise TypeError('Cannot visit node %r' % node)

    def _visit_value_node(self, value_node, **kwargs):
        """Return the value from a ValueNode."""
        return value_node.value

    def _visit_roles_node(self, roles_node, **kwargs):
        """
        Abstract visit method for the leaf node type RolesNode.

        Input: RolesNode
        """

        raise NotImplementedError(
            'Child classes of NodeVisitor must implement _visit_roles_node.')

    def _visit_operator_node(self, operator_node, **kwargs):
        """
        Dispatcher method for OperatorNode types.

        Currently dispatches based on the arity of the operator.

        Input: OperatorNode
        """

        visited_operands = [VisitedNode(operand, self.visit(operand, **kwargs))
                            for operand in operator_node._operands]
        dispatch_methods = [
            self._visit_nullary_node,
            self._visit_unary_node,
            self._visit_binary_node,
        ]
        return dispatch_methods[operator_node.arity](operator_node,
                                                     *visited_operands)

    def _visit_nullary_node(self, operator_node):
        raise ValueError('There are no nullary operators yet.')

    def _visit_unary_node(self, operator_node, visited_operand):
        raise NotImplementedError(
            'Child classes of NodeVisitor must implement _visit_unary_node.')

    def _visit_binary_node(self, operator_node, left_visited_operand,
                           right_visited_operand):
        raise NotImplementedError(
            'Child classes of NodeVisitor must implement _visit_binary_node.')


class ExpressionWriter(NodeVisitor):
    """
    NodeVisitor concrete class that writes out a pretty-printed expression.

    For example, instead of naively interpreting the following node structure
    > OrNode(XorNode('A', 'B'), XorNode('C', 'D'))
    as '((A ^ B) | (C ^ D))' it will return 'A ^ B | C ^ D'.
    But for the following node structure
    > AndNode(OrNode('A', 'B'), OrNode('C', 'D'))
    it will still print it as '(A | B) & (C | D)'.

    All concrete visit methods will return strings.
    """

    # Items that appear first have higher precedence.
    binary_operator_precedence = [
        AndNode,
        XorNode,
        OrNode,
    ]

    def _visit_value_node(self, value_node, **kwargs):
        return str(super(ExpressionWriter, self)._visit_value_node(
            value_node, **kwargs))

    def _visit_roles_node(self, roles_node, **kwargs):
        return str(roles_node)

    def _visit_unary_node(self, operator_node, visited_operand):
        args = (operator_node.display_name, visited_operand.value)
        if self._get_arity(visited_operand.node) > 1:
            return '%s(%s)' % args
        return '%s%s' % args

    def _visit_binary_node(self, operator_node, left_visited_operand,
                           right_visited_operand):
        def get_operand_value(visited_operand):
            value = visited_operand.value
            if (self._get_arity(visited_operand.node) == 2 and
                    self._has_precedence_over(operator_node,
                                              visited_operand.node)):
                value = '(%s)' % value
            return value

        return '%s %s %s' % (get_operand_value(left_visited_operand),
                             operator_node.display_name,
                             get_operand_value(right_visited_operand))

    @staticmethod
    def _get_arity(node):
        return getattr(node, 'arity', None)

    @classmethod
    def _has_precedence_over(cls, left_node, right_node):
        """
        Helper method that determines which operator node has precedence.

        Returns True if left_node has strict precedence over right_node.
        """

        return (cls.binary_operator_precedence.index(left_node.__class__) <
                cls.binary_operator_precedence.index(right_node.__class__))


class PermissionChecker(NodeVisitor):
    """
    NodeVisitor concrete class that checks whether the node has permissions.

    PermissionChecker is instantiated with a roles set, which is an iterable of
    strings which represent role names.  This visitor then evaluates the
    expression encoded in the node AST.  Each node is an operator or a leaf
    node.  Currently leaf nodes are RolesNodes, which evaluate to True if and
    only if their roles set is a subset of the PermissionChecker's roles set.
    Then the operator nodes perform operations on the child booleans and
    propagate the final value up to the root.

    All concrete visit methods will return a boolean.
    """

    def __init__(self, roles):
        """Instantiate a PermissionChecker.

        Args:
            roles: An iterable of strings, representing roles a user has.

        Usage:

            from baya.utils import group_names
            from baya.membership import RolesNode as g

            user_groups = group_names(request.user.ldap_user.group_dns)
            # user_groups looks like {'group1', 'group2', ...}
            checker = PermissionChecker(user_groups)
            required_groups = g('req1') & g('req2')
            user_has_permissions = checker.visit(required_groups)
        """
        self._roles_set = {role.lower() for role in roles}

    def _visit_roles_node(self, roles_node, **kwargs):
        return roles_node.get_roles_set(**kwargs) <= self._roles_set

    def _visit_unary_node(self, operator_node, visited_operand):
        return operator_node.operator(visited_operand.value)

    def _visit_binary_node(self, operator_node, left_visited_operand,
                           right_visited_operand):
        return operator_node.operator(left_visited_operand.value,
                                      right_visited_operand.value)
