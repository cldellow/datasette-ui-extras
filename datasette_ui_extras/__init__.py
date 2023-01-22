from datasette import hookimpl

from datasette import hookimpl


@hookimpl
def extra_css_urls(datasette):
    return [
        datasette.urls.static_plugins("datasette-ui-extras", "app.css")
    ]
