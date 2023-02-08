import sqlite3
import time
import json

DUX_COLUMN_STATS = 'dux_column_stats'
DUX_COLUMN_STATS_VALUES = 'dux_column_stats_values'

CREATE_DUX_COLUMN_STATS = '''
CREATE TABLE {}(
  "table" text not null,
  column text not null,
  type text not null,
  nullable boolean not null,
  pk boolean not null,
  min any,
  max any,
  computed_at text not null default (datetime()),
  "limit" integer, -- Was this based on SELECT *, or SELECT * LIMIT N ?
  distinct_limit int not null, -- How many distinct examples were we willing to capture?
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
  primary key ("table", column)
)
'''.format(DUX_COLUMN_STATS).strip()

CREATE_DUX_COLUMN_STATS_VALUES = '''
CREATE TABLE {}(
  "table" text not null,
  "column" text not null,
  value text,
  count integer not null,
  pks text, -- JSON array of pkeys that have this value
  primary key ("table", "column", value)
)
'''.format(DUX_COLUMN_STATS_VALUES).strip()

def escape_identifier(name):
    return '"{}"'.format(name)

async def get_dux_column_stats_values_sql(db):
    sql = list(await db.execute("SELECT sql FROM sqlite_master WHERE name = ?", [DUX_COLUMN_STATS_VALUES]))

    if not sql:
        return None

    return sql[0][0]


async def get_dux_column_stats_sql(db):
    sql = list(await db.execute("SELECT sql FROM sqlite_master WHERE name = ?", [DUX_COLUMN_STATS]))

    if not sql:
        return None

    return sql[0][0]

async def create_dux_column_stats(db):
    await db.execute_write(CREATE_DUX_COLUMN_STATS)

async def create_dux_column_stats_values(db):
    await db.execute_write(CREATE_DUX_COLUMN_STATS_VALUES)

async def ensure_dux_column_stats_values(db):
    old_schema = await get_dux_column_stats_values_sql(db)

    if old_schema != CREATE_DUX_COLUMN_STATS_VALUES:
        if old_schema:
            await db.execute_write('DROP TABLE {}'.format(DUX_COLUMN_STATS_VALUES))

        await create_dux_column_stats_values(db)

        # sanity check: confirm it round trips
        new_schema = await get_dux_column_stats_values_sql(db)

        if new_schema != CREATE_DUX_COLUMN_STATS_VALUES:
            raise Exception('datasette-ui-extras: unable to create {}'.format(DUX_COLUMN_STATS_VALUES))


async def ensure_dux_column_stats(db):
    await ensure_dux_column_stats_values(db)
    sql = await get_dux_column_stats_sql(db)

    if sql != CREATE_DUX_COLUMN_STATS:
        if sql:
            await db.execute_write('DROP TABLE {}'.format(DUX_COLUMN_STATS))

        await create_dux_column_stats(db)

        # sanity check: confirm it round trips
        new_schema = await get_dux_column_stats_sql(db)

        if new_schema != CREATE_DUX_COLUMN_STATS:
            raise Exception('datasette-ui-extras: unable to create {}'.format(DUX_COLUMN_STATS))

    # For each table, for each column, ensure it exists.
    # Skip virtual tables and shadow tables associated with virtual tables.
    tables = [row[0] for row in list(await db.execute("select name from sqlite_master sm where type = 'table' and not sql like 'CREATE VIRTUAL TABLE%' and not exists(select 1 from sqlite_master sm2 where type = 'table' and sql like 'CREATE VIRTUAL TABLE%' and sm.name like sm2.name || '_%')"))]

    for table in tables:
        columns = list(await db.execute('select name from pragma_table_info(?)', [table]))

        for column, in columns:
            await fetch_column_stats(db, table, column)

        # TODO: delete entries that are in dux_column_stats but no longer in columns
        # TODO: delete entries that are in dux_column_stats_values but no longer in columns


