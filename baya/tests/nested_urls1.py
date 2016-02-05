from django.conf.urls import include, patterns, url

from baya.permissions import requires

from .views import my_view
from .views import my_undecorated_view
from . import nested_urls2


urlpatterns = patterns(
    '',
    url(r'^my_view/$', my_view, name='nested1_my_view'),
    url(r'^my_undecorated_view/$',
        requires('aa')(my_undecorated_view),
        name='nested1_my_undecorated_view'),
    url(r'^nested2/', requires('aa')(include(nested_urls2))),
)
