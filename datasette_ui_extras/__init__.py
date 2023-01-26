from datasette import hookimpl

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
