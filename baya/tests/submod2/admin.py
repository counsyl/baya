from baya.admin import BayaModelAdmin
from baya.admin.sites import NestedGroupsAdminSite
from baya.permissions import DENY_ALL

from ..admin import A
from ..admin import AA
from ..admin import B
from .models import SomethingElse


class SomethingElseOptions(BayaModelAdmin):
    CREATE = A
    READ = AA | B
    UPDATE = AA
    DELETE = DENY_ALL


site = NestedGroupsAdminSite(name='sub-admin')
site.register(SomethingElse, SomethingElseOptions)
