import sqlite3
import time
import json
import asyncio
from .column_stats_schema import ensure_schema_and_triggers, DUX_COLUMN_STATS, DUX_COLUMN_STATS_VALUES, indexable_tables, indexable_columns
import traceback
import sys

async def compute_dux_column_stats(ds):
    t = time.time()

    dbs_to_watch = []
    for db_name, db in ds.databases.items():
        if db.is_memory or not db.is_mutable:
            continue

        if hasattr(db, 'engine') and db.engine == 'duckdb':
            continue

        await ensure_schema_and_triggers(db)
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

async def ensure_ids(db, ids, needles): 
    missing = []
    for needle in list(set(needles)):
        if not needle in ids:
            missing.append(needle)

    if not missing:
        return

    for name in missing:
        ids[name] = await ensure_id(db, name)

async def ensure_empty_rows_for_db(db):
    known_tables = {}
    tables = await db.execute_fn(indexable_tables)

    ids = {}
    all_ids = await db.execute('SELECT id, name FROM dux_ids')
    for row in all_ids:
        ids[row['name']] = row['id']

    known_ops_raw = list(await db.execute('SELECT table_id, column_id FROM dux_column_stats_ops'))
    known_ops = {}
    for table_id, column_id in known_ops_raw:
        known_ops[(table_id, column_id)] = True

    known_stats_raw = list(await db.execute('SELECT table_id, column_id FROM dux_column_stats'))
    known_stats = {}
    for table_id, column_id in known_stats_raw:
        known_stats[(table_id, column_id)] = True

    await ensure_ids(db, ids, tables)
    for table in tables:
        table_id = ids[table]
        def indexable_columns_for_table(conn):
            return indexable_columns(conn, table)

        columns = await db.execute_fn(indexable_columns_for_table)
        await ensure_ids(db, ids, columns)
        column_ids = []
        known_tables[table_id] = column_ids

        column_infos = list(await db.execute('select name, type, "notnull", pk from pragma_table_info(?)', [table]))
        column_info_by_name = {}
        for column_info in column_infos:
            column_info_by_name[column_info['name']] = column_info

        for column in columns:
            column_id = ids[column]
            column_ids.append(column_id)

            column_info = column_info_by_name.get(column, None)
            if not column_info:
                continue

            column, type, notnull, pk = column_info
            nullable = notnull == 0

            if not (table_id, column_id) in known_ops:
                await db.execute_write(
                    'INSERT INTO dux_column_stats_ops(table_id, column_id, pending) SELECT ?, ?, 1 WHERE NOT EXISTS(SELECT * FROM dux_column_stats_ops WHERE table_id = ? AND column_id = ?)',
                   [table_id, column_id, table_id, column_id]
                )

            if not (table_id, column_id) in known_stats:
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
        return await index_pending_db(db)

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

def get_pk_columns(conn, table):
    pks = list(conn.execute('select name from pragma_table_info(?) where pk', [table]))
    pks = [row[0] for row in pks]
    if not pks:
        pks = ['rowid']

    return pks

