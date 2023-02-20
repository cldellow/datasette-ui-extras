from .column_stats import autosuggest_column

async def omnisearch(datasette, db, table, q):
    # Do we have a title column? Search for entries based on that.
    label_column = await db.label_column_for_table(table)

    row_results = []
    if label_column:
        def get_row_results(conn):
            return suggest_row_results(datasette, conn, db.name, table, label_column, q)
        row_results = await db.execute_fn(get_row_results)

    return row_results

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
