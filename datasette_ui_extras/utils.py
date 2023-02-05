from urllib.parse import urlparse, parse_qs
from sqlglot import parse_one, exp

# Returns:
# - None if the edit UI ought not be shown
# - Information about which columns are editable
async def row_edit_params(datasette, request, database, table):
    if not request:
        return None

    if hasattr(request, '_dux_row_edit_params'):
        return request._dux_row_edit_params

    rv = await row_edit_params_raw(datasette, request, database, table)
    request._dux_row_edit_params = rv
    return rv

async def row_edit_params_raw(datasette, request, database, table):
    url = urlparse(request.url)
    qs = parse_qs(url.query)

    dux_edit_param = '_dux_edit' in qs and qs['_dux_edit'] == ['1']

    config = datasette.plugin_config('datasette-ui-extras', database=database)

    metadata_edit_param = config and 'editable' in config and table in config['editable']

    if not (dux_edit_param or metadata_edit_param):
        return None

    # Ensure user has permission to update this row
    visible, private = await datasette.check_visibility(
        request.actor,
        permissions=[
            ("update-row", (database, table)),
        ],
    )

    if not visible:
        return None

    editable_columns = await get_editable_columns(datasette, request, database, table)

    rv = {}
    for column in editable_columns:
        rv[column] = {}

    return rv

async def get_editable_columns(datasette, request, database, table):
    db = datasette.get_database(database)

    is_view = await db.view_exists(table)

    pkeys = await db.primary_keys(table)
    columns = await db.table_columns(table)


    if not is_view:
        return [col for col in columns if not col in pkeys]

    def fn(conn):
        return get_view_info(conn, table)

    view_info = await db.execute_fn(fn)

    if 'pks' in view_info and 'base_columns' in view_info:
        return [col for col in view_info['base_columns'] if not col in view_info['pks']]

    return []

def get_view_info(conn, name):
    sql, = conn.execute("select sql from sqlite_master where type = 'view' and name = ?", [name]).fetchone()

    parsed = None
    try:
        parsed = parse_one(sql)
    except:
        return {}

    view_exp = parsed.expression

    if not 'from' in view_exp.args:
        return {}

    from_exps = view_exp.args['from'].expressions

    if len(from_exps) != 1:
        return {}

    table_name = from_exps[0].this.this

    table_pkeys = [x[0] for x in conn.execute('select name from pragma_table_info(?) where pk = 1', [table_name]).fetchall()]
    cols = view_exp.expressions

    # We only want the columns that are pass-through identifiers
    ids = []
    for col in cols:
        this = col.this
        if isinstance(col, exp.Column) and isinstance(col.this, exp.Identifier):
            ids.append(col.name)


    return {
        'view': name,
        'base_table': table_name,
        'pks': table_pkeys,
        'base_columns': ids
    }


