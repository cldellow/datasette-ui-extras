import pytest

from datasette_ui_extras.schema_utils import get_column_choices_from_check_constraints

def test_column_choices_from_check_constraints():
    schema = '''CREATE TABLE q(
a check (a in ('foo', 'bar')),
b,
c check (c > 5),
check (b in (1, 2)))'''

    constraints = get_column_choices_from_check_constraints(schema)
    assert constraints == {'a': ['foo', 'bar'], 'b': [1, 2]}

    assert {} == get_column_choices_from_check_constraints('invalid sql')
