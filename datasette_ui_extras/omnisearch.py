from .column_stats import autosuggest_column

async def omnisearch(datasette, db, table, q):
    if not q:
        return []

    # TODO: dates
    # TODO: strings
    # TODO: string arrays

    banned_columns = {}

    # Do we have a title column? Search for entries based on that.
    label_column = await db.label_column_for_table(table)

    row_results = []
    if label_column:
        banned_columns[label_column] = True
        def get_row_results(conn):
            return suggest_row_results(datasette, conn, db.name, table, label_column, q)
        row_results = await db.execute_fn(get_row_results)

    # We only support single-column fkeys, so filter on max(seq)
    fkey_columns = list(await db.execute('select "table", "from", "to" from pragma_foreign_key_list(:table) where id in (select id from pragma_foreign_key_list(:table) group by 1 having max(seq) = 0)', [table]))

    fkey_results = []
    for other_table, my_column, other_column in fkey_columns:
        banned_columns[my_column] = True
        label_column = await db.label_column_for_table(other_table)

        def get_row_results(conn):
            return suggest_fkey_results(datasette, conn, db.name, table, my_column, other_table, other_column, label_column, q)
        fkey_results = fkey_results + list(await db.execute_fn(get_row_results))[0:3]
    return row_results + fkey_results

def suggest_fkey_results(datasette, conn, db, table, my_column, other_table, other_column, other_label_column, q):
    hits = autosuggest_column(conn, other_table, other_label_column, q)

    rv = []
    for hit in hits[0:3]:
        rv.append({
            'value': '{} is {}'.format(my_column, hit['value']),
            'url': '{}?{}={}'.format(datasette.urls.table(db, table), my_column, hit['pks'][0][other_column])
        })

    return rv

def suggest_row_results(datasette, conn, db, table, column, q):
    hits = autosuggest_column(conn, table, column, q)

    rv = []
    for hit in hits[0:3]:
        rv.append({
            'value': '...' + hit['value'],
            # TODO: this is wrong - doesn't support tilde encoding or multi-column pkeys
            'url': '{}/{}'.format(datasette.urls.table(db, table), list(hit['pks'][0].values())[0])
        })

    return rv
