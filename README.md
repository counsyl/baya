# Baya

Baya is a library for using nested LDAP Groups for authorization. It lets you
put urls, methods, CBVs, and Admin views behind access control that uses nested
LDAP groupOfNames.

This also includes an example Django site in the `tests` directory.

The Baya Weaver is a species of bird that weaves complex nests.

<img src="media/Baya_Weaver.jpg" width=350 title="Baya Weaver" />

Image courtesy [J.M.Garg](http://commons.wikimedia.org/wiki/User:J.M.Garg)
on [Wikipedia](http://commons.wikimedia.org/wiki/File:Baya_Weaver_%28Ploceus_philippinus%29-_Male_W_IMG_0732.jpg).
This file is licensed under the [Creative Commons Attribution 3.0 Unported](http://creativecommons.org/licenses/by/3.0/deed.en)
license.

# Installation

```sh
pip install baya
```

If you wish to use mockldap during your development process with Baya, you can install it as part of the optional development dependencies by using:

```sh
pip install baya[development]
```

```python
INSTALLED_APPS = (
    ...
    'baya',
    ...
)

# SessionMiddleware must be active

AUTHENTICATION_BACKENDS = (
    'baya.backend.NestedLDAPGroupsBackend',
    # If you're already using django_auth_ldap.backend.LDAPBackend, delete it
    'django.contrib.auth.backends.ModelBackend',
)
```


# LDAP Prerequisites

Note that you must be using `GroupOfNames` or `GroupOfUniqueNames` and not
`PosixGroup`. You should also emable the `memberOf` overlay (but with some
effort we can eliminate that requirement).

# Configuration

You need to set up your ldap settings. If you already have a working version
of `django_auth_ldap` then you're nearly finished. Make sure the following
settings are configured:

```python
import ldap
from django_auth_ldap.config import LDAPSearch
from django_auth_ldap.config import NestedGroupOfNamesType

AUTH_LDAP_GROUP_TYPE = NestedGroupOfNamesType()
AUTH_LDAP_FIND_GROUP_PERMS = True
AUTH_LDAP_MIRROR_GROUPS = True

AUTH_LDAP_BIND_DN = 'cn=auth,dc=example,dc=com'
AUTH_LDAP_BIND_PASSWORD = 'password'
AUTH_LDAP_SERVER_URI = 'ldaps://ldap'

AUTH_LDAP_USER_SEARCH = LDAPSearch(
    'ou=People,dc=example,dc=com',
    ldap.SCOPE_SUBTREE,
    '(uid=%(user)s)')

AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    'ou=Access,dc=example,dc=com',
    ldap.SCOPE_SUBTREE,
    "(objectClass=groupOfNames)"
)

# Change this to True when testing locally to disable permissions checking
BAYA_ALLOW_ALL = False

# If you have a custom, internal-only login url, you can set this:
# (If you don't set this, baya defaults to LOGIN_URL)
BAYA_LOGIN_URL = "/internal/login/url"
```

Of course, change the values to match your actual setup.

## Admin configuration

The django admin requires that users logging in have the `is_staff` flag set.
You should add this config to your settings if you use the django admin.
See also [admin](#admin).

```python
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    'is_staff': ['cn=myapp_admin,ou=Access,dc=example,dc=com'],
}
```

## Testing access permissions

You will not always have a connection to your production LDAP server, so Baya
supports a couple ways to develop locally and test your views.

### Disable all permissions checking

Be sure to never deploy this setting to production!

The easiest way to test your app locally is to just disable Baya entirely.
You can do this by enabling this setting:

```python
# settings.py
BAYA_ALLOW_ALL = True
```

This will allow all requests to your protected views and is useful if you're
just testing that your view works, but don't currently care about the
access restrictions.

One drawback to this is that you cannot test admin views, due to the way
django admin interacts with django-auth-ldap. It just has to have an LDAP
directory to read from. If your views are protected admin views, then go to
the next section "Use python-mock-ldap".

### Use python-mock-ldap

If you want to test a few views you can use
[mockldap](http://pythonhosted.org//mockldap/). Place the following lines in
your urls.py file so it runs on django startup.

```python
# urls.py

patterns = (...)

from baya.mock_ldap_helpers import mock_ldap_setup

mock_ldap_instance = mock_ldap_setup(
    extra_users=[
        ('my_user', 'group_1'),
        ('my_user', 'group_b'),
        ('other_user', 'group_a'),
    ],
    group_lineage=[
        ('group_a', 'group_b'),  # group_b is a child of group_a
    ]
)
mock_ldap_instance.start()

# And you must update the ldap bind password to use the fake one
from django.conf import settings
settings.AUTH_LDAP_BIND_PASSWORD = 'password'
```

Keep in mind that if you are manually setting groups in your test fixtures
django-auth-ldap will overwrite all of that user's groups with the groups in
LDAP. If your tests suddenly break due to group permissions problems, that's
a likely cause. For this reason I recommend you create new test users for
each app.

For a more complete example, see [baya.tests.directory](baya/tests/directory.py).

# Usage

## Syntax

### baya.permissions.requires([groups, get, post])

* `groups`: A `baya.membership.BaseNode` child which all `GET` and `POST`
  requests must pass.
* `get`: A `baya.membership.BaseNode` child which all `GET` requests must pass.
  AND-ed with the `groups` parameter.
* `post`: A `baya.membership.BaseNode` child which all `POST` requests must
  pass. AND-ed with the `groups` parameter.

Note that if you specify `groups` and `get` or `post`, then the roles are `&`-ed
together. This lets you specify roles common to both `GET` and `POST` requests,
as well as further restrict each method accordingly.

`requires` returns a function which takes your view or urlpattern as its only
argument.

```python
from baya.permissions import requires
from baya.membership import RolesNode as g

admin = g('admin')
billing_ro = g('billing_ro')
customer_service = g('customer_service')

# Only an admin may access this view
requires(admin)(view_or_url)

# Anyone with 'billing_ro' permissions may access this view, but only an admin
# may post. These two declarations result in the same behavior:
requires(billing_ro, post=admin)(view_or_url)
requires(get=billing_ro, post=(billing_ro & admin))

# Customer service or anyone with billing_ro role may access the view, but only
# an admin or customer service may post
requires(get=(customer_service | billing_ro), post=(admin | customer_service))(view_or_url)
```

### DENY_ALL

For convenience, there's a `DENY_ALL` permissions node which you can use to
completely disable access to a view using a given class of HTTP verbs.

```python
from baya.permissions import requires
from baya.permissions import DENY_ALL
from baya.membership import RolesNode as g

@requires(get=g('billing'), post=DENY_ALL)
def my_view(request):
    ...
```

## urls.py

You can protect URLs individually or an entire import:

Decorating the URLs is the preferred usage, since decorating the view methods
themselves makes you hunt around for the permissions.

```python
from django.conf.urls import patterns, url
from django.views.generic import ListView

from baya import requires
from baya import RolesNode as g

from .models import Blag


urlpatterns = patterns(
    '',
    # Protect a single view
    url(r'^$', requires(g('group1'), post=g('group2'))(ListView.as_view(model=Blag))),
    # Protect an entire URL module include
    url(r'^billing/', requires(get=g('billing_ro'), post=g('billing'))(include('my_app.billing.urls'))),
)
```

**Note** Typing the same `g('my_group')` over and over is tedious, verbose,
and prone to typos. A better pattern is to define the groups you'll be using
as constants at the module level:

```python
from django.conf.urls import patterns, url
from django.views.generic import ListView

from baya import requires
from baya import RolesNode as g

from .models import Blag
from .models import Entry

GROUP1 = g('group1')
GROUP2 = g('group2')
BILLING = g('billing')
BILLING_RO = g('billing_ro')

SUPER_GROUP = GROUP1 & GROUP2

urlpatterns = patterns(
    '',
    # Protect a single view
    url(r'^$', requires(GROUP1, post=GROUP2)(ListView.as_view(model=Blag))),
    url(r'^super/$', requires(SUPER_GROUP)(ListView.as_view(model=Entry))),
    # Protect an entire URL module include
    url(r'^billing/', requires(get=BILLING_RO, post=BILLING)(include('my_app.billing.urls'))),
)
```


## views.py

Decorate regular method-based views. Avoid this if possible, preferring url
decoration.

```python
from django.http import HttpResponse

from baya import requires
from baya import RolesNode as g


@requires(g('A'))
def my_simple_view(request):
    return HttpResponse("my_simple_view response")

@requires(g('Aaa'), get=g('A_RO') | g('B_RO'), post=g('A') | g('B'))
def my_view(request):
    return HttpResponse("my_view response")
```

## admin

The admin site takes a little more work. Rather than use
`django.contrib.admin.site` you will instead have to instantiate
`baya.admin.sites.NestedGroupsAdminSite`. You will also have to use the
`baya.admin.BayaModelAdmin` in your `ModelAdmin` classes.

You have a couple more options with django admin option classes than you
normally do with regular views. You can specify different permissions for
the django admin's create, read, update, and delete views.

Note that you can also decorate the `ModelAdmins` individually or wrap them
in `requires` at `site.register` time if you want a given permission to apply
to every request, and not just a particular CRUD verb.

```python
from django.contrib import admin
from django.conf.urls import patterns
from django.conf.urls import url
from django.shortcuts import render

from baya import requires
from baya import RolesNode as g
from baya.admin import BayaModelAdmin
from baya.admin.sites import NestedGroupsAdminSite
from baya.permissions import DENY_ALL

from testsite.example.models import Blag
from testsite.example.models import Entry


@requires(get=g('Aaa'), post=g('A'))
class BlagOptions(BayaModelAdmin):
    fields = list_display = ['name']

    def get_urls(self):
        urls = super(BlagOptions, self).get_urls()

        # This inner url ends up protected like this:
        # requires(get="Aaa", post="a")(requires("B")(self.inner))
        urls += patterns(
            '',
            url(r'inner_admin_view',
                requires(g('B'))(self.inner),
                name='inner')
        )
        return urls

    def inner(self, request):
        return render(...)


class EntryOptions(BayaModelAdmin):
    DELETE = DENY_ALL


class CommentOptions(BayaModelAdmin):
    CREATE = g('A')
    READ = g('Aaa')
    UPDATE = g('Aa')
    DELETE = DENY_ALL


site = NestedGroupsAdminSite(name='example')
site.register(Blag, BlagOptions)
site.register(Entry, requires(g('Aa'))(EntryOptions))
site.register(Comment, CommentOptions)
```

Note that all of the urls returned by your model admin's `get_urls` method
will be protected with the appropriate permissions. You can further restrict
admin inner urls by using the `requires` decorator there.

You must also add configuration for the `is_staff` flag. See
[admin configuration](#admin-configuration).

# Development Set Up

## Django

First check this out and install the requirements:

```sh
make setup
cd testsite
./manage.py syncdb
```

If installation of python-ldap fails on Mac OSX with `fatal error: 'sasl.h' file not found` or similar missing header files then run the following to manualy install `python-ldap`.

```sh
source .venv/bin/activate
pip install python-ldap \
   --global-option=build_ext \
   --global-option="-I$(xcrun --show-sdk-path)/usr/include/sasl"
```

Now `make setup` should work.

# Run

```sh
# in testsite/
./manage.py runserver
```

Runserver and log in to http://localhost:8000/example/ using one of the mock
users in the directory module. Play around with the `@requires` decorator in
`tests.testsite.example.admin` to see the ldap authorization working.

# Testing
```sh
make test
```