async def index_pending_db(db):
    next_row = list(await db.execute('select id, the_rowid, "table", "old", "new" from dux_pending_rows order by id limit 1'))

    if not next_row:
        return False

    id, the_rowid, table, old, new = next_row[0]

    old = json.loads(old or '{}')
    new = json.loads(new or '{}')

    def get_pk_columns_fn(conn):
        return get_pk_columns(conn, table)

    pk_columns = await db.execute_fn(get_pk_columns_fn)

    # Diff old and new to determine what stats need to be updated.
    changes = []

    # The keys will be the same in each object, so enumerate the first non-empty object
    for column in (old or new).keys():
        if old and new:
            if old[column] != new[column]:
                changes.append(('delete', column, old[column]))
                changes.append(('insert', column, new[column]))
        elif old:
            changes.append(('delete', column, old[column]))
        elif new:
            changes.append(('insert', column, new[column]))

    stats_updates = []

    # We don't support updating all the stats columns, for example, we can update counts,
    # and we can update min/max when an addition sets a new min/max. But if we deleted
    # a value that was a min/max, we can't know what the new min/max should be without
    # scanning all the values, which we're not going to do.
    for kind, column, value in changes:
        # Try to mimic the SQL we use in the backfilling.
        #
        # Note: there is a semantic difference between:
        # SELECT CASE WHEN json_valid(column) THEN json_type(column) == 'text' ELSE 0 END FROM table;
        # and
        # SELECT CASE WHEN json_valid('literal') THEN json_type('literal') == 'text' ELSE 0 END FROM table;
        #
        # In the former case, the json_type(...) is not evaluated eagerly. In the literal case,
        # it is, meaning you will get a malformed JSON error.
        #
        # Instead, we do:
        # SELECT json_type(CASE WHEN json_valid('literal') THEN 'literal' ELSE 0 END)
        #
        # This differs from the backfill SQL.
        await db.execute_write('''
UPDATE dux_column_stats
SET
  count = count + :delta,
  nulls = CASE WHEN typeof(:value) == 'null' THEN nulls + :delta ELSE nulls END,
  integers = CASE WHEN typeof(:value) == 'integer' THEN integers + :delta ELSE integers END,
  reals = CASE WHEN typeof(:value) == 'real' THEN reals + :delta ELSE reals END,
  blobs = CASE WHEN typeof(:value) == 'blob' THEN blobs + :delta ELSE blobs END,
  texts = CASE WHEN typeof(:value) == 'text' THEN texts + :delta ELSE texts END,
  json_strings = json_strings + CASE WHEN json_type(CASE WHEN json_valid(:value) THEN :value ELSE 0 END) = 'text' THEN :delta ELSE 0 END,
  json_arrays = json_arrays + CASE WHEN json_type(CASE WHEN json_valid(:value) THEN :value ELSE 0 END) = 'array' THEN :delta ELSE 0 END,
  json_objects = json_objects + CASE WHEN json_type(CASE WHEN json_valid(:value) THEN :value ELSE 0 END) = 'object' THEN :delta ELSE 0 END,
  texts_whitespace = texts_whitespace + CASE WHEN typeof(:value) = 'text' AND :value LIKE '% %' THEN :delta ELSE 0 END,
  texts_newline = texts_newline + CASE WHEN typeof(:value) = 'text' AND :value LIKE '%' || x'0a' || '%' THEN :delta ELSE 0 END,
  texts_min_length = CASE WHEN typeof(:value) != 'text' OR :delta = -1 THEN texts_min_length
    ELSE MIN(COALESCE(texts_min_length, length(:value)), length(:value)) END,
  texts_max_length = CASE WHEN typeof(:value) != 'text' OR :delta = -1 THEN texts_max_length
    ELSE MAX(COALESCE(texts_max_length, length(:value)), length(:value)) END,
  blobs_min_length = CASE WHEN typeof(:value) != 'blob' OR :delta = -1 THEN blobs_min_length
    ELSE MIN(COALESCE(blobs_min_length, length(:value)), length(:value)) END,
  blobs_max_length = CASE WHEN typeof(:value) != 'blob' OR :delta = -1 THEN blobs_max_length
    ELSE MAX(COALESCE(blobs_max_length, length(:value)), length(:value)) END,
  min = CASE WHEN :delta = -1 OR typeof(:value) = 'blob' OR (typeof(:value) = 'text' AND LENGTH(:value) > 100) THEN min
  ELSE min(coalesce(min, :value), :value) END,
  max = CASE WHEN :delta = -1 OR typeof(:value) = 'blob' OR (typeof(:value) = 'text' AND LENGTH(:value) > 100) THEN max
  ELSE max(coalesce(max, :value), :value) END

WHERE
  table_id = (SELECT id FROM dux_ids WHERE name = :table)
  AND column_id = (SELECT id FROM dux_ids WHERE name = :column)
''', {
    'delta': 1 if kind == 'insert' else -1,
    'table': table,
    'column': column,
    'value': value
})
        # Index the actual values, but only for strings, and only some strings.
        # We don't index all string values - check if we should ignore this.
        #
        if isinstance(value, str):
            items = [value]

            try:
                # If this is a JSON-serialized array of strings, use those strings instead.
                maybe_items = json.loads(value)
                if isinstance(maybe_items, list):
                    items = maybe_items
            except:
                # Not a JSON array of strings.
                pass



            for item in items:
                if is_ignored_string(item):
                    continue

                # Compute the string and hash values for the lookup key.
                # This could be done in python, but I'm lazy.
                value_key, hash_key = list(await db.execute('SELECT substr(lower(:value), 1, 20), substr(md5(:value), 1, 8)', { 'value': item }))[0]
                #print('value_key={} hash_key={}'.format(value_key, hash_key))

                where = '''
table_id = (SELECT id FROM dux_ids WHERE name = :table)
AND column_id = (SELECT id FROM dux_ids WHERE name = :column)
AND value = :value_key
AND hash = :hash_key
'''

                where_args = {
                    'value_key': value_key,
                    'hash_key': hash_key,
                    'table': table,
                    'column': column,
                }

                if kind == 'delete':
                    # 1) Get the pkey for the old row
                    pk = {}
                    for pk_column in pk_columns:
                        pk[pk_column] = the_rowid if pk_column == 'rowid' else old[pk_column]

                    def do_delete(conn):


                        old_row = list(conn.execute('SELECT count, pks FROM dux_column_stats_values WHERE {where}'.format(where = where), where_args))

                        if not old_row:
                            return

                        old_row = old_row[0]
                        # 4) Delete the entire row if count is now negative

                        count, pks = old_row
                        # 2) Decrement the count of old entries
                        count -= 1
                        # 3) Delete the old pkey from the list of pkeys
                        pks = json.loads(pks)
                        pks = [x for x in pks if x != pk]

                        # 4) Delete the whole row if count <= 0.
                        if count <= 0:
                            conn.execute('DELETE FROM dux_column_stats_values WHERE {where}'.format(where=where), where_args)
                        else:
                            where_args['count'] = count
                            where_args['pks'] = json.dumps(pks)
                            conn.execute('UPDATE dux_column_stats_values SET count = :count, pks = :pks WHERE {where}'.format(where=where), where_args)

                    await db.execute_write_fn(do_delete)
                elif kind == 'insert':
                    # 1) Get the pkey for the new row
                    pk = {}
                    for pk_column in pk_columns:
                        pk[pk_column] = the_rowid if pk_column == 'rowid' else new[pk_column]

                    # 2) Ensure there is a row with 0 count and empty pkey array
                    def do_insert(conn):
                        old_row = list(conn.execute('SELECT count, pks FROM dux_column_stats_values WHERE {where}'.format(where = where), where_args))

                        count = 0
                        pks = []
                        if not old_row:
                            # Insert the empty row
                            where_args['count'] = 0
                            where_args['pks'] = '[]'
                            conn.execute('INSERT INTO dux_column_stats_values(table_id, column_id, value, hash, count, pks) VALUES ((SELECT id FROM dux_ids WHERE name = :table), (SELECT id FROM dux_ids WHERE name = :column), :value_key, :hash_key, :count, :pks)', where_args)

                        else:
                            old_row = old_row[0]
                            # 4) Delete the entire row if count is now negative

                            count, pks = old_row
                            pks = json.loads(pks)

                        count += 1
                        pks = [x for x in pks if x != pk] + [pk]

                        where_args['count'] = count
                        where_args['pks'] = json.dumps(pks)
                        conn.execute('UPDATE dux_column_stats_values SET count = :count, pks = :pks WHERE {where}'.format(where=where), where_args)


                    await db.execute_write_fn(do_insert)
                    # 3) Increment the coutn
                    # 4) Insert the pkey


    await db.execute_write('DELETE FROM dux_pending_rows WHERE id = :id', [id])



    return False

