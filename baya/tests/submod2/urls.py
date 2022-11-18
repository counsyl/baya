import django
if django.VERSION[:2] < (4, 0):
    from django.conf.urls import url
else:
    from django.urls import re_path
    url = re_path

from . import admin


app_name = 'submod2'

urlpatterns = [
    url(r'^admin/', admin.site.urls, name='submod2_admin'),
]
