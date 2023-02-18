from urllib.parse import urlparse, parse_qs
from sqlglot import parse_one, exp
from .column_stats_schema import DUX_COLUMN_STATS, DUX_IDS
from .schema_utils import get_column_choices_from_check_constraints

def is_row_page(request):
    # This feels like a giant hack!
    return request and request.scope and request.scope['url_route'] and 'database' in request.scope['url_route']['kwargs'] and 'table' in request.scope['url_route']['kwargs'] and 'pks' in request.scope['url_route']['kwargs'] and True

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

    is_insert = url.path.endswith('/dux-insert')

    metadata_edit_param = config and 'editable' in config and table in config['editable']

    if not (dux_edit_param or metadata_edit_param or is_insert):
        return None

    permission_required = 'insert-row' if is_insert else 'update-row'
    # Ensure user has permission to update this row
    allowed = await datasette.permission_allowed(
        request.actor,
        permission_required,
        (database, table)
    )

    if not allowed:
        return None

    rv = await get_editable_columns(datasette, request, database, table)
    return rv

async def get_editable_columns(datasette, request, database, table):
    db = datasette.get_database(database)

    is_view = await db.view_exists(table)


    pkeys = await db.primary_keys(table)
    columns = await db.table_columns(table)


    if not is_view:
        def fn(conn):
            return get_table_info(conn, table)

        table_info = await db.execute_fn(fn)

        rv = {}
        for column in table_info['columns'].values():
            if column['pk']:
                continue

            rv[column['name']] = column

        await annotate_columns(rv, db, table)

        return rv

    def fn(conn):
        return get_view_info(conn, table)

    view_info = await db.execute_fn(fn)

    if not view_info:
        return {}

    rv = {}
    for column in view_info['base_columns']:
        if column in view_info['pks']:
            continue
        rv[column] = view_info['table_info']['columns'][column]

    await annotate_columns(rv, db, view_info['base_table'])

    return rv

async def annotate_columns(rv, db, table_name):
    # Annotate rv with data from a few places:
    # (1) sqlite_master - parse the table schema for CHECK (column IN ('a', 'b', ..., 'z')) constraints
    #     These are a closed set of options.
    #
    # (2) dux_column_stats - this is summary metadata that can inform what UI is best to show.
    schema = list(await db.execute("SELECT sql FROM sqlite_master WHERE name = ? AND type = 'table'", [table_name]))[0][0]
    choices = get_column_choices_from_check_constraints(schema)
    for column, options in choices.items():
        if column in rv:
            rv[column]['check_choices'] = options


    results = []
    try:
        # TODO: this will need to look up by dux_ids
        results = list(await db.execute('SELECT stats.*, ids.name AS column FROM dux_column_stats stats JOIN dux_ids ids ON ids.id = stats.column_id WHERE "table_id" = (SELECT id FROM dux_ids WHERE name = ?)', [table_name]))
    except:
        return

    for row in results:
        column = row['column']
        if not column in rv:
            continue

        to_annotate = rv[column]
        to_annotate['base_table'] = table_name

        for key in row.keys():
            if key == 'column':
                continue
            elif key == 'table_id' or key == 'column_id':
                # Don't pass these through -- they're internal transient details, as dux_ids IDs aren't
                # meaningful
                pass
            else:
                value = row[key]
                if key == 'nullable':
                    value = not not value
                to_annotate[key] = value


def get_table_info(conn, name):
    data = conn.execute('select name, "type", "notnull", dflt_value, pk from pragma_table_info(?)', [name]).fetchall()
    rv = {}
    cols = {}
    rv['columns'] = cols

    # TODO: add sqlglot to parse CHECK constraints

    # TODO: parse select "table", "from", "to" from pragma_foreign_key_list(?)
    for name, type, notnull, dflt_value, pk in data:
        cols[name] = {
            'name': name,
            'type': type,
            'nullable': notnull == 0,
            'default_value': dflt_value,
            'pk': pk == 1
        }

    return rv

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
        'base_columns': ids,
        'table_info': get_table_info(conn, table_name)
    }