def is_ignored_string(value):
    # from the SQL backfill code:
    # WHERE typeof(value) == 'text' AND length(value) <= 100 and not (value >= '1800-01-01' and value <= '9999-12-31') and not value like 'http://%' and not value like 'https://%' and cast(cast(value as integer) as text) != value and not (value like '[%' and json_valid(value))
    if not isinstance(value, str):
        return False

    if value >= '1800-01-01' and value <= '9999-12-31':
        return True

    if value.startswith('http://') or value.startswith('https://'):
        return True

    if value.startswith('['):
        try:
            json.loads(value)
            return True
        except:
            pass

    try:
        int(value)
        return True
    except:
        pass

    return False

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
  coalesce(sum(case when json_valid(value) then json_type(value) = 'text' else 0 end), 0) as json_strings,
  coalesce(sum(case when json_valid(value) then json_type(value) = 'array' else 0 end), 0) as json_arrays,
  coalesce(sum(case when json_valid(value) then json_type(value) = 'object' else 0 end), 0) as json_objects,
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
        json_strings = json_strings + :json_strings,
        json_arrays = json_arrays + :json_arrays,
        json_objects = json_objects + :json_objects,
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
        'json_strings': summary_stats['json_strings'],
        'json_arrays': summary_stats['json_arrays'],
        'json_objects': summary_stats['json_objects'],
        'texts_min_length': summary_stats['texts_min_length'],
        'texts_max_length': summary_stats['texts_max_length'],
        'blobs_min_length': summary_stats['blobs_min_length'],
        'blobs_max_length': summary_stats['blobs_max_length'],
        'texts_whitespace': summary_stats['texts_whitespace'],
        'texts_newline': summary_stats['texts_newline'],
    })


