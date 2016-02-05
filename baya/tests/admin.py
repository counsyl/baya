from django.conf.urls import patterns
from django.conf.urls import url
from django.contrib import admin
from django.shortcuts import render

from baya.admin import BayaModelAdmin
from baya.admin import BayaInlineMixin
from baya.admin.sites import NestedGroupsAdminSite
from baya import requires
from baya import SetMembershipNode as g
from baya.permissions import DENY_ALL

from .models import Blag
from .models import BlagEntry
from .models import PhotoBlagEntry
from .submod.models import Comment

A = g('a')
AA = g('aa')
AAA = g('aaa')
B = g('b')


class UnprotectedPhotoBlagEntryOptions(admin.ModelAdmin):
    pass


class UnprotectedPhotoBlagEntryInline(admin.TabularInline):
    model = PhotoBlagEntry


class ProtectedPhotoBlagEntryInline(BayaInlineMixin, admin.TabularInline):
    CREATE = A | B
    UPDATE = A
    DELETE = A

    model = PhotoBlagEntry


class BlagEntryInline(admin.TabularInline):
    model = BlagEntry


@requires(get=AAA, post=A)
class BlagOptions(BayaModelAdmin):
    """http://xkcd.com/148/"""
    DELETE = A

    fields = list_display = ['name']

    inlines = [
        BlagEntryInline,  # Perms inherited from BlagEntryOptions
        UnprotectedPhotoBlagEntryInline,  # This doesn't show up b/c no perms
        ProtectedPhotoBlagEntryInline,
    ]

    def get_urls(self):
        urls = super(BlagOptions, self).get_urls()
        my_urls = patterns(
            '',
            # Just having B isn't enough to access this URL, because you still
            # need the GET permission from the class definition.
            url(r'^list/$',
                requires(B)(self.list_of_blags),
                name='list'),
        )
        return my_urls + urls

    def list_of_blags(self, request):
        blags = Blag.objects.all()
        return render(request, 'tests/blag_list.html', {'object_list': blags})


class BlagEntryOptions(BayaModelAdmin):
    CREATE = A


class CommentOptions(BayaModelAdmin):
    CREATE = A
    READ = AA | B
    UPDATE = AA
    DELETE = DENY_ALL


site = NestedGroupsAdminSite(name='example')
site.register(PhotoBlagEntry, UnprotectedPhotoBlagEntryOptions)
site.register(Blag, BlagOptions)
site.register(BlagEntry, requires(AA)(BlagEntryOptions))
site.register(Comment, CommentOptions)
