import logging

logger = logging.getLogger('baya')


class DynamicRoleCallable(object):
    def __call__(self, **kwargs):
        raise NotImplementedError("You must implement this method.")


class DjangoRequestCallable(DynamicRoleCallable):
    def __call__(self, request, **kwargs):
        raise NotImplementedError("You must implement this method.")


class DjangoRequestGroupFormatter(DjangoRequestCallable):
    """Create a dynamic group, whose name depends on a query parameter.

    For example, say you have a view:

        def admin_view(request, thing):
            ...

    If you want to restrict access to this view based on a request.GET query
    parameter or on a named URL pattern kwarg you can use this class. Say you
    want to restrict access to thing='abcd' to only those users in the
    abcd_admin group. Then you can annotate the view like this:

        from baya.membership import DynamicRolesNode
        from baya.dynamic_roles import DjangoRequestGroupFormatter
        @requires(DynamicRolesNode(DjangoRequestGroupFormatter(
            "%s_admin", 'thing')))
        def my_view(request, thing):
            ...

    Note that if you have a url like

        url(r'my_view/(?P<param>\w+)/',
            requires(DynamicRolesNode(DjangoRequestGroupFormatter(
                     "%s_admin", 'thing')))(path.to.my_view),
        )

    Then the named reverse kwarg named `param` will always take precedence over
    a url query parameter named `param`. For example:

        http://mysite.com/my_view/my_param1?param=my_param2

    This url will pass my_param1 to the formatter and log a warning about
    my_param2 being there.
    """
    def __init__(self, group_name_format, query_field):
        """
        Args:
            group_name_format: The group name which can be formatted with
                the query_field's value. EG "%s_admin"
            query_field: The query parameter which contains the value to
                format `group_name_format` with.
        """
        self.group_name_format = group_name_format
        self.query_field = query_field

    def __call__(self, request):
        url_kwargs = request.resolver_match.kwargs
        if self.query_field in url_kwargs and self.query_field in request.GET:
            logger.warning(
                "The requested parameter (%s) was in both the url kwargs "
                "and the url query parameters." % self.query_field)
        value = url_kwargs.get(self.query_field,
                               request.GET.get(self.query_field))
        group = self.group_name_format % value
        return {group.lower()}

    def __repr__(self):
        return "%s(%s, %s)" % (
            self.__class__.__name__,
            self.group_name_format,
            self.query_field)
