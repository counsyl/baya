from django.contrib.admin import ModelAdmin

from baya.utils import has_permission
from baya.permissions import ALLOW_ALL
from baya.permissions import requires


class BayaInlineMixin(object):
    """Mixin for using with Django admin.InlineModelAdmin.

    Inlines, unlike everything else protected by baya, don't get special
    read-only permissions because Django.

    The implementation of change views for inlines is baked deep into the
    Django ModelAdmin.change_view. In order to give read only access to
    inlines I would have to reimplement the entire ModelAdmin.change_view.

    BayaInline classes take required groups for CREATE, UPDATE, and DELETE
    operations. See BayaModelAdmin for documentation on those class-level
    constants.
    """
    CREATE = ALLOW_ALL
    UPDATE = ALLOW_ALL
    DELETE = ALLOW_ALL

    def has_add_permission(self, request):
        return has_permission(requires(self.CREATE), request.user, 'post')

    def has_change_permission(self, request, obj=None):
        return has_permission(requires(self.UPDATE), request.user, 'post')

    def has_delete_permission(self, request, obj=None):
        return has_permission(requires(self.DELETE), request.user, 'post')


class BayaModelAdmin(ModelAdmin):
    """
    All of the create, read, update, and delete permissions will be
    AND-ed with any gates already on the ModelAdmin class (eg when the
    class is decorated by requires).

    This class has four class attributes that determine the CRUD permissions:
        CREATE: Permissions necessary to gain the app.add_model django
            permission. You must still have POST permissions to create
            the object.
        READ: Permissions necessary to gain the app.change_model
            django permission. Note that this does not actually grant
            you permission to change the object, but only to view the
            changelist. You must still have GET permissions to view the
            changelist and POST permissions to change the objects.
        UPDATE: Permissions necessary to gain the app.change_model
            django permission and save changes to the model. You must
            still have POST permissions to change the objects.
        DELETE: Permissions necessary to gain the app.delete_model django
            permission. You must still have POST permissions to delete
            the object.
    """
    CREATE = ALLOW_ALL
    READ = ALLOW_ALL
    UPDATE = ALLOW_ALL
    DELETE = ALLOW_ALL

    def __init__(self, *args, **kwargs):
        super(BayaModelAdmin, self).__init__(*args, **kwargs)
        if hasattr(self, '_gate'):
            self._gate.get_requires &= self.READ
        else:
            requires(self.READ).decorate_admin(self)

        self.add_view = requires(self.CREATE)(self.add_view)
        self.changelist_view = requires(get=self.READ, post=self.UPDATE)(
            self.changelist_view)
        self.change_view = requires(get=self.READ, post=self.UPDATE)(
            self.change_view)
        self.delete_view = requires(self.DELETE)(self.delete_view)

    def user_has_add_permission(self, user):
        return has_permission(self.add_view, user, 'post')

    def has_add_permission(self, request):
        return self.user_has_add_permission(request.user)

    def user_has_change_permission(self, user):
        return (has_permission(self.changelist_view, user, 'any') or
                has_permission(self.change_view, user, 'any'))

    def has_change_permission(self, request, obj=None):
        return self.user_has_change_permission(request.user)

    def user_has_delete_permission(self, request):
        return has_permission(self.delete_view, request, 'post')

    def has_delete_permission(self, request, obj=None):
        return self.user_has_delete_permission(request.user)
