import functools
from types import TypeType

from django.conf import settings
from django.contrib.admin.options import BaseModelAdmin
from django.contrib.admin.options import InlineModelAdmin
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import RegexURLPattern
from django.core.urlresolvers import RegexURLResolver

from .membership import BaseNode
from .membership import ValueNode
from .membership import RolesNode
from .utils import group_names
from .utils import user_in_group
from .visitors import ExpressionWriter


DENY_ALL = ValueNode(False)
ALLOW_ALL = ValueNode(True)


class Gate(object):
    """Track the groups that a view requires.

    The `requires` decorator attaches an instance of this class to every
    view it decorates.
    """
    GET_METHODS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
    POST_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE', 'CONNECT'}
    DEFAULT_PERMISSION_NODE = RolesNode

    def __init__(self, all_requires=None,
                 get_requires=None, post_requires=None,
                 login_url=None):
        """Create a Gate object, which protects access to views.

        Args:
            all_requires: Groups which are required for access via any HTTP
                verb.
            get_requires: Groups which are required for GET-like access. See
                Gate.GET_METHODS
            post_requires: Groups which are required for POST-like access. See
                Gate.POST_METHODS
            login_url: The URL to redirect to when the user is unauthenticated.
                Defaults to django's LOGIN_URL setting. You can set a
                baya-specific default by setting BAYA_LOGIN_URL in your
                django settings.
        """
        baya_login_url = getattr(settings, 'BAYA_LOGIN_URL', None)
        if login_url is not None:
            self.login_url = login_url
        elif baya_login_url is not None:
            self.login_url = baya_login_url
        else:
            self.login_url = settings.LOGIN_URL

        if all_requires is None:
            self.get_requires = self._ensure_permission_node(get_requires)
            self.post_requires = self._ensure_permission_node(post_requires)
        else:
            all_requires = self._ensure_permission_node(all_requires)
            self.get_requires = all_requires
            self.post_requires = all_requires
            if get_requires is not None:
                self.get_requires &= self._ensure_permission_node(get_requires)
            if post_requires is not None:
                self.post_requires &= self._ensure_permission_node(
                    post_requires)

    def _ensure_permission_node(self, groups):
        """
        Convert a 'groups' parameter (from __init__) into a PermissionNode.
        """
        if isinstance(groups, BaseNode):
            return groups

        if groups is None:
            groups = []
        elif isinstance(groups, basestring):
            groups = [group.strip() for group in groups.split(',')]

        return self.DEFAULT_PERMISSION_NODE(*groups)

    def _has_permission(self, user, membership_node, request=None):
        return user_in_group(user, membership_node, request=request)

    def has_get_permission(self, request):
        return self._has_permission(request.user, self.get_requires, request)

    def user_has_get_permission(self, user):
        return self._has_permission(user, self.get_requires)

    def has_post_permission(self, request):
        return self._has_permission(request.user, self.post_requires, request)

    def user_has_post_permission(self, user):
        return self._has_permission(user, self.post_requires)

    def has_any_permission(self, request):
        return (self.has_get_permission(request) or
                self.has_post_permission(request))

    def user_has_any_permission(self, user):
        return (self.user_has_get_permission(user) or
                self.user_has_post_permission(user))

    def get_membership_node(self, request):
        if request.method in self.GET_METHODS:
            return self.get_requires
        elif request.method in self.POST_METHODS:
            return self.post_requires

    def get_permissions_required_data(self, request):
        user_groups = []
        user_groups_str = "{}"
        if hasattr(request, 'user') and hasattr(request.user, 'ldap_user'):
            user_groups = sorted(
                group_names(request.user.ldap_user.group_dns))
            user_groups_str = "{%s}" % ", ".join(
                str(el) for el in user_groups)
        data = {
            'requires_groups': self.get_membership_node(request),
            'requires_groups_str': ExpressionWriter().visit(
                self.get_membership_node(request)),
            'user_groups': user_groups,
            'user_groups_str': user_groups_str,
        }
        return data

    def allow_or_deny(self, request):
        """
        Allow the request to continue (return None), redirect to login,
        or raise PermissionDenied.

        These weird semantics are so you can do:
        return allow_or_deny(request) or HttpResponse(...)
        """
        from django.contrib.auth.views import redirect_to_login
        # Annotate request with some baya information
        request.baya_requires = self.get_permissions_required_data(request)
        # Set BAYA_ALLOW_ALL while testing in development to disable
        # permissions checking.
        if getattr(settings, 'BAYA_ALLOW_ALL', False):
            return None

        # Check permissions before checking if the user is authenticated,
        # to allow views to be protected by empty RolesNodes to be served.
        if (request.method in self.POST_METHODS and
                self.has_post_permission(request)):
            return None
        elif (request.method in self.GET_METHODS and
                self.has_get_permission(request)):
            return None
        if not request.user.is_authenticated():
            path = request.get_full_path()
            return redirect_to_login(path, self.login_url)

        permission_denied_msg = (
            "User {user} does not have permission to {method} to this "
            "resource. Groups {groups} are required, but {user} only has "
            "{user_groups}").format(
                user=request.user,
                method=request.method,
                groups=request.baya_requires['requires_groups'],
                user_groups=request.baya_requires['user_groups'])
        raise PermissionDenied(permission_denied_msg)

    def __iadd__(self, other):
        self.get_requires &= other.get_requires
        self.post_requires &= other.post_requires
        # Prefer other's login_url, if set
        if (other.login_url is not None and
                unicode(other.login_url) != unicode(settings.BAYA_LOGIN_URL)):
            self.login_url = other.login_url
        return self

    def __add__(self, other):
        new = self.__class__()
        new.get_requires = self.get_requires
        new.post_requires = self.post_requires
        new.login_url = self.login_url
        new += other
        return new

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.get_requires == other.get_requires and
                self.post_requires == other.post_requires and
                self.login_url == other.login_url)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "Gate(get_requires=%s, post_requires=%s)" % (
            repr(self.get_requires), repr(self.post_requires))


