import json
import os
from functools import wraps
import hashlib
import datasette
from datasette import Response
import asyncio
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
from .column_stats_schema import DUX_IDS, DUX_COLUMN_STATS, DUX_COLUMN_STATS_OPS, DUX_COLUMN_STATS_VALUES
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
    def inner():
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
    return facets_extra_body_script(template, database, table, columns, view_name, request, datasette)

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
        (r"^/(?P<dbname>.*)/(?P<tablename>.*)/-/dux-autosuggest-column$", handle_autosuggest_column)
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

@datasette.hookimpl
def get_metadata(datasette, key, database, table):
    hide_tables = {
        'tables': {
            DUX_IDS: { 'hidden': True },
            DUX_COLUMN_STATS: { 'hidden': True },
            DUX_COLUMN_STATS_OPS: { 'hidden': True },
            DUX_COLUMN_STATS_VALUES: { 'hidden': True },
        }
    }

    rv = {
        'databases': {
        }
    }

    for db in datasette.databases.keys():
        rv['databases'][db] = hide_tables

    return rv

@datasette.hookimpl
def prepare_connection(conn):
    conn.enable_load_extension(True)

    crypto_so = os.path.abspath(os.path.join(__file__, '..', 'static', 'extensions', 'crypto.so'))
    conn.execute("SELECT load_extension(?)", [crypto_so]).fetchone()
    conn.enable_load_extension(False)

    # Try to set synchronous = NORMAL mode
    conn.execute('PRAGMA synchronous = NORMAL')

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
