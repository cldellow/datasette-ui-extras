import sqlite3

DUX_COLUMN_STATS = 'dux_column_stats'
DUX_COLUMN_STATS_OPS = 'dux_column_stats_ops'
DUX_COLUMN_STATS_VALUES = 'dux_column_stats_values'
DUX_PENDING_ROWS = 'dux_pending_rows'
DUX_IDS = 'dux_ids'

# This table should have reasonable defaults so we can insert new rows
# without having knowledge about what stats are being collected.
CREATE_DUX_COLUMN_STATS = '''
CREATE TABLE {}(
  table_id integer not null references dux_ids(id),
  column_id integer not null references dux_ids(id),
  type text not null,
  nullable boolean not null,
  pk boolean not null,
  min any,
  max any,
  count integer not null default 0, -- count(*)
  nulls integer not null default 0, -- the output of COUNT(*) FILTER (WHERE TYPEOF(column) == 'null')
  integers integer not null default 0, -- as above, but integer
  reals integer not null default 0, -- as above, but real
  texts integer not null default 0, -- as above, but text
  blobs integer not null default 0, -- as above, but blob
  json_strings integer not null default 0, -- sum(json_valid(column) and json_type(column) = 'text')
  json_arrays integer not null default 0, -- sum(json_valid(column) and json_type(column) = 'array')
  json_objects integer not null default 0, -- sum(json_valid(column) and json_type(column) = 'object')
  texts_min_length integer default 0,
  texts_max_length integer default 0,
  texts_whitespace integer not null default 0, -- # of texts that have whitespace
  texts_newline integer not null default 0, -- # of texts that have a newline
  blobs_min_length integer default 0,
  blobs_max_length integer default 0,
  primary key (table_id, column_id)
)
'''.format(DUX_COLUMN_STATS).strip()

CREATE_DUX_COLUMN_STATS_VALUES = '''
CREATE TABLE {}(
  table_id integer not null references dux_ids(id),
  column_id integer not null references dux_ids(id),
  value text,
  hash blob not null,
  count integer not null,
  pks text not null, -- JSON array of pkeys that have this value
  primary key (table_id, column_id, value, hash)
)
'''.format(DUX_COLUMN_STATS_VALUES).strip()

CREATE_DUX_IDS = '''
CREATE TABLE {}(
  id integer primary key,
  name text not null unique
)
'''.format(DUX_IDS).strip()

CREATE_DUX_COLUMN_STATS_OPS = '''
CREATE TABLE {}(
  table_id integer REFERENCES dux_ids(id),
  column_id integer REFERENCES dux_ids(id),
  last_key text not null default '{{}}',
  pending integer not null check (pending in (0, 1)),
  updated_at text not null default '1970-01-01 00:00:00Z',
  primary key (table_id, column_id)
)
'''.format(DUX_COLUMN_STATS_OPS).strip()

CREATE_DUX_PENDING_ROWS = '''
CREATE TABLE {}(
  id integer primary key,
  "table" text not null,
  the_rowid integer, -- for rowid tables, store the rowid
  old text,
  new text,
  timestamp integer not null default (strftime('%Y-%m-%d %H:%M:%fZ'))
)
'''.format(DUX_PENDING_ROWS).strip()

table_schemas = {
    DUX_PENDING_ROWS: CREATE_DUX_PENDING_ROWS,
    DUX_IDS: CREATE_DUX_IDS,
    DUX_COLUMN_STATS_OPS: CREATE_DUX_COLUMN_STATS_OPS,
    DUX_COLUMN_STATS: CREATE_DUX_COLUMN_STATS,
    DUX_COLUMN_STATS_VALUES: CREATE_DUX_COLUMN_STATS_VALUES,
}

async def ensure_schema_and_triggers(db):
    # We take a very brute force approach: if any table has the wrong schema,
    # we'll drop all the tables.
    await db.execute_write_fn(ensure_schema_and_triggers_conn)

def ensure_schema_and_triggers_conn(conn):
    ensure_schema(conn)
    ensure_triggers(conn)

