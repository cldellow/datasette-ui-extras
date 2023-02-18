import json
import os
from functools import wraps
import hashlib
import datasette
from datasette import Response
from datasette.utils import await_me_maybe, to_css_class
import asyncio
import sqlite_sqlean
import markupsafe
from urllib.parse import parse_qs
from .hookspecs import hookimpl
from .facets import enable_yolo_facets, facets_extra_body_script
from .filters import enable_yolo_arraycontains_filter, enable_yolo_exact_filter, yolo_filters_from_request
from .plugin import pm
from .edit_controls import render_cell_edit_control
from .new_facets import StatsFacet, YearFacet, YearMonthFacet
from .view_row_pages import enable_yolo_view_row_pages
from .edit_row_pages import enable_yolo_edit_row_pages
from .utils import is_row_page
from .yolo_command import yolo_command
from .column_stats_schema import DUX_IDS, DUX_PENDING_ROWS, DUX_COLUMN_STATS, DUX_COLUMN_STATS_OPS, DUX_COLUMN_STATS_VALUES
from .column_stats import compute_dux_column_stats, autosuggest_column, start_column_stats_indexer

PLUGIN = 'datasette-ui-extras'

css_files = [
    "app.css",
    "hide-export.css",
    "hide-table-definition.css",
    "sticky-table-headers.css",
    "lazy-facets.css",
    "hide-filters.css",
    "layout-row-page.css",
    "compact-cogs.css",
    "mobile-column-menu.css",
    "edit-row/",
]

js_files = [
    'hide-filters.js',
    "sticky-table-headers.js",
    "focus-search-box.js",
    'lazy-facets.js',
    'layout-row-page.js',
    "mobile-column-menu.js",
    "edit-row/",
]

def fingerprint(files, ext):
    def concatenate():
        rv = []
        for fname in files:

            fpaths = [os.path.abspath(os.path.join(__file__, '..', 'static', fname))]

            if fname.endswith('/'):
                fpaths = []

                for fname in sorted(os.scandir(os.path.join(os.path.abspath(os.path.join(__file__, '..', 'static')), fname[:-1])), key=lambda f: f.path):
                    if fname.path.endswith('.' + ext):
                        fpaths.append(os.path.abspath(fname.path))


            for fpath in fpaths:
                rv.append('/* {} */'.format(fpath))
                f = open(fpath, 'r')
                contents = f.read()
                f.close()
                rv.append(contents)

        return '\n\n'.join(rv)

    hashcode = hashlib.sha256(concatenate().encode('utf-8')).hexdigest()[0:8]

    # TODO: how can we distinguish prod vs dev so we can serve a fingerprinted,
    #       long-lived cached file in prod, but have live reload in dev?
    #path = '/-/{}/{}.{}'.format(PLUGIN, hashcode, ext)
    path = '/-/{}/{}.{}'.format(PLUGIN, ext, ext)

    return path, concatenate

css_path, css_contents = fingerprint(css_files, 'css')
js_path, js_contents = fingerprint(js_files, 'js')

# Not fully fleshed out: datasette-ui-extras consists of a bunch of "extras".
# Each extra has one or more of: custom CSS, custom JS, custom Python.
#
# Try to develop them as though they're standalone things, so they can be
# easily turned on/off, or upstreamed into Datasette.
@datasette.hookimpl
def extra_css_urls(datasette):
    return [
        css_path,
        'https://cdnjs.cloudflare.com/ajax/libs/awesomplete/1.1.5/awesomplete.min.css',
        'https://cdn.jsdelivr.net/npm/air-datepicker@3.3.5/air-datepicker.min.css'
    ]

@datasette.hookimpl()
def extra_js_urls(datasette):
    return [
        js_path,
        'https://cdnjs.cloudflare.com/ajax/libs/awesomplete/1.1.5/awesomplete.min.js',
        'https://cdn.jsdelivr.net/npm/air-datepicker@3.3.5/air-datepicker.min.js'
    ]

@datasette.hookimpl
def render_cell(datasette, database, table, column, value):
    async def inner():
        task = asyncio.current_task()
        request = None if not hasattr(task, '_duxui_request') else task._duxui_request

        # Are we on the row page?
        # This feels like quite a large hack!
        if is_row_page(request):
            db = datasette.databases[database]

            # Is this column an fkey?
            fkeys = list(await db.execute('SELECT "table", "to" FROM pragma_foreign_key_list(?) WHERE "from" = ?', [table, column]))

            # We don't support compound foreign keys.
            if len(fkeys) == 1:

                other_table, other_column = fkeys[0]
                label_column = await db.label_column_for_table(other_table)
                the_other_row = list(await db.execute('SELECT "{}" FROM "{}" WHERE "{}" = ?'.format(label_column, other_table, other_column), [value]))
                if the_other_row:
                    return markupsafe.Markup(
                        '<a href="{href}">{label}</a>'.format(
                            href=datasette.urls.table(database, other_table) + '/' + str(value),
                            label=markupsafe.escape(str(the_other_row[0][0]))
                        )
                    )

        if isinstance(value, str) and (value == '[]' or (value.startswith('["') and value.endswith('"]'))):
            try:
                tags = json.loads(value)
                rv = ''

                for i, tag in enumerate(tags):
                    if i > 0:
                        rv += ', '
                    rv += markupsafe.Markup(
                        '<span>{tag}</span>'.format(
                            tag=markupsafe.escape(tag)
                        )
                    )

                return rv
            except:
                pass

    return inner

