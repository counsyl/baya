from ldap.dn import str2dn

from .membership import RolesNode as g
from .visitors import PermissionChecker


def group_names(group_dn_list):
    return {str2dn(group)[0][0][1].lower() for group in group_dn_list}


def user_in_group(user, group, **kwargs):
    """Check if a user is in a desired group.

    Args:
        user: A user with its ldap_user property populated (which means the
              user was logged in)
        group: The expected group, as a string or a RolesNode. If you want
               to check membership in several groups, this must be a RolesNode.
        kwargs: passed to the PermissionChecker.visit method.
    """
    user_groups = set()
    if hasattr(user, 'ldap_user'):
        user_groups = group_names(user.ldap_user.group_dns)
    if isinstance(group, basestring):
        group = g(group)
    return PermissionChecker(user_groups).visit(group, **kwargs)


def _get_gate(fn):
    from .permissions import requires
    if isinstance(fn, requires):
        return fn.gate
    else:
        return getattr(fn, '_gate', None)


def has_permission(fn, user, permission):
    """Check if the given user has permission to access the given fn.

    This recurses on all nested Gates, unlike the Gate.user_has_permission
    methods which only operate on a single Gate.

    Args:
        fn: The function which may be protected by baya
        user: The django User which is being checked for access
        permission: The permission to check for. One of 'get', 'post', 'any'
    Returns True if the user has permission, False otherwise.
    """
    gate = _get_gate(fn)
    if gate:
        if permission == 'get':
            check_perm = gate.user_has_get_permission
        elif permission == 'post':
            check_perm = gate.user_has_post_permission
        elif permission == 'any':
            check_perm = gate.user_has_any_permission
        else:
            raise ValueError(
                "%s is not a valid permission to check." % permission)
        if check_perm(user):
            if not hasattr(fn, 'func_closure'):
                # Not wrapping any function, so bail out
                return True

            nested_fn = fn.func_closure[0].cell_contents
            if not _get_gate(nested_fn):
                return True
            else:
                return has_permission(nested_fn, user, permission)
    return False
