import json
import os
import hashlib
import datasette
import asyncio
import markupsafe
from .plugin import pm
from .facets import enable_yolo_facets, facets_extra_body_script
from .filters import enable_yolo_arraycontains_filter, enable_yolo_exact_filter, yolo_filters_from_request
from .new_facets import StatsFacet, YearFacet, YearMonthFacet
from .view_row_pages import enable_yolo_view_row_pages
from .edit_row_pages import enable_yolo_edit_row_pages
from .utils import row_edit_params

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
    "edit-row.css",
]

js_files = [
    'hide-filters.js',
    "sticky-table-headers.js",
    "focus-search-box.js",
    'lazy-facets.js',
    'layout-row-page.js',
    "mobile-column-menu.js",
    "edit-row.js",
]

def fingerprint(files, ext):
    def concatenate():
        rv = []
        for fname in files:
            rv.append('/* {} */'.format(fname))
            fpath = os.path.abspath(os.path.join(__file__, '..', 'static', fname))

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
        css_path
    ]

@datasette.hookimpl(tryfirst=True)
def extra_js_urls(datasette):
    return [
        js_path
    ]

@datasette.hookimpl
def render_cell(datasette, database, table, column, value):
    async def inner():
        task = asyncio.current_task()
        request = None if not hasattr(task, '_duxui_request') else task._duxui_request

        params = await row_edit_params(datasette, request, database, table)
        if params and column in params:
            control = pm.hook.edit_control(datasette=datasette, database=database, table=table, column=column)

            if control:
                return markupsafe.Markup(
                    '<div class="dux-edit-stub" data-database="{database}" data-table="{table}" data-column="{column}" data-control="{control}" data-initial-value="{value}">Loading...</div>'.format(
                        control=markupsafe.escape(control),
                        database=markupsafe.escape(database),
                        table=markupsafe.escape(table),
                        column=markupsafe.escape(column),
                        value=markupsafe.escape(json.dumps(value)),
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
        return None
    return inner

@datasette.hookimpl
def extra_body_script(template, database, table, columns, view_name, request, datasette):
    return facets_extra_body_script(template, database, table, columns, view_name, request, datasette)

@datasette.hookimpl
def startup():
    enable_yolo_facets()
    enable_yolo_arraycontains_filter()
    enable_yolo_exact_filter()
    enable_yolo_view_row_pages()
    enable_yolo_edit_row_pages()

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
    ]