@datasette.hookimpl
def extra_body_script(template, database, table, columns, view_name, request, datasette):
    async def inner():
        facets = facets_extra_body_script(template, database, table, columns, view_name, request, datasette) or ''

        dux_pks = ''
        permissions = {}
        if database and table:
            for perm in ['insert-row', 'update-row', 'delete-row', 'drop-table']:
                res = await datasette.permission_allowed(
                    request.actor,
                    perm,
                    (database, table)
                )

                permissions[perm] = res == True

        if database:
            for perm in ['create-table']:
                res = await datasette.permission_allowed(
                    request.actor,
                    perm,
                    database
                )

                permissions[perm] = res == True

        if view_name == 'row':
            db = datasette.databases[database]

            pks = list(await db.execute('SELECT name FROM pragma_table_info(?) WHERE pk', [table]))
            pks = [r[0] for r in pks]
            pks = pks if pks else ['rowid']

            dux_pks = '__dux_pks = {};'.format(json.dumps(pks))


        permissions = '''
    __dux_permissions = {};
    '''.format(json.dumps(permissions))

        return '''
    {}

    {}

    {}
    '''.format(dux_pks, facets, permissions)

    return inner

@datasette.hookimpl
def startup(datasette):
    enable_yolo_facets()
    enable_yolo_arraycontains_filter()
    enable_yolo_exact_filter()
    enable_yolo_view_row_pages()
    enable_yolo_edit_row_pages()

    async def inner():
        await compute_dux_column_stats(datasette)

    return inner

@datasette.hookimpl
def register_facet_classes():
    return [StatsFacet, YearFacet, YearMonthFacet]

@datasette.hookimpl
def filters_from_request(request, database, table, datasette):
    async def dothething():
        return await yolo_filters_from_request(request, database, table, datasette)

    return dothething


@datasette.hookimpl(specname='actor_from_request', hookwrapper=True)
def sniff_actor_from_request(datasette, request):
    # TODO: This is temporary, we'll remove it when render_cell gets the request
    # param. The code is committed, just needs a new release of Datasette.
    asyncio.current_task()._duxui_request = request

    # all corresponding hookimpls are invoked here
    outcome = yield

@datasette.hookimpl
def register_routes():
    return [
        (
            css_path,
            lambda: datasette.Response(
                css_contents(),
                content_type="text/css; charset=utf-8"
            )
        ),
        (
            js_path,
            lambda: datasette.Response(
                js_contents(),
                content_type="text/javascript; charset=utf-8"
            )
        ),
        (r"^/(?P<dbname>.*)/(?P<tablename>.*)/-/dux-autosuggest-column$", handle_autosuggest_column),
        (r"^/(?P<dbname>.*)/(?P<tablename>.*)/(?P<pkey>.*)/-/dux-redirect-after-edit$", handle_redirect_after_edit)
    ]

async def handle_autosuggest_column(datasette, request):
    qs = parse_qs(request.query_string)

    column = qs['column'][0]
    q = qs.get('q', [''])[0]
    dbname = request.url_vars["dbname"]
    tablename = request.url_vars["tablename"]

    db = datasette.get_database(dbname)

    def fn(conn):
        return autosuggest_column(conn, tablename, column, q)
    suggestions = await db.execute_fn(fn)
    return Response.json(
        suggestions
    )

async def handle_redirect_after_edit(datasette, request):
    qs = parse_qs(request.query_string)

    action = qs['action'][0]
    dbname = request.url_vars["dbname"]
    tablename = request.url_vars["tablename"]
    pk = request.url_vars["pkey"]

    # TODO: why is this not finding our hook?
    redirects = pm.hook.redirect_after_edit(datasette=datasette, database=dbname, table=tablename, action=action, pk=pk)

    for redirect in redirects:
        rv = await await_me_maybe(redirect)

        if rv:
            return Response.json(
                {'url': rv}
            )

    raise Exception('handle_redirect_after_edit failed to find redirect')

@datasette.hookimpl
def get_metadata(datasette, key, database, table):
    rv = {
        'databases': {
        }
    }

    for db in datasette.databases.keys():
        # NB: don't re-use this object across databases, it causes
        # things to get mingled unexpectedly.
        hide_tables = {
            'tables': {
                DUX_IDS: { 'hidden': True },
                DUX_PENDING_ROWS: { 'hidden': True },
                DUX_COLUMN_STATS: { 'hidden': True },
                DUX_COLUMN_STATS_OPS: { 'hidden': True },
                DUX_COLUMN_STATS_VALUES: { 'hidden': True },
            }
        }

        rv['databases'][db] = hide_tables

    return rv

@datasette.hookimpl
def prepare_connection(conn):
    conn.enable_load_extension(True)

    sqlite_sqlean.load(conn, 'crypto')
    conn.enable_load_extension(False)

    # Try to enable WAL and synchronous = NORMAL mode
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA synchronous = NORMAL')

    # Foreign keys are great, databases should enforce them.
    conn.execute('PRAGMA foreign_keys = ON')


@datasette.hookimpl
def asgi_wrapper(datasette):
    def wrap_with_indexer(app):
        @wraps(app)
        async def handle_request(scope, receive, send):
            if not hasattr(datasette, "_dux_column_stats_indexer"):
                start_column_stats_indexer(datasette)
            datasette._dux_column_stats_indexer = True
            await app(scope, receive, send)

        return handle_request

    return wrap_with_indexer
