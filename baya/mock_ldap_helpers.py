"""Helpers for mock_ldap.

You can use these helpers to create a mock LDAP directory for local testing.
See the testsite.directory module for an example.
"""
from collections import defaultdict

DEFAULT_DC = "dc=test"


def person_dn(name, dc=None):
    dc = dc or DEFAULT_DC
    return ("cn=%s,ou=People,%s" % (name, dc)).lower()


def group_dn(name, dc=None):
    dc = dc or DEFAULT_DC
    return ("cn=%s,ou=Access,%s" % (name, dc)).lower()


def person(name, memberOf=None, dc=None, password=None):
    if memberOf is None:
        memberOf = []
    dc = dc or DEFAULT_DC
    domain_parts = dc.split(",")
    email_suffix = ".".join(part.replace("dc=", "") for part in domain_parts)
    password = password or 'password'
    return (person_dn(name, dc=dc), {
        "uid": [name],
        "cn": [name],
        "objectClass": [
            "person", "organizationalPerson", "inetOrgPerson", "posixAccount"],
        "userPassword": [password],
        "uidNumber": ["1000"],
        "gidNumber": ["1000"],
        "givenName": [name.title()],
        "sn": [name],
        "memberOf": memberOf,
        "mail": ["%s@%s" % (name.replace(" ", '-'), email_suffix)],
    })


def group(name, member, memberOf=None, dc=None):
    if memberOf is None:
        memberOf = []
    return (group_dn(name, dc=dc), {
        "cn": [name],
        "objectClass": ["groupOfNames"],
        "member": member,
        "memberOf": memberOf,
    })


def mock_ldap_directory(
        ldap_dc="dc=example,dc=com",
        bind_user="auth",
        bind_password=None,
        extra_users=None,
        group_lineage=None,
        default_password=None):
    """Get a directory for use with MockLdap.

    Args:
        ldap_dc: The base dc to use, eg 'dc=example,dc=com'
        bind_user: The mock user to use for ldap BIND
        bind_password: The password to use for the bind user. Defaults to
            'password'.
        extra_users: A list of (user, group) pairs that will be added to the
            mockldap config.
        group_lineage: A list of (group_parent, group_child) tuples to
            establish a group hierarchy.
        default_password: Set the password for every user to
            `default_password`. Defaults to 'password'.
    Returns a dict.
    """
    extra_users = extra_users or []
    group_lineage = group_lineage or []

    top = (ldap_dc, {"dc": ldap_dc})
    people = ("ou=People,%s" % ldap_dc, {"ou": "People"})
    access = ("ou=Access,%s" % ldap_dc, {"ou": "Access"})
    auth_user = person(bind_user, [], ldap_dc, bind_password)

    all_users = []
    all_groups = []

    users_to_groups = defaultdict(list)
    groups_to_users = defaultdict(list)
    # Create (user -> [group]) and (group -> [user]) mappings
    for user, group_name in extra_users:
        users_to_groups[user].append(group_name)
        groups_to_users[group_name].append(user)

    child_group_lineage_dict = defaultdict(list)
    parent_group_lineage_dict = defaultdict(list)
    # Create parent group <-> child group mappings
    for parent, child in group_lineage:
        child_group_lineage_dict[parent].append(child)
        parent_group_lineage_dict[child].append(parent)

    # Create a person for every user, which includes that user's groups
    for user, groups in users_to_groups.iteritems():
        all_users.append(person(user, groups, ldap_dc, default_password))

    # Now we need to build groups for every group we know about
    # First look at all of the groups which have users
    for group_name, users in groups_to_users.iteritems():
        people_in_group = [person_dn(user, ldap_dc) for user in users]
        parent_groups = [
            group_dn(parent_group, ldap_dc)
            for parent_group in parent_group_lineage_dict[group_name]]

        all_groups.append(
            group(group_name,
                  people_in_group + parent_groups,
                  [group_dn(child_group, ldap_dc)
                   for child_group in child_group_lineage_dict[group_name]],
                  dc=ldap_dc))
    # Second, look at the groups that are only in a group hierarchy
    for child, parents in parent_group_lineage_dict.iteritems():
        if child in groups_to_users:
            # Skip it if we've already covered it above
            continue
        all_groups.append(
            group(child,
                  [group_dn(parent, ldap_dc) for parent in parents],
                  [group_dn(child_group, ldap_dc)
                   for child_group in child_group_lineage_dict[child]],
                  dc=ldap_dc))

    directory = [top, people, access, auth_user]
    directory.extend(all_users)
    directory.extend(all_groups)
    return dict(directory)


def mock_ldap_setup(
        ldap_dc="dc=example,dc=com", bind_user="auth",
        **kwargs):
    """Mock ldap setup.

    Args:
        ldap_dc: The base dc to use, eg 'dc=example,dc=com'
        bind_user: The mock user to use for ldap BIND

    Returns an instance of MockLdap. To apply the settings you must call
    `.start()` on the returned value.
    """
    from django.conf import settings
    import mockldap

    directory = mock_ldap_directory(ldap_dc, bind_user, **kwargs)

    bind_user_dn = person_dn(bind_user, ldap_dc)
    settings.AUTH_LDAP_BIND_DN = bind_user_dn
    settings.AUTH_LDAP_BIND_PASSWORD = \
        directory[bind_user_dn]['userPassword'][0]
    return mockldap.MockLdap(directory)
