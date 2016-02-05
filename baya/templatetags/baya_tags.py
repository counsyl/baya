from baya.utils import has_permission
from django import template
from django.core.urlresolvers import resolve
from django.core.urlresolvers import reverse

register = template.Library()


@register.assignment_tag(takes_context=True)
def can_user_perform_action(context, action, *args, **kwargs):
    """
    Assignment tag to check user permission within a template.

    Example:
        {%  can_user_perform_action "home" as can_view_homepage %}

    Args:
        context: The template context (implicitly passed in because
            takes_context=True)
        action: The name of the url
        args/kwargs: The args/kwargs required by reverse

    Returns:
        bool: True if user has permission, False otherwise.

    Caveats:
        If there is no Gate (no requires function wrapping the viewfunc),
        has_permission returns False.

        action, args, and kwargs are fed directly into reverse. If they aren't
        given correctly, exceptions will be thrown. e.g. You supply both
        args and kwargs. For details please see django docs:
        https://docs.djangoproject.com/en/1.8/ref/urlresolvers/#reverse
    """
    view_func = resolve(reverse(action, args=args, kwargs=kwargs)).func

    return has_permission(view_func, context['user'], 'any')
