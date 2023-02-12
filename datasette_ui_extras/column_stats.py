import sqlite3
import time
import json
import asyncio
from .column_stats_schema import ensure_schema, DUX_COLUMN_STATS, DUX_COLUMN_STATS_VALUES
import traceback
import sys

# A table is indexable if:
# - not a virtual table (eg fts_posts)
# - not a suffix of a virtual table (eg, fts_posts_idx)
# - not a dux_ table
async def indexable_tables(db):
    return [row[0] for row in list(await db.execute("select name from sqlite_master sm where type = 'table' and not sql like 'CREATE VIRTUAL TABLE%' and not name like 'dux_%' and not exists(select 1 from sqlite_master sm2 where type = 'table' and sql like 'CREATE VIRTUAL TABLE%' and sm.name like sm2.name || '_%')"))]

async def indexable_columns(db, table):
    columns = list(await db.execute('select name from pragma_table_info(?)', [table]))
    return [row[0] for row in columns]

async def compute_dux_column_stats(ds):
    t = time.time()

    dbs_to_watch = []
    for db_name, db in ds.databases.items():
        if db.is_memory or not db.is_mutable:
            continue

        if hasattr(db, 'engine') and db.engine == 'duckdb':
            continue

        await ensure_schema(db)
        dbs_to_watch.append(db_name)

    ds._dux_dbs_to_index = dbs_to_watch

def start_column_stats_indexer(datasette):
    if not datasette._dux_dbs_to_index:
        return

    loop = asyncio.get_running_loop()
    # We need to keep a reference to this task to prevent GC?
    # https://news.ycombinator.com/item?id=34754276
    datasette._dux_indexer_task = loop.create_task(index_loop(datasette, datasette._dux_dbs_to_index))

async def ensure_id(db, identifier):
    existing = await db.execute('SELECT id FROM dux_ids WHERE name = ?', [identifier])

    if existing:
        return list(existing)[0][0]

    if not existing:
        await db.execute_write('INSERT INTO dux_ids(name) VALUES (?)', [identifier])

        return await ensure_id(db, identifier)

async def ensure_empty_rows_for_db(db):
    # TODO: I think this is quite slow - we're _always_ doing write transactions, even
    # if the rows already exist.
    #
    # Also, we're not batching the ensure_id calls.
    #
    # e.g. on geonames, cooking, superuser this takes 400-500ms. I feel like 10ms would
    # be more reasonable?
    #
    # Checking existence of rows gets us to 160ms -- still, doing this intelligently in batch
    # would be good.

    known_tables = {}
    tables = await indexable_tables(db)
    for table in tables:
        table_id = await ensure_id(db, table)
        columns = await indexable_columns(db, table)
        column_ids = []
        known_tables[table_id] = column_ids
        for column in columns:
            column_id = await ensure_id(db, column)
            column_ids.append(column_id)

            column_info = list(await db.execute('select type, "notnull", pk from pragma_table_info(?) where name = ?', [table, column]))
            if not column_info:
                continue

            type, notnull, pk = column_info[0]
            nullable = notnull == 0

            if not list(await db.execute('SELECT 1 FROM dux_column_stats_ops WHERE table_id = ? AND column_id = ?', [table_id, column_id])):
                await db.execute_write(
                    'INSERT INTO dux_column_stats_ops(table_id, column_id, pending) SELECT ?, ?, 1 WHERE NOT EXISTS(SELECT * FROM dux_column_stats_ops WHERE table_id = ? AND column_id = ?)',
                   [table_id, column_id, table_id, column_id]
                )

            if not list(await db.execute('SELECT 1 FROM dux_column_stats WHERE table_id = ? AND column_id = ?', [table_id, column_id])):
                await db.execute_write(
                    'INSERT INTO dux_column_stats(table_id, column_id, type, nullable, pk) SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS(SELECT * FROM dux_column_stats WHERE table_id = ? AND column_id = ?)',
                   [table_id, column_id, type, nullable, pk, table_id, column_id]
                )

    # Remove entries for tables that no longer exist
    # Eventually we'll want to be able to do this online, but for now you have to restart.
    known_table_ids = ', '.join([str(x) for x in known_tables.keys()])
    if known_table_ids:
        await db.execute_write('DELETE FROM dux_column_stats_ops WHERE NOT table_id IN ({})'.format(known_table_ids))
        await db.execute_write('DELETE FROM dux_column_stats_values WHERE NOT table_id IN ({})'.format(known_table_ids))
        await db.execute_write('DELETE FROM dux_column_stats WHERE NOT table_id IN ({})'.format(known_table_ids))

    # TODO: delete entries that are in dux_column_stats but no longer in columns
    # TODO: delete entries that are in dux_column_stats_values but no longer in columns


