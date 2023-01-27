import json
from datasette import hookimpl
import markupsafe
from .facets import enable_yolo_facets

PLUGIN = 'datasette-ui-extras'

@hookimpl
def extra_css_urls(datasette):
    return [
        datasette.urls.static_plugins(PLUGIN, "facet-treatment.css"),
        datasette.urls.static_plugins(PLUGIN, "sticky-table-headers.css"),
        datasette.urls.static_plugins(PLUGIN, "lazy-facets.css"),
    ]

@hookimpl
def extra_js_urls(datasette):
    return [
        datasette.urls.static_plugins(PLUGIN, "sticky-table-headers.js"),
        datasette.urls.static_plugins(PLUGIN, "focus-search-box.js"),
        datasette.urls.static_plugins(PLUGIN, 'lazy-facets.js')
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
    return value

@hookimpl
def startup():
    enable_yolo_facets()
