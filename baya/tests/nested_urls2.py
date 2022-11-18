import django

if django.VERSION[:2] < (4, 0):
    from django.conf.urls import url
else:
    from django.urls import re_path
    url = re_path

from baya.permissions import requires

from .views import my_view
from .views import my_undecorated_view


urlpatterns = [
    url(r'^my_view/$', my_view, name='nested_nested_my_view'),
    url(r'^my_undecorated_view/$',
        requires('A')(my_undecorated_view),
        name='nested_nested_my_undecorated_view'),
]
