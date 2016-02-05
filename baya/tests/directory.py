test_users = [
    ('has_all', 'a'),
    ('has_all', 'a_admin'),
    ('has_all', 'b'),
    ('has_a', 'a'),
    ('has_b', 'b'),
    ('has_aa', 'aa'),
    ('has_ab', 'ab'),
    ('has_aaa', 'aaa'),
    ('has_a_b', 'a'),
    ('has_a_b', 'b'),
    ('has_nothing', 'nothing')
]

group_lineage = [
    ('a_admin', 'a'),
    ('a', 'aa'),
    ('a', 'ab'),
    ('aa', 'aaa'),
]
