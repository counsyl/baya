from functools import partial
import six

from django.contrib.auth import get_permission_codename
from django_auth_ldap.backend import LDAPBackend


class NestedLDAPGroupsBackend(LDAPBackend):
    def get_all_permissions(self, user, obj=None):
        """Return a set of <app_label>.<permission> for this user.

        Note that these results will only be applicable to the admin panel.

        <permission> is something like add_mymodel or change_mymodel.
        """
        if hasattr(user, '_baya_cached_all_permissions'):
            return user._baya_cached_all_permissions
        permissions = super(NestedLDAPGroupsBackend, self).get_all_permissions(
            user, obj)
        from baya.admin.sites import _admin_registry
        for admin_site in _admin_registry:
            for model, opts in six.iteritems(admin_site._registry):
                app = model._meta.app_label
                perm_name = partial(get_permission_codename, opts=model._meta)
                if (hasattr(opts, 'user_has_add_permission') and
                        opts.user_has_add_permission(user)):
                    permissions.add("%s.%s" % (app, perm_name('add')))
                if (hasattr(opts, 'user_has_change_permission') and
                        opts.user_has_change_permission(user)):
                    permissions.add("%s.%s" % (app, perm_name('change')))
                if (hasattr(opts, 'user_has_delete_permission') and
                        opts.user_has_delete_permission(user)):
                    permissions.add("%s.%s" % (app, perm_name('delete')))
        user._baya_cached_all_permissions = permissions
        return permissions
