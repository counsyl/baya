from unittest import TestCase

from ..mock_ldap_helpers import DEFAULT_DC
from ..mock_ldap_helpers import group
from ..mock_ldap_helpers import group_dn
from ..mock_ldap_helpers import mock_ldap_directory
from ..mock_ldap_helpers import person
from ..mock_ldap_helpers import person_dn


class TestPerson(TestCase):
    def test_attrs(self):
        name = "bigfoot"
        person_attrs = person(name)
        self.assertEqual(person_attrs[0],
                         "cn=%s,ou=people,%s" % (name, DEFAULT_DC))
        self.assertEqual(person_attrs[1]['uid'], [name])
        self.assertEqual(person_attrs[1]['cn'], [name])
        self.assertEqual(person_attrs[1]['sn'], [name])
        self.assertEqual(person_attrs[1]['mail'], ["%s@test" % name])

    def test_password(self):
        name = "yeti"
        person_attrs = person(name)
        self.assertEqual(person_attrs[1]['userPassword'], ['password'])
        person_attrs = person(name, password='snowstorm')
        self.assertEqual(person_attrs[1]['userPassword'], ['snowstorm'])

    def test_email(self):
        name = "sasquatch"
        dc = "dc=test,dc=example,dc=com"
        person_attrs = person(name, dc=dc)
        self.assertEqual(person_attrs[0],
                         "cn=%s,ou=people,%s" % (name, dc))
        self.assertEqual(person_attrs[1]['mail'],
                         ["%s@test.example.com" % name])


class TestGroup(TestCase):
    def test_attrs(self):
        member = person('bigfoot')
        name = "north-american-great-apes"
        group_attrs = group(name, member)
        self.assertEqual(group_attrs[1]['cn'], [name])


class TestMockLdapDirectory(TestCase):
    def test_child_group_no_user(self):
        """Child groups shouldn't require a user for mockldap setup."""
        directory = mock_ldap_directory(
            extra_users=[
                ('somebody', 'the_parent'),
            ],
            group_lineage=[
                ('the_parent', 'child_1'),
                ('the_parent', 'child_2'),
                ('child_1', 'child_1_1'),
                ('child_2', 'child_2_1'),
                ('child_2', 'child_2_2'),
            ],
            ldap_dc="",
        )
        self.assertEqual(len(directory), 11)
        self.assertIn(group_dn('child_1', ""), directory)
        self.assertEqual(directory[group_dn('child_1', '')]['memberOf'],
                         [group_dn('child_1_1', '')])
        self.assertEqual(directory[group_dn('child_1', "")]['member'],
                         [group_dn('the_parent', '')])
        self.assertIn(group_dn('child_2', ""), directory)
        self.assertEqual(
            directory[group_dn('child_2', '')]['memberOf'],
            [group_dn('child_2_1', ''), group_dn('child_2_2', '')])
        self.assertEqual(directory[group_dn('child_2', "")]['member'],
                         [group_dn('the_parent', '')])
        self.assertIn(group_dn('child_1_1', ""), directory)
        self.assertEqual(directory[group_dn('child_1_1', "")]['memberOf'], [])
        self.assertEqual(directory[group_dn('child_1_1', "")]['member'],
                         [group_dn('child_1', '')])
        self.assertIn(group_dn('child_2_1', ""), directory)
        self.assertEqual(directory[group_dn('child_2_1', "")]['memberOf'], [])
        self.assertEqual(directory[group_dn('child_2_1', "")]['member'],
                         [group_dn('child_2', '')])
        self.assertIn(group_dn('child_2_2', ""), directory)
        self.assertEqual(directory[group_dn('child_2_2', "")]['memberOf'], [])
        self.assertEqual(directory[group_dn('child_2_2', "")]['member'],
                         [group_dn('child_2', '')])

    def test_no_args(self):
        directory = mock_ldap_directory()
        self.assertEqual(len(directory), 4)

    def test_bind_user(self):
        directory = mock_ldap_directory(ldap_dc="")
        dn = person_dn('auth', "")
        self.assertIn(dn, directory)
        self.assertEqual(directory[dn]['userPassword'], ['password'])

    def test_bind_password(self):
        directory = mock_ldap_directory(
            bind_user='ned', default_password='mancy', ldap_dc="")
        dn = person_dn('ned', "")
        self.assertEqual(directory[dn]['userPassword'], ['password'])
        directory = mock_ldap_directory(
            bind_user='ned', bind_password='flanders',
            default_password='mancy', ldap_dc="")
        self.assertEqual(directory[dn]['userPassword'], ['flanders'])

    def test_default_password(self):
        dn = person_dn('somebody', "")
        directory = mock_ldap_directory(
            ldap_dc="",
            extra_users=[('somebody', 'agroup')])
        self.assertEqual(directory[dn]['userPassword'], ['password'])
        directory = mock_ldap_directory(
            ldap_dc="",
            extra_users=[('somebody', 'agroup')],
            default_password='swordfish')
        self.assertEqual(directory[dn]['userPassword'], ['swordfish'])
