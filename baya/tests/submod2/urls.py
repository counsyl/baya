from django.conf.urls import include, url

from . import admin


urlpatterns = [
    url(r'^admin/', include(admin.site.urls), name='submod2_admin'),
]