async def index_loop(ds, dbs_to_watch):
    try:
        # Ensure that there are default empty rows in dux_column_stats_ops, dux_column_stats for every column.
        t = time.time()
        for db_name in dbs_to_watch:
            db = ds.databases[db_name]
            await ensure_empty_rows_for_db(db)

        print('datasette-ui-extras: stats schemas ensured in {} s'.format(time.time() - t))

        while True:
            did_work = False
            for db_name in dbs_to_watch:
                await asyncio.sleep(0)

                db = ds.databases[db_name]
                did_work = await index_db(db) or did_work

            if not did_work:
                await asyncio.sleep(1)

    except Exception as e:
       print('datasette-ui-extras: error during index_loop; exiting', file=sys.stderr)
       traceback.print_exc()
       sys.exit(1)

async def index_db(db):
    chunk_size = 1000

    # Look for a column that needs some progress.
    next_row = list(await db.execute('select table_id, column_id, last_key, (select name from dux_ids ids where ids.id = ops.table_id) AS table_name, (select name from dux_ids ids where ids.id = ops.column_id) AS column_name, updated_at from dux_column_stats_ops ops where pending order by updated_at asc limit 1'))

    if not next_row:
        return

    next_row = next_row[0]
    # print([x for x in next_row])
    table_id, column_id, last_key, table_name, column_name, updated_at = next_row

    pks = list(await db.execute('select name from pragma_table_info(?) where pk', [table_name]))
    pks = [row[0] for row in pks]
    if not pks:
        pks = ['rowid']

    key_expr = 'json_object({})'.format(
        ', '.join(["'{}'".format(pk) + ', ' + '"{}"'.format(pk) for pk in pks])
    )
    order_by = ', '.join(['"{}"'.format(pk) for pk in pks])
    last_key = json.loads(last_key)
    where = ''
    where_args = []
    if last_key:
        where = 'WHERE ({pks}) > ({last_keys})'.format(
            pks=', '.join(['"{}"'.format(pk) for pk in pks]),
            last_keys = ', '.join(['?' for pk in pks]),
        )
        where_args = [last_key[pk] for pk in pks]

    def make_base_sql(include_value=True, limit=chunk_size):
        value = ""

        if include_value:
            value = ", {value} AS value ".format(value = '"{}"'.format(column_name))
        base_sql = 'SELECT {key} AS key {value} FROM {table_name} {where} ORDER BY {order_by} LIMIT {limit}'.format(
            key=key_expr,
            value=value,
            table_name='"{}"'.format(table_name),
            where=where,
            order_by=order_by,
            limit=limit
        )
        return base_sql

    sql_including_values = make_base_sql(True)

    await update_summary_stats(db, table_id, column_id, sql_including_values, where_args)
    await update_distincts(db, table_id, column_id, sql_including_values, where_args)
    await update_json_distincts(db, table_id, column_id, sql_including_values, where_args)

    # Fetch and update distinct json array values

    # Determine what new value for last_key should be and update the ops table.
    next_key = list(await db.execute('{} OFFSET {}'.format(make_base_sql(False, 1), chunk_size - 1), where_args))


    if next_key:
        next_key = next_key[0][0]
    else:
        next_key = '{}'

    await db.execute_write(
        "UPDATE dux_column_stats_ops SET last_key = ?, pending = ?, updated_at = strftime('%Y-%m-%d %H:%M:%f') || 'Z' WHERE table_id = ? AND column_id = ?",
        [next_key, 0 if next_key == '{}' else 1, table_id, column_id]
    )

    return True

