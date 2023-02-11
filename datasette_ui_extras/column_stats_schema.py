import sqlite3

DUX_COLUMN_STATS = 'dux_column_stats'
DUX_COLUMN_STATS_OPS = 'dux_column_stats_ops'
DUX_COLUMN_STATS_VALUES = 'dux_column_stats_values'
DUX_IDS = 'dux_ids'

CREATE_DUX_COLUMN_STATS = '''
CREATE TABLE {}(
  table_id integer not null references dux_ids(id),
  column_id integer not null references dux_ids(id),
  type text not null,
  nullable boolean not null,
  pk boolean not null,
  min any,
  max any,
  count integer not null, -- count(*)
  nulls integer not null, -- the output of COUNT(*) FILTER (WHERE TYPEOF(column) == 'null')
  integers integer not null, -- as above, but integer
  reals integer not null, -- as above, but real
  texts integer not null, -- as above, but text
  blobs integer not null, -- as above, but blob
  jsons integer not null, -- sum(json_valid(column))
  texts_min_length integer,
  texts_max_length integer,
  texts_whitespace integer not null, -- # of texts that have whitespace
  texts_newline integer not null, -- # of texts that have a newline
  blobs_min_length integer,
  blobs_max_length integer,
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
  name text not null
)
'''.format(DUX_IDS).strip()

CREATE_DUX_COLUMN_STATS_OPS = '''
CREATE TABLE {}(
  table_id integer primary key REFERENCES dux_ids(id),
  last_key text not null default '[]',
  pending integer not null check (pending in (0, 1)),
  rows integer not null default 0
)
'''.format(DUX_COLUMN_STATS_OPS).strip()

table_schemas = {
    DUX_IDS: CREATE_DUX_IDS,
    DUX_COLUMN_STATS_OPS: CREATE_DUX_COLUMN_STATS_OPS,
    DUX_COLUMN_STATS: CREATE_DUX_COLUMN_STATS,
    DUX_COLUMN_STATS_VALUES: CREATE_DUX_COLUMN_STATS_VALUES
}

async def ensure_schema(db):
    # We take a very brute force approach: if any table has the wrong schema,
    # we'll drop all the tables.
    await db.execute_write_fn(ensure_schema_conn)

def ensure_schema_conn(conn):
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

