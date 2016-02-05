from collections import OrderedDict
from operator import or_

from django.conf.urls import url
from django.conf.urls import include
from django.contrib.admin.sites import AdminSite

from baya.permissions import requires
from baya.membership import ValueNode


# Keep a registry of baya-enabled admin sites so we can properly intercept
# permissions checking in NestedLDAPGroupsBackend.
_admin_registry = set()


class NestedGroupsAdminSite(AdminSite):
    def __init__(self, *args, **kwargs):
        super(NestedGroupsAdminSite, self).__init__(*args, **kwargs)
        _admin_registry.add(self)
        all_groups = self._get_required_baya_groups()
        if all_groups is not None:
            self.index = requires(all_groups)(self.index)
            self.app_index = requires(all_groups)(self.app_index)

    def _get_admins_with_gate(self):
        admins = []
        # Only need to sort this list so we get consistent OperatorNode trees.
        items = sorted(self._registry.items(),
                       key=lambda x: x[0]._meta.model_name)
        for model, model_admin in items:
            if hasattr(model_admin, '_gate'):
                admins.append((model, model_admin))
        return admins

    def get_urls(self):
        """Ensure that urls included in get_urls() are behind requires().

        We need to fix the include() logic for admin URLs. Django admin isn't
        very extensible, so we have to call super, remove the url patterns
        for model_admins that have a _gate, and replace the pattern with
        a properly built include behind the model admin's gate.

        Would be a lot easier if django exposed something like
        get_patterns_for_app(app_label), but noooooo.
        """
        # We have to maintain the URL ordering due to the way URLs are resolved
        # TODO - Test this, can lead to heisenbugs
        urls = OrderedDict((urlp.regex.pattern, urlp) for urlp in
                           super(NestedGroupsAdminSite, self).get_urls())
        for model, model_admin in self._get_admins_with_gate():
            if hasattr(model._meta, 'module_name'):
                model_name = model._meta.module_name
            elif hasattr(model._meta, 'model_name'):
                model_name = model._meta.model_name
            else:
                raise ValueError(
                    "Model Admin is missing a module or model name.")
            pattern = (
                r'^%s/%s/' %
                (model._meta.app_label, model_name))
            urls[pattern] = url(
                pattern,
                requires(get=model_admin._gate.get_requires,
                         post=model_admin._gate.post_requires)(
                             include(model_admin.urls)))
        return urls.values()

    def _get_required_baya_groups(self, app_label=None):
        # Loop over all model admins, checking their set of permissions
        all_roles = OrderedDict()
        for model, model_admin in self._get_admins_with_gate():
            if app_label and app_label != model._meta.app_label:
                continue
            roles = model_admin._gate.get_requires
            if roles is not None and not isinstance(roles, ValueNode):
                all_roles[roles] = True
        if all_roles:
            return reduce(or_, all_roles.keys())
        return None

    def admin_view(self, view, cacheable=False):
        fn = super(NestedGroupsAdminSite, self).admin_view(view, cacheable)
        all_groups = self._get_required_baya_groups()
        if all_groups is not None:
            fn = requires(all_groups)(fn)
        return fn
