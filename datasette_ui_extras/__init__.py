import json
from datasette import hookimpl
import markupsafe


@hookimpl
def extra_css_urls(datasette):
    return [
        datasette.urls.static_plugins("datasette-ui-extras", "facet-treatment.css"),
        datasette.urls.static_plugins("datasette-ui-extras", "sticky-table-headers.css"),
    ]

@hookimpl
def extra_js_urls(datasette):
    return [
        datasette.urls.static_plugins("datasette-ui-extras", "sticky-table-headers.js"),
        datasette.urls.static_plugins("datasette-ui-extras", "focus-search-box.js")
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
