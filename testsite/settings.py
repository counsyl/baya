# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

STATIC_URL = '/static/'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '7(g6j4ff9!864#py0iump(8nf4w_fs$in@taxp&)^5ycx@xms9'

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = []

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_nose',
    'baya',
    'baya.tests',
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "baya.context_processors.permission_context",
)

ROOT_URLCONF = 'urls'

WSGI_APPLICATION = 'wsgi.application'

LOGIN_URL = "/login/"

AUTHENTICATION_BACKENDS = (
    'baya.backend.NestedLDAPGroupsBackend',
    'django.contrib.auth.backends.ModelBackend',
)

import os
BASE_DIR = os.path.dirname(__file__)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_L10N = False
USE_TZ = True

# LDAP
LIVE_LDAP = False

import ldap
from django_auth_ldap.config import LDAPSearch, NestedGroupOfNamesType

AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0
}
AUTH_LDAP_GROUP_TYPE = NestedGroupOfNamesType()
AUTH_LDAP_FIND_GROUP_PERMS = True
AUTH_LDAP_MIRROR_GROUPS = True

BAYA_ALLOW_ALL = False

LDAP_DC = "dc=test"
AUTH_LDAP_BIND_DN = 'cn=auth,ou=people,%s' % LDAP_DC
AUTH_LDAP_BIND_PASSWORD = 'password'
AUTH_LDAP_SERVER_URI = 'ldap://localhost'
AUTH_LDAP_START_TLS = False

AUTH_LDAP_USER_SEARCH = LDAPSearch(
    'ou=people,%s' % LDAP_DC,
    ldap.SCOPE_SUBTREE,
    '(uid=%(user)s)')
# User attributes to populate with values from the LDAP database.
AUTH_LDAP_USER_ATTR_MAP = {
    'first_name': 'givenName',
    'last_name': 'sn',
    'email': 'mail',
}
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    'is_staff': ['cn=a,ou=access,%s' % LDAP_DC,
                 'cn=aa,ou=access,%s' % LDAP_DC,
                 'cn=aaa,ou=access,%s' % LDAP_DC,
                 'cn=b,ou=access,%s' % LDAP_DC],
}
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    'ou=access,%s' % LDAP_DC,
    ldap.SCOPE_SUBTREE,
    "(objectClass=groupOfNames)"
)
# END LDAP