async def update_distincts(db, table_id, column_id, sql, where_args):
    # Fetch and update distinct values
    distincts_sql = '''
WITH xs AS ({}),
distincts AS (
SELECT
  substr(lower(value), 1, 20) AS value,
  substr(md5(value), 1, 8) AS hash,
  count(*) as count,
  json_group_array(json(key)) AS keys
FROM xs
WHERE typeof(value) == 'text' AND length(value) <= 100 and not (value >= '1800-01-01' and value <= '9999-12-31') and not value like 'http://%' and not value like 'https://%' and cast(cast(value as integer) as text) != value and not (value like '[%' and json_valid(value))
GROUP BY 1, 2
ORDER BY 3 DESC
)
SELECT value, hash, count, (select json_group_array(value) from (select value from json_each(keys) limit 10)) AS keys
FROM distincts
'''.format(sql)

    def read_fn(conn):
        return conn.execute(distincts_sql, where_args).fetchall()
    # NB: use execute_fn to avoid time limits
    distincts = await db.execute_fn(read_fn)

    def fn(conn):
        for value, hash, count, pks in distincts:
            pks = json.loads(pks)
            exists = conn.execute('SELECT pks FROM dux_column_stats_values WHERE table_id = ? and column_id = ? AND value = ? AND hash = ?', [table_id, column_id, value, hash]).fetchone()

            new_pks = []
            if exists:
                new_pks = json.loads(exists[0])
            else:
                conn.execute("INSERT INTO dux_column_stats_values(table_id, column_id, value, hash, count, pks) VALUES (?, ?, ?, ?, 0, '[]')", [table_id, column_id, value, hash]).fetchall()

            new_pks = [pk for pk in new_pks if not pk in pks]
            new_pks = new_pks[0:10 - len(pks)]
            new_pks = new_pks + pks

            conn.execute("UPDATE dux_column_stats_values SET count = count + ?, pks = ? WHERE table_id = ? AND column_id = ? AND value = ? AND hash = ?", [count, json.dumps(new_pks), table_id, column_id, value, hash]).fetchall()

    await db.execute_write_fn(fn)

async def update_json_distincts(db, table_id, column_id, sql, where_args):
    # Fetch and update distinct values from JSON string arrays
    json_distincts_sql = '''
WITH raw_xs AS ({}),
array_xs AS (SELECT key, value FROM raw_xs WHERE json_valid(value) AND json_type(value) = 'array'),
xs AS (SELECT array_xs.key, js_value.value FROM array_xs, json_each(array_xs.value) js_value),
distincts AS (
SELECT
  substr(lower(value), 1, 20) AS value,
  substr(md5(value), 1, 8) AS hash,
  count(*) as count,
  json_group_array(json(key)) AS keys
FROM xs
WHERE typeof(value) == 'text' AND length(value) <= 100 and not (value >= '1800-01-01' and value <= '9999-12-31') and not value like 'http://%' and not value like 'https://%' and cast(cast(value as integer) as text) != value and not (value like '[%' and json_valid(value))
GROUP BY 1, 2
ORDER BY 3 DESC
)
SELECT value, hash, count, (select json_group_array(value) from (select value from json_each(keys) limit 10)) AS keys
FROM distincts
'''.format(sql)

    def read_fn(conn):
        return conn.execute(json_distincts_sql, where_args).fetchall()

    # NB: use excute_fn to avoid time limits
    distincts = await db.execute_fn(read_fn)

    def fn(conn):
        for value, hash, count, pks in distincts:
            pks = json.loads(pks)
            exists = conn.execute('SELECT pks FROM dux_column_stats_values WHERE table_id = ? and column_id = ? AND value = ? AND hash = ?', [table_id, column_id, value, hash]).fetchone()

            new_pks = []
            if exists:
                new_pks = json.loads(exists[0])
            else:
                conn.execute("INSERT INTO dux_column_stats_values(table_id, column_id, value, hash, count, pks) VALUES (?, ?, ?, ?, 0, '[]')", [table_id, column_id, value, hash]).fetchall()

            new_pks = [pk for pk in new_pks if not pk in pks]
            new_pks = new_pks[0:10 - len(pks)]
            new_pks = new_pks + pks

            conn.execute("UPDATE dux_column_stats_values SET count = count + ?, pks = ? WHERE table_id = ? AND column_id = ? AND value = ? AND hash = ?", [count, json.dumps(new_pks), table_id, column_id, value, hash]).fetchall()

    await db.execute_write_fn(fn)