class requires(object):
    """Decorate methods or urls that need to be access controlled.

    The requires decorator takes a BaseNode as parameters. You can
    read more about those in the baya.membership module. You really just
    need to know about RolesNode, which is usally imported as 'g':

        from baya import RolesNode as g

    Examples:

    Both GET and POST need 'group1' and 'group2' permissions:

        @requires(g('group1') & g('group2'))
        def my_view(request):
            ...

    Both GET and POST require one permission, and POST requires an extra.
    The first parameter is &-ed with the following get and post parameters:

        @requires(g('both_methods'), post=g('and_another_method'))
        def my_view(request):
            ...

    Specify get and post required permissions individually:

        @requires(get=g('group1') | g('group2'), post=g('group2'))
        def my_view(request):
            ...

    Protect a url:

        url(r'^protected_url/$', requires(g('admin'))(my_view))

    Protect an entire url include. Note that when you nest requires() calls
    you are &-ing them together.

        url(r'^admin_views/', requires(g('admin'))(include(my_admin.urls)))

    All of the binary logic operations are available: & | ^ ~.
    """
    GATE_MODEL = Gate

    def __init__(self, groups=None, get=None, post=None, **kwargs):
        self.gate = self.GATE_MODEL(
            all_requires=groups,
            get_requires=get,
            post_requires=post,
            login_url=kwargs.get('login_url'))

    def decorate_method(self, fn, *args, **kwargs):
        """Decorate a view method.

        This is pretty simple - just attach a Gate as a `_gate` property
        to the function and then wrap it in the method dispatcher.
        """
        @functools.wraps(fn)
        def dispatcher(*args, **kwargs):
            largs = list(args)
            if isinstance(largs[0], BaseModelAdmin):
                func = functools.partial(fn, largs.pop(0))
            else:
                func = fn
            request = largs.pop(0)
            return (self.gate.allow_or_deny(request) or
                    func(request, *largs, **kwargs))
        dispatcher._gate = self.gate
        return dispatcher

    def decorate_url_pattern(self, pattern, *args, **kwargs):
        """Decorate a RegexURLPattern or RegexURLResolver.

        Args:
            resolve_fn: Either RegexURLPattern or RegexURLResolver, from
                django.core.urlresolvers

        This decorates the callback for a url after it gets resolved with
        self.decorate_method.
        """
        resolve_fn = pattern.resolve

        @functools.wraps(resolve_fn)
        def patch_resolve(path):
            result = resolve_fn(path)
            if result:
                result.func = self.decorate_method(
                    result.func, *args, **kwargs)
            return result
        pattern.resolve = patch_resolve
        return pattern

    def decorate_admin(self, cls, *args, **kwargs):
        """Alter an admin view for access control.

        This doesn't actually decorate the given class, but instead decorates
        change_view and changelist_view. This is necessary because we often
        want to allow GET access to the chagelist/change_view but not POST,
        since those views are often used as information sources.

        Admin views also need to be in a admin.sites.NestedGroupsAdminSite
        again because we need to properly decorate the admin urls, which are
        provided via NestedGroupsAdminSite.get_urls().
        """
        if not hasattr(cls, '_gate'):
            setattr(cls, '_gate', self.gate)
        else:
            cls._gate += self.gate
            self.gate = cls._gate

        cls.add_view = self.decorate_method(
            cls.add_view, *args, **kwargs)
        cls.changelist_view = self.decorate_method(
            cls.changelist_view, *args, **kwargs)
        cls.change_view = self.decorate_method(
            cls.change_view, *args, **kwargs)
        cls.delete_view = self.decorate_method(
            cls.delete_view, *args, **kwargs)
        return cls

    def decorate_include(self, inc_tup, *args, **kwargs):
        """Decorate a url include with a requires().

        Args:
            inc_tuple: The tuple returned from executing include(my_app.urls).

        Returns the modified include tuple. Note that the url-patterns are
        modified in-place.
        """
        if isinstance(inc_tup[0], (list, tuple)):
            # Must be an include from the admin, where instaed of setting
            # a single module, it returns a list(?!) of patterns...
            patterns = inc_tup[0]
        elif hasattr(inc_tup[0], 'urlpatterns'):
            patterns = inc_tup[0].urlpatterns
        else:
            raise TypeError("Unknown include type: %s" % repr(inc_tup))

        for pattern in patterns:
            self.decorate_url_pattern(pattern, *args, **kwargs)
        return inc_tup

    def __call__(self, fn, *args, **kwargs):
        """Delegate the decoration to the appropriate method."""
        if isinstance(fn, functools.partial) and not hasattr(fn, '__module__'):
            raise ValueError(
                'Cannot decorate a bare functools.partial view.  '
                'You must invoke functools.update_wrapper(partial_view, '
                'full_view) first.')
        if not isinstance(fn, TypeType) and callable(fn):
            return self.decorate_method(fn, *args, **kwargs)
        elif isinstance(fn, tuple):
            # Must be an include('my_app.urls') we're decorating
            return self.decorate_include(fn, *args, **kwargs)
        elif isinstance(fn, (RegexURLPattern, RegexURLResolver)):
            return self.decorate_url_pattern(fn, *args, **kwargs)
        elif isinstance(fn, TypeType) and issubclass(fn, BaseModelAdmin):
            if issubclass(fn, InlineModelAdmin):
                raise TypeError("Cannot decorate Inlines. See "
                                "baya.admin.options.BayaInline instead.")
            return self.decorate_admin(fn, *args, **kwargs)
        elif isinstance(fn, basestring):
            raise TypeError("Cannot decorate string-path to view: %s." % fn)
        else:
            # You'll probably only get here if you're trying to decorate
            # a class-based view
            raise TypeError(
                "Invalid type for requires decorator (%s). "
                "You cannot decorate class-based views. Decorate "
                "the URL or the as_view method instead." % type(fn))
