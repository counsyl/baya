from __future__ import absolute_import
from django.conf.urls import include, url

from .baya.tests import urls as eu

urlpatterns = [
    url(r'^', include(eu)),
]

from .baya.mock_ldap_helpers import mock_ldap_setup
from .baya.tests import directory
mock_ldap_instance = mock_ldap_setup(
    'dc=test',
    extra_users=directory.test_users,
    group_lineage=directory.group_lineage)
mock_ldap_instance.start()
