from datasette import hookimpl

from datasette import hookimpl


@hookimpl
def extra_css_urls(datasette):
    return [
        datasette.urls.static_plugins("datasette-ui-extras", "app.css")
    ]

@hookimpl
def extra_js_urls(datasette):
    return [
        datasette.urls.static_plugins("datasette-ui-extras", "fixed-table-headers.js")
    ]
