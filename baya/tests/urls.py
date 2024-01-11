import django
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.views.generic import ListView
from django.contrib import admin
admin.autodiscover()

from baya import requires
from baya import RolesNode as g
from baya.membership import DynamicRolesNode as dg
from baya.dynamic_roles import DjangoRequestGroupFormatter as drgf
from baya.tests import views

from .models import Blag
from .views import my_view
from .views import my_undecorated_view
from .views import query_param_view
from .admin import site
from . import nested_urls1
from .submod2 import urls as sub2_urls

if django.VERSION[:2] < (4, 0):
    from django.conf.urls import url, include
else:
    from django.urls import include, re_path
    url = re_path

A = g('a')
AA = g('aa')
AAA = g('aaa')


urlpatterns = [
    url(r'^$', requires(AA)(ListView.as_view(model=Blag)), name='index'),
    url(r'^login/$', LoginView.as_view(template_name='registration/login.html'), name='login'),
    url(
        r'^lazy_login/$',
        LoginView.as_view(template_name='registration/login.html'),
        name='lazy_login'
    ),
    url(r'^my_view_str/$', views.my_view, name='my_view_str'),
    url(r'^my_view/$', my_view, name='my_view'),
    url(r'^lazy_login_my_view',
        requires(AA, login_url=reverse_lazy('lazy_login'))(my_view),
        name='lazy_login_my_view'),
    # Cannot decorate string paths to views
    # url(r'^my_undecorated_view_str/$',
    #     requires('A')('baya.tests.views.my_undecorated_view')),
    url(r'^my_undecorated_view/$',
        requires(A)(my_undecorated_view),
        name='my_undecorated_view'),
    url(r'^nested/',
        requires(AAA)(include(nested_urls1))),
    url(r'^nested-namespaced/',
        requires(AAA)(include(nested_urls1, namespace='nested-ns'))),
    url(r'^query_param/(?P<name>\w+)/',
        requires(dg(drgf('%s', 'name')))(query_param_view),
        name='query_param_view'),
    url(r'^admin/', site.urls, name='admin'),
    url(r'^submod2/', include(sub2_urls, namespace='ns-submod2')),
]
