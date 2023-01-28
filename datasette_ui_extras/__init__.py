import json
from datasette import hookimpl
import markupsafe
from .facets import enable_yolo_facets, facets_extra_body_script

PLUGIN = 'datasette-ui-extras'

# Not fully fleshed out: datasette-ui-extras consists of a bunch of "extras".
# Each extra has one or more of: custom CSS, custom JS, custom Python.
#
# Try to develop them as though they're standalone things, so they can be
# easily turned on/off, or upstreamed into Datasette.
#
# TODO: serve a minified/concatenated CSS/JS file
@hookimpl
def extra_css_urls(datasette):
    return [
        datasette.urls.static_plugins(PLUGIN, "app.css"),
        datasette.urls.static_plugins(PLUGIN, "hide-export.css"),
        datasette.urls.static_plugins(PLUGIN, "hide-table-definition.css"),
        datasette.urls.static_plugins(PLUGIN, "sticky-table-headers.css"),
        datasette.urls.static_plugins(PLUGIN, "lazy-facets.css"),
        datasette.urls.static_plugins(PLUGIN, "hide-filters.css"),
        datasette.urls.static_plugins(PLUGIN, "layout-row-page.css"),
        datasette.urls.static_plugins(PLUGIN, "compact-cogs.css"),
    ]

@hookimpl
def extra_js_urls(datasette):
    return [
        datasette.urls.static_plugins(PLUGIN, 'hide-filters.js'),
        datasette.urls.static_plugins(PLUGIN, "sticky-table-headers.js"),
        datasette.urls.static_plugins(PLUGIN, "focus-search-box.js"),
        datasette.urls.static_plugins(PLUGIN, 'lazy-facets.js'),
        datasette.urls.static_plugins(PLUGIN, 'layout-row-page.js'),
    ]

@hookimpl
def render_cell(value):
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

@hookimpl
def extra_body_script(template, database, table, columns, view_name, request, datasette):
    return facets_extra_body_script(template, database, table, columns, view_name, request, datasette)

@hookimpl
def startup():
    enable_yolo_facets()