async def fetch_column_stats(db, table, column):
    if table == DUX_COLUMN_STATS or table == DUX_COLUMN_STATS_VALUES:
        # Avoid creating black holes.
        return

    t = time.time()
    limit = 100
    distinct_limit = 100
    rows = list(await db.execute('select * from {} where "table" = ? and "column" = ?'.format(DUX_COLUMN_STATS), [table, column]))

    if rows:
        return rows[0]

    def fn(conn):
        return compute_column_stats(conn, table, column, limit, distinct_limit)
    computed = await db.execute_fn(fn)

    def save_fn(conn):
        return save_column_stats(conn, table, column, computed)
    await db.execute_write_fn(save_fn)

def save_column_stats(conn, table, column, computed):
    # Save most of `computed` into dux_column_stats.
    # If json_distincts is non empty, save it into dux_column_stats_values.
    # Else, save distincts into dux_column_stats.

    with conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('DELETE FROM {} WHERE "table" = ? AND "column" = ?'.format(DUX_COLUMN_STATS_VALUES), [table, column])
        conn.execute('DELETE FROM {} WHERE "table" = ? AND "column" = ?'.format(DUX_COLUMN_STATS), [table, column])

        json_distincts = computed.pop('json_distincts')
        distincts = computed.pop('distincts')
        if json_distincts:
            conn.executemany(
                'INSERT INTO {}("table", "column", "value", "count") VALUES (?, ?, ?, ?)'.format(DUX_COLUMN_STATS_VALUES),
                [(table, column, row[0], row[1]) for row in json_distincts]
            )
        else:
            conn.executemany(
                'INSERT INTO {}("table", "column", "value", "count", "pks") VALUES (?, ?, ?, ?, ?)'.format(DUX_COLUMN_STATS_VALUES),
                [(table, column, row[0], row[1], row[2]) for row in distincts]
            )

        keys = list(computed.keys())
        stmt = "INSERT INTO {}({}) VALUES({})".format(
            DUX_COLUMN_STATS,
            ', '.join([escape_identifier(key) for key in keys]),
            ', '.join(['?' for key in keys])
        )
        conn.execute(stmt, [computed[key] for key in keys])



