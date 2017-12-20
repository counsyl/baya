from functools import partial
import six

from django.conf import settings
from django.contrib.auth import get_permission_codename
from django_auth_ldap.backend import LDAPBackend


class NestedLDAPGroupsBackend(LDAPBackend):

    use_reconnecting_client = getattr(
        settings, 'BAYA_USE_RECONNECTING_CLIENT', False)

    def _get_ldap(self):
        if self.use_reconnecting_client:
            if self._ldap is None:
                ldap_module = super(NestedLDAPGroupsBackend, self).ldap
                self._ldap = ReconnectingLDAP(ldap_module)
            return self._ldap
        else:
            return super(NestedLDAPGroupsBackend, self).ldap
    ldap = property(_get_ldap)

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


class ReconnectingLDAP(object):
    """
    An object that makes the standard ldap.initialize function use
    ldap.ldapobject.ReconnectLDAPObject instead.

    The django_auth_ldap library does not provide a simple way to
    override how the LDAP connection is created. The actual method
    that initiates the connection is on the _get_connection method
    on the hidden _LDAPUser class.

    Instances of this class take the original ldap module instance
    and provide the same set of attributes, except that the initialize
    attribute returns ReconnectLDAPObject instead of the original
    initialize function (which just instantiates a SimpleLDAPObject).
    """
    retry_max = 6

    def __init__(self, original_module):
        self._original_module = original_module

    def __getattr__(self, name):
        """
        Return the requested value from the original module.

        This is called when ordinary attribute lookups fail.
        Since initialize is defined below, it will not be called
        for accesses to that attribute.
        """
        return getattr(self._original_module, name)

    def initialize(self, uri):
        return self._original_module.ldapobject.ReconnectLDAPObject(
            uri, retry_max=self.retry_max)
