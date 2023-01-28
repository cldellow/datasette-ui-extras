import json
from datasette import hookimpl
from datasette.facets import load_facet_configs
import markupsafe
from .facets import enable_yolo_facets

PLUGIN = 'datasette-ui-extras'

@hookimpl
def extra_css_urls(datasette):
    return [
        datasette.urls.static_plugins(PLUGIN, "hide-table-definition.css"),
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
def extra_body_script(template, database, table, columns, view_name, request, datasette):
    if view_name != 'table':
        return

    # Infer the facets to render. This is... complicated.
    # Look in the query string: _facet, _facet_date, _facet_array
    # Also look in metadata: https://docs.datasette.io/en/stable/facets.html#facets-in-metadata-json



    # TODO: get the set of facets to render. This might come from metadata,
    #       or from something that the facet classes stashed in the request
    #       object
    tables_metadata = datasette.metadata("tables", database=database) or {}
    table_metadata = tables_metadata.get(table) or {}
    configs = load_facet_configs(request, table_metadata)

    facet_params = []

    # column and simple feel duplicative?
    # { 'column': [ {'source': 'metadata', 'config': { 'simple': 'country_long' } } ] }
    for type, facets in configs.items():
        # Blech, _facet_size=max isn't actually a facet.
        if type == 'size':
            continue

        key = 'simple'
        if type != 'column':
            key = type

        for facet in facets:
            param = '_facet'
            if type != 'column':
                param += '_' + type
            facet_params.append({ 'param': param, 'column': facet['config'][key], 'source': facet['source'] })

    return '''
__dux_facets = {};
'''.format(json.dumps(facet_params))

@hookimpl
def startup():
    enable_yolo_facets()