def compute_column_stats(conn, table, column, limit, distinct_limit):
    # Determine the pkeys of the table.
    pks = [row[0] for row in conn.execute('select name from pragma_table_info(?) where pk', [table]).fetchall()]
    if not pks:
        pks = ['rowid']

    column_info = conn.execute('select type, "notnull", pk from pragma_table_info(?) where name = ?', [table, column]).fetchone()
    if not column_info:
        return

    type, notnull, pk = column_info
    nullable = notnull == 0


    # The goal is collect stats for driving UI, and being lossy is OK.
    #
    # We avoid collecting very large string/blob values in the
    # min/max colums and the distinct values columns.
    summary_stats = conn.execute('''
WITH xs AS (SELECT "{}" AS value FROM "{}" LIMIT {})
SELECT
  min(case when typeof(value) == 'blob' or (typeof(value) == 'text' and length(value) > 100) then null else value end) as min,
  max(case when typeof(value) == 'blob' or (typeof(value) == 'text' and length(value) > 100) then null else value end) as max,
  count(*) filter (where typeof(value) == 'null') as nulls,
  count(*) filter (where typeof(value) == 'integer') as integers,
  count(*) filter (where typeof(value) == 'real') as reals,
  count(*) filter (where typeof(value) == 'text') as texts,
  count(*) filter (where typeof(value) == 'blob') as blobs,
  sum(json_valid(value)) as jsons,
  min(length(value)) filter (where typeof(value) == 'text') as texts_min_length,
  max(length(value)) filter (where typeof(value) == 'text') as texts_max_length,
  sum(case when typeof(value) == 'text' and value like '% %' then 1 else 0 end) as texts_whitespace,
  sum(case when typeof(value) == 'text' and value like '%' || x'0a' || '%' then 1 else 0 end) as texts_newline,
  min(length(value)) filter (where typeof(value) == 'blob') as blobs_min_length,
  max(length(value)) filter (where typeof(value) == 'blob') as blobs_max_length
FROM xs
'''.format(column, table, limit)
    ).fetchone()

    pk_json_parts = []
    for pk in pks:
        pk_json_parts.append('?') # the key name, eg 'id'
        pk_json_parts.append(escape_identifier(pk))

    no_blobs = []
    for pk in pks:
        no_blobs.append("typeof({}) == 'blob'".format(escape_identifier(pk)))
    no_blobs = ' OR '.join(no_blobs)
    pk_json_object = 'CASE WHEN {} THEN NULL ELSE json_object('.format(no_blobs) + ','.join(pk_json_parts) + ') END'

    distincts_sql = '''
WITH xs AS (SELECT {} AS "pk", "{}" AS value FROM "{}" LIMIT {})
SELECT value, count(*) as count, json_group_array(json(pk)) AS pks
FROM xs
WHERE typeof(value) != 'blob' AND (typeof(value) != 'text' OR length(value) <= 100)
GROUP BY 1
ORDER BY 2 DESC
LIMIT {}
'''.format(pk_json_object, column, table, limit, distinct_limit)
    distincts = conn.execute(distincts_sql, pks).fetchall()

    json_distincts = []
    json_distincts_sql = '''
WITH xs_raw AS (SELECT {} as "pk", "{}" AS json_value FROM "{}" LIMIT {}),
xs AS (SELECT "pk", "json_value" FROM xs_raw WHERE json_type("json_value") = 'array'),
ys AS (SELECT value FROM json_each(json_value), xs)
SELECT value, count(*) as count
FROM ys
WHERE typeof(value) != 'text' OR length(value) <= 100
GROUP BY 1
ORDER BY 2 DESC
LIMIT {}
'''.format(pk_json_object, column, table, limit, distinct_limit)

    try:
        json_distincts = list(conn.execute(json_distincts_sql, pks).fetchall())
    except sqlite3.OperationalError:
        # Invalid JSON will throw, that's OK
        pass

    return {
        'table': table,
        'column': column,
        'type': type,
        'nullable': nullable,
        'pk': pk,
        'limit': limit,
        'distinct_limit': distinct_limit,
        'min': summary_stats['min'],
        'max': summary_stats['max'],
        'nulls': summary_stats['nulls'],
        'integers': summary_stats['integers'],
        'reals': summary_stats['reals'],
        'texts': summary_stats['texts'],
        'blobs': summary_stats['blobs'],
        'jsons': summary_stats['jsons'],
        'texts_newline': summary_stats['texts_newline'],
        'texts_whitespace': summary_stats['texts_whitespace'],
        'texts_min_length': summary_stats['texts_min_length'],
        'texts_max_length': summary_stats['texts_max_length'],
        'blobs_min_length': summary_stats['blobs_min_length'],
        'blobs_max_length': summary_stats['blobs_max_length'],
        'distincts': [list(x) for x in distincts],
        'json_distincts': [list(x) for x in json_distincts],
    }


async def compute_dux_column_stats(ds):
    t = time.time()
    for db in ds.databases.values():
        if db.is_memory or not db.is_mutable:
            continue

        if hasattr(db, 'engine') and db.engine == 'duckdb':
            continue

        await ensure_dux_column_stats(db)

def autosuggest_column(conn, table, column, q):
    rows = conn.execute(
        'SELECT value, count, pks FROM {} WHERE "table" = ? AND "column" = ? AND lower(value) LIKE ? ORDER BY count DESC LIMIT 10'.format(DUX_COLUMN_STATS_VALUES),
        [table, column, q.lower() + '%']
    ).fetchall()

    return [{
        'value': row['value'],
        'count': row['count'],
        'pks': None if not row['pks'] else json.loads(row['pks'])
    } for row in rows]
