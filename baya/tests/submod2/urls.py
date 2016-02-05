from django.conf.urls import include, patterns, url

from . import admin


urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls), name='submod2_admin'),
)
