from .column_stats import autosuggest_column
from .utils import get_editable_columns

def dateish(column):
    min = column['min']
    max = column['max']

    if not isinstance(min, str) or not isinstance(max, str):
        return False

    if min >= '1900-01-01' and max <= '9999-12-31':
        return True

    return False

async def omnisearch(datasette, db, table, q):
    if not q:
        return []

    known_columns = [r[0] for r in list(await db.execute("SELECT name FROM pragma_table_info(?)", [table]))]

    editable_columns = await get_editable_columns(datasette, db.name, table)
    base_table = table
    for info in editable_columns.values():
        if info['base_table'] != table:
            base_table = info['base_table']

    ok_columns = (datasette.plugin_config('datasette-ui-extras', db.name, table) or {}).get('omnisearch-columns', None)

    # TODO: dates

    banned_columns = {}

    # Do we have a title column? Search for entries based on that.
    label_column = await db.label_column_for_table(base_table)

    row_results = []
    if label_column and label_column in known_columns and (not ok_columns or label_column in ok_columns):
        banned_columns[label_column] = True
        def get_results(conn):
            return suggest_row_results(datasette, conn, db.name, base_table, table, label_column, q)
        row_results = await db.execute_fn(get_results)

    # We only support single-column fkeys, so filter on max(seq)
    fkey_columns = list(await db.execute('select "table", "from", "to" from pragma_foreign_key_list(:table) where id in (select id from pragma_foreign_key_list(:table) group by 1 having max(seq) = 0)', { 'table': base_table}))

    fkey_results = []
    for other_table, my_column, other_column in fkey_columns:
        if not my_column in known_columns:
            continue

        if ok_columns and not my_column in ok_columns:
            continue

        label_column = await db.label_column_for_table(other_table)
        if not label_column:
            continue

        banned_columns[my_column] = True

        def get_results(conn):
            return suggest_fkey_results(datasette, conn, db.name, base_table, table, my_column, other_table, other_column, label_column, q)
        fkey_results = fkey_results + list(await db.execute_fn(get_results))[0:3]

    all_columns = list(await db.execute('select di.name, dcs.* from dux_column_stats dcs join dux_ids di on di.id = dcs.column_id where table_id = (select id from dux_ids where name = ?)', [base_table]))
    string_results = []
    for column in all_columns:
        if not column['name'] in known_columns:
            continue

        if ok_columns and not column['name'] in ok_columns:
            continue

        if column['name'] in banned_columns:
            continue
        # column__exact={}, column__contains={}
        if column['json_arrays'] + column['nulls'] == column['count']:
            #print('json array: {}'.format(column['name']))
            banned_columns[column['name']] = True
            def get_results(conn):
                return suggest_string_results(datasette, conn, db.name, base_table, table, column['name'], q, 'contains', column['name'] + '__contains={}')
            string_results = string_results + list(await db.execute_fn(get_results))[0:3]

        elif column['texts'] + column['nulls'] == column['count'] and column['texts_newline'] == 0 and not dateish(column):
            # print('simple text: {}'.format(column['name']))
            banned_columns[column['name']] = True
            def get_results(conn):
                return suggest_string_results(datasette, conn, db.name, base_table, table, column['name'], q, 'is', column['name'] + '__exact={}')
            string_results = string_results + list(await db.execute_fn(get_results))[0:3]


    return row_results + fkey_results + string_results

def suggest_string_results(datasette, conn, db, table, link_table, column, q, verb, template):
    hits = autosuggest_column(conn, table, column, q)

    rv = []
    for hit in hits[0:3]:
        rv.append({
            'value': '{} {} {}'.format(column, verb, hit['value']),
            'url': '{}?{}'.format(datasette.urls.table(db, link_table), template.format(hit['value']))
        })

    return rv

def suggest_fkey_results(datasette, conn, db, table, link_table, my_column, other_table, other_column, other_label_column, q):
    hits = autosuggest_column(conn, other_table, other_label_column, q)

    rv = []
    for hit in hits[0:3]:
        rv.append({
            'value': '{} is {}'.format(my_column, hit['value']),
            'url': '{}?{}={}'.format(datasette.urls.table(db, link_table), my_column, hit['pks'][0][other_column])
        })

    return rv

def suggest_row_results(datasette, conn, db, table, link_table, column, q):
    # TODO: when table != link_table, we should filter the results to
    #       confirm that their pks are in link_table
    #
    #       If we don't, we may give nonsense results, and leak data that the
    #       user is not meant to have access to.
    #
    #       There's not a _good_ solution here. Because it's a view, we can't
    #       compute membership using triggers, so the worst case performance
    #       to do the filter could be quite bad.
    #
    #       We may want to forbid table != link_table? :(
    hits = autosuggest_column(conn, table, column, q)

    rv = []
    for hit in hits[0:3]:
        rv.append({
            'value': '...' + hit['value'],
            # TODO: this is wrong - doesn't support tilde encoding or multi-column pkeys
            'url': '{}/{}'.format(datasette.urls.table(db, link_table), list(hit['pks'][0].values())[0])
        })

    return rv