def ensure_triggers(conn):
    tables = indexable_tables(conn)

    actual_triggers = conn.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'dux_stats_%'")
    actual_triggers = [(row[0], row[1], row[2]) for row in actual_triggers]

    # We install 3 triggers: dux_stats_insert_<table>, dux_stats_update_<table>, dux_stats_delete_<table>
    #
    # We compute the expected set of triggers, compare it to the actual, and drop/create as needed.
    expected_triggers = []
    for table in tables:
        is_rowid_table = True

        if list(conn.execute('SELECT * FROM pragma_index_info(?)', [table])):
            is_rowid_table = False

        for name, tbl_name, sql in get_stats_triggers(conn, table, is_rowid_table):
            expected_triggers.append((name, tbl_name, sql))

    for actual in actual_triggers:
        if not actual in expected_triggers:
            conn.execute('DROP TRIGGER "{}"'.format(actual[0]))

    for expected in expected_triggers:
        if not expected in actual_triggers:
            conn.execute(expected[2])

def get_stats_triggers(conn, table, is_rowid_table):
    columns = indexable_columns(conn, table)

    def generate_json_object(prefix):
        rv = ['json_object(']

        sep = ''
        for column in columns:
            rv.append("{sep}'{column}', {prefix}.\"{column}\"".format(column=column, prefix=prefix, sep=sep))
            sep = ', '

        rv.append(')')

        return ''.join(rv)

    rv = []
    for op in ['delete', 'insert', 'update']:
        trigger_name = 'dux_stats_{}_{}'.format(op, table)
        maybe_old = 'NULL'
        maybe_new = 'NULL'

        if op == 'delete' or op == 'update':
            maybe_old = generate_json_object('old')

        if op == 'insert' or op == 'update':
            maybe_new = generate_json_object('new')

        maybe_rowid = 'NULL'
        if is_rowid_table and op == 'delete':
            maybe_rowid = '"old".rowid'
        elif is_rowid_table and op == 'insert':
            maybe_rowid = '"new".rowid'
        elif is_rowid_table and op == 'update':
            maybe_rowid = '"old".rowid'

        sql = '''
CREATE TRIGGER "{trigger_name}" AFTER {op} ON "{table}" FOR EACH ROW
BEGIN
  INSERT INTO dux_pending_rows("table", "the_rowid", "old", "new") VALUES ('{table}', {maybe_rowid}, {maybe_old}, {maybe_new});
END
'''.format(trigger_name=trigger_name, op=op, table=table, maybe_rowid=maybe_rowid, maybe_old=maybe_old, maybe_new=maybe_new).strip()


        rv.append((trigger_name, table, sql))
    return rv

def ensure_schema(conn):
    def get_sql(table):
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", [table]).fetchone()

        if not sql:
            return None

        return sql[0]

    all_ok = True
    for k, v in table_schemas.items():
        if get_sql(k) != v:
            all_ok = False
            break

    if all_ok:
        return

    # Drop all the tables, in reverse order so fkeys don't cause us grief.
    for table in reversed(list(table_schemas.keys())):
        conn.execute('DROP TABLE IF EXISTS {}'.format(table))

    for table, sql in table_schemas.items():
        conn.execute(sql)

        roundtrip = get_sql(table)
        if roundtrip != sql:
            raise Exception('failed to create sql for table {}\nexpected: {}\nactual: {}'.format(table, sql, roundtrip))

# A table is indexable if:
# - not a virtual table (eg fts_posts)
# - not a suffix of a virtual table (eg, fts_posts_idx)
# - not a dux_ table
def indexable_tables(conn):
    return [row[0] for row in conn.execute("select name from sqlite_master sm where type = 'table' and not sql like 'CREATE VIRTUAL TABLE%' and not name like 'dux_%' and not exists(select 1 from sqlite_master sm2 where type = 'table' and sql like 'CREATE VIRTUAL TABLE%' and sm.name like sm2.name || '_%')")]

def indexable_columns(conn, table):
    return [row[0] for row in conn.execute('select name from pragma_table_info(?)', [table])]
