from django.conf.urls import url

from baya.permissions import requires

from .views import my_view
from .views import my_undecorated_view


urlpatterns = [
    url(r'^my_view/$', my_view, name='nested_nested_my_view'),
    url(r'^my_undecorated_view/$',
        requires('A')(my_undecorated_view),
        name='nested_nested_my_undecorated_view'),
]
