import ldap
import os

import django
from django.core.urlresolvers import reverse_lazy
from django_auth_ldap.config import LDAPSearch
from django_auth_ldap.config import NestedGroupOfNamesType


DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DBFILENAME', ':memory:')
    }
}

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django_nose',
    'baya',
    'baya.tests',
    'baya.tests.submod',
    'baya.tests.submod2',
)
if django.VERSION[:2] >= (1, 7):
    # Django switched the order of installed apps in 1.7.
    INSTALLED_APPS = tuple(reversed(INSTALLED_APPS))

ROOT_URLCONF = "baya.tests.urls"

LOGIN_URL = '/login/'

BAYA_LOGIN_URL = reverse_lazy('login')

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages'
)

AUTHENTICATION_BACKENDS = (
    'baya.backend.NestedLDAPGroupsBackend',
    'django.contrib.auth.backends.ModelBackend',
)

SECRET_KEY = 'secretkey'

ALLOWED_HOSTS = []

STATIC_FILE_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

STATIC_URL = '/static/'

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Mock LDAP settings
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0
}
AUTH_LDAP_GROUP_TYPE = NestedGroupOfNamesType()
AUTH_LDAP_FIND_GROUP_PERMS = True
AUTH_LDAP_MIRROR_GROUPS = True

AUTH_LDAP_BIND_DN = 'cn=auth,ou=people,dc=test'
AUTH_LDAP_BIND_PASSWORD = 'password'
AUTH_LDAP_SERVER_URI = 'ldap://localhost'
AUTH_LDAP_START_TLS = False

AUTH_LDAP_USER_SEARCH = LDAPSearch(
    'ou=people,dc=test',
    ldap.SCOPE_SUBTREE,
    '(uid=%(user)s)'
)
# User attributes to populate with values from the LDAP database.
AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'givenName',
    'last_name': 'sn',
    'email': 'mail',
}
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    'is_staff': ['cn=a,ou=access,dc=test',
                 'cn=aa,ou=access,dc=test',
                 'cn=aaa,ou=access,dc=test',
                 'cn=b,ou=access,dc=test'],
}
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    'ou=access,dc=test',
    ldap.SCOPE_SUBTREE,
    "(objectClass=groupOfNames)"
)