def autosuggest_column(conn, table, column, q):
    # Consider max 100 things before sorting - gives generally good results, and is defensive
    # against someone autocompleting the empty string
    raw_rows = conn.execute(
        ('WITH xs AS (SELECT value, hash, count, pks FROM {} WHERE "table_id" = (SELECT id FROM dux_ids WHERE name = ?) AND "column_id" = (SELECT id FROM dux_ids WHERE name = ?) AND value >= ? AND value < ? || ' + "x'ffffffff'" + ' LIMIT 100) SELECT * FROM xs ORDER BY count DESC LIMIT 10').format(DUX_COLUMN_STATS_VALUES),
        [table, column, q.lower(), q.lower()]
    ).fetchall()

    # The value stored is just for indexing -- we need to fetch the actual value
    # from the underlying table, by looking up the entries in `pks`.
    rows = []
    for value, hash, count, pks in raw_rows:
        pks = json.loads(pks)
        if not pks:
            continue

        pk = pks[0]
        keys = list(pk.items())
        rv = conn.execute(
            '''
WITH xs as (SELECT "{column}" AS value FROM "{table}" WHERE ({keys}) = ({key_bindings})),
choices AS (SELECT json.value, substr(md5(json.value), 1, 8) as hash FROM xs, json_each(CASE WHEN json_valid(xs.value) AND json_type(xs.value) = 'array' THEN xs.value ELSE json_array(xs.value) END) AS json)
SELECT value FROM choices WHERE hash = ?
            '''.format(
                column = column,
                table = table,
                keys = ', '.join([k[0] for k in keys]),
                key_bindings = ', '.join(['?' for k in keys])
            ),
            [k[1] for k in keys] + [hash]
        ).fetchone()

        if not rv:
            continue

        rows.append({
            'value': rv[0],
            'count': count,
            'pks': pks
        })


    return rows