async def update_summary_stats(db, table_id, column_id, sql, where_args):
    # Fetch and update summary stats
    summary_stats = list(await db.execute('''
WITH xs AS ({})
SELECT
  min(case when typeof(value) == 'blob' or (typeof(value) == 'text' and length(value) > 100) then null else value end) as min,
  max(case when typeof(value) == 'blob' or (typeof(value) == 'text' and length(value) > 100) then null else value end) as max,
  count(*) as count,
  count(*) filter (where typeof(value) == 'null') as nulls,
  count(*) filter (where typeof(value) == 'integer') as integers,
  count(*) filter (where typeof(value) == 'real') as reals,
  count(*) filter (where typeof(value) == 'text') as texts,
  count(*) filter (where typeof(value) == 'blob') as blobs,
  coalesce(sum(json_valid(value)), 0) as jsons,
  min(length(value)) filter (where typeof(value) == 'text') as texts_min_length,
  max(length(value)) filter (where typeof(value) == 'text') as texts_max_length,
  coalesce(sum(case when typeof(value) == 'text' and value like '% %' then 1 else 0 end), 0) as texts_whitespace,
  coalesce(sum(case when typeof(value) == 'text' and value like '%' || x'0a' || '%' then 1 else 0 end), 0) as texts_newline,
  min(length(value)) filter (where typeof(value) == 'blob') as blobs_min_length,
  max(length(value)) filter (where typeof(value) == 'blob') as blobs_max_length
FROM xs
'''.format(sql), where_args))

    # texts_whitespace, texts_newline
    if summary_stats:
        summary_stats = summary_stats[0]
        #print('jsons={}'.format(summary_stats['jsons']))
        await db.execute_write('''
    UPDATE dux_column_stats SET
        count = count + :count,
        max = CASE WHEN max IS NULL THEN :max ELSE max(max, :max) END,
        min = CASE WHEN min IS NULL THEN :min ELSE min(min, :min) END,
        nulls = nulls + :nulls,
        integers = integers + :integers,
        reals = reals + :reals,
        texts = texts + :texts,
        blobs = blobs + :blobs,
        jsons = jsons + :jsons,
        texts_min_length = CASE WHEN texts_min_length IS NULL THEN :texts_min_length ELSE min(texts_min_length, :texts_min_length) END,
        texts_max_length = CASE WHEN texts_max_length IS NULL THEN :texts_max_length ELSE max(texts_max_length, :texts_max_length) END,
        blobs_min_length = CASE WHEN blobs_min_length IS NULL THEN :blobs_min_length ELSE min(blobs_min_length, :blobs_min_length) END,
        blobs_max_length = CASE WHEN blobs_max_length IS NULL THEN :blobs_max_length ELSE max(blobs_max_length, :blobs_max_length) END,
        texts_whitespace = texts_whitespace + :texts_whitespace,
        texts_newline = texts_newline + :texts_newline
    WHERE table_id = :table_id AND column_id = :column_id
    ''', {
        'table_id': table_id,
        'column_id': column_id,
        'count': summary_stats['count'],
        'min': summary_stats['min'],
        'max': summary_stats['max'],
        'nulls': summary_stats['nulls'],
        'integers': summary_stats['integers'],
        'reals': summary_stats['reals'],
        'texts': summary_stats['texts'],
        'blobs': summary_stats['blobs'],
        'jsons': summary_stats['jsons'],
        'texts_min_length': summary_stats['texts_min_length'],
        'texts_max_length': summary_stats['texts_max_length'],
        'blobs_min_length': summary_stats['blobs_min_length'],
        'blobs_max_length': summary_stats['blobs_max_length'],
        'texts_whitespace': summary_stats['texts_whitespace'],
        'texts_newline': summary_stats['texts_newline'],
    })


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
