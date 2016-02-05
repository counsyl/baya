"""Arbitrary expressions evaluated as an AST."""
from operator import and_
from operator import not_
from operator import or_
from operator import xor


# Abstract base classes for nodes.

class BaseNode(object):
    """Abstract base class for permission nodes."""

    # Unary operators.
    def __invert__(self):
        return InvertNode(self)

    # Binary operators.
    def __and__(self, other):
        return AndNode(self, other)

    def __rand__(self, other):
        return self & other

    def __or__(self, other):
        return OrNode(self, other)

    def __ror__(self, other):
        return self | other

    def __xor__(self, other):
        return XorNode(self, other)

    def __rxor__(self, other):
        return self ^ other

    # Comparisons.
    def __eq__(self, other):
        return self.__class__ is other.__class__

    def __ne__(self, other):
        return not (self == other)

    def __nonzero__(self):
        raise TypeError(
            "You probably tried to do 'group1 or/and group2' which, due to "
            "python's semantics, only returns one group. Use a bitwise "
            "operator like &, |, or ^ instead.")


class ValueNode(BaseNode):
    """A Node which always returns a given value."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "ValueNode(%s)" % repr(self.value)


class RolesNode(BaseNode):
    def __init__(self, *roles):
        self._roles_set = {role.lower() for role in roles}

    def get_roles_set(self, **kwargs):
        return self._roles_set

    def __and__(self, other):
        if type(other) is type(self):
            # We can reduce the node complexity by simply combining roles sets.
            return self.__class__(*(self._roles_set | other._roles_set))
        return super(RolesNode, self).__and__(other)

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self._roles_set == other._roles_set)

    def __str__(self):
        return '{%s}' % (', '.join(sorted(self._roles_set)))

    def __repr__(self):
        return ('RolesNode(%s)' %
                (', '.join('"%s"' % role for role in sorted(self._roles_set))))


class DynamicRolesNode(RolesNode):
    """DynamicRolesNodes take callables that return a set of groups.

    The primary use case is when you don't know the required LDAP groups
    until runtime. For example, say you have a BlogPost model that is put
    into one of the categories {'Programming', 'Food', 'Travel'}. Each of
    your users is in only one of those categories, so you want to allow
    posting and editing of content only if the user is authorized for that
    category. You can do this with a DynamicRolesNode:

        class Category(models.Model):
            name = models.CharField(...)

        class BlogPost(models.Model):
            title = models.CharField(...)
            body = models.TextField(...)
            category = models.ForeignKey(Category)

        def _category_name(category_id):
            return {Category.objects.get(id=category_id).name}

        def _blog_post_category(request):
            "Return the category the User is trying to post into."
            # Note that this callable must return a set!
            return _category_name(request.POST['category_id'])

        @requires(post=DynamicRolesNode(_blog_post_category))
        def create_post(request):
            # The user's group membership will be checked on POST to verify
            # that they are in the <category> LDAP group.
            ...

        def _edit_post_category(request):
            return _category_name(BlogPost.objects.get(
                id=request.GET['post_id']).category_id)

        @requires(DynamicRolesNode(_edit_post_category))
        def edit_post(request, post_id):
            # The user can only edit posts in their authorized category.
            ...

    The callable should take kwargs. Note that for Django requests, the
    kwarg `request` will be populated with the current request. The callable
    should return a set of group names.

    Note that DynamicRolesNodes are not compatible with Django admin panels
    because the request is not available to the auth backend when checking
    permissions.
    """
    def __init__(self, *roles_callables):
        self._roles_set = set(roles_callables)

    def get_roles_set(self, **kwargs):
        roles = set()
        for _callable in self._roles_set:
            result = _callable(**kwargs)
            if not isinstance(result, set):
                raise RuntimeError("The callable must return a set.")
            roles |= result
        return roles

    def __str__(self):
        return '{%s}' % self._roles_set

    def __repr__(self):
        return 'DynamicRolesNode(%s)' % self._roles_set


# Operator nodes.

class OperatorNode(BaseNode):
    # Children must define a string that represents this operator.
    display_name = None
    # Children must define an integer arity attribute.
    arity = None
    # Children must define an operator callable with the same arity as
    # specified above.
    operator = None

    def __init__(self, *operands):
        if len(operands) != self.arity:
            raise ValueError('Incorrect number of operands for %s: %d.  '
                             'Expected %d.' % (self.__class__.__name__,
                                               len(operands), self.arity))
        for operand in operands:
            if not isinstance(operand, BaseNode):
                raise TypeError('%r is not a child of BaseNode.' %
                                operand)
            # TODO: Check if operand is an instance of basestring and cast to
            # a BaseNode?
        self._operands = operands

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                len(self._operands) == len(other._operands) and
                all(op1 == op2 for op1, op2 in
                    zip(self._operands, other._operands)))

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(map(repr, self._operands)))


class InvertNode(OperatorNode):
    display_name = '~'
    arity = 1
    operator = not_


class AndNode(OperatorNode):
    display_name = '&'
    arity = 2
    operator = and_


class OrNode(OperatorNode):
    display_name = '|'
    arity = 2
    operator = or_


class XorNode(OperatorNode):
    display_name = '^'
    arity = 2
    operator = xor
