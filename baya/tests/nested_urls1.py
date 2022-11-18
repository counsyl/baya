import django
if django.VERSION[:2] < (4, 0):
    from django.conf.urls import url, include
else:
    from django.urls import include, re_path
    url = re_path

from baya.permissions import requires

from .views import my_view
from .views import my_undecorated_view
from . import nested_urls2

app_name = 'nested1'


urlpatterns = [
    url(r'^my_view/$', my_view, name='nested1_my_view'),
    url(r'^my_undecorated_view/$',
        requires('aa')(my_undecorated_view),
        name='nested1_my_undecorated_view'),
    url(r'^nested2/', requires('aa')(include(nested_urls2))),
]
